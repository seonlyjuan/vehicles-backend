alter table public.listing_payments
  add column if not exists net_amount numeric(12, 2) not null default 0 check (net_amount >= 0),
  add column if not exists vat_amount numeric(12, 2) not null default 0 check (vat_amount >= 0),
  add column if not exists vat_rate_percent numeric(5, 2) not null default 0 check (vat_rate_percent >= 0);

do $$
declare
  vehicle_table text;
begin
  foreach vehicle_table in array array['bicycles', 'cars', 'motorbikes']
  loop
    execute format('alter table public.%I drop constraint if exists %I', vehicle_table, vehicle_table || '_payment_status_check');
    execute format(
      'alter table public.%I add constraint %I check (payment_status in (''pending'', ''paid'', ''failed'', ''refunded''))',
      vehicle_table,
      vehicle_table || '_payment_status_check'
    );
  end loop;
end $$;

create table if not exists public.payment_webhook_events (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  provider_event_id text not null,
  provider_transaction_id text not null,
  event_status text not null check (event_status in ('paid', 'failed', 'refunded')),
  payload jsonb not null default '{}'::jsonb,
  received_at timestamptz not null default now(),
  processed_at timestamptz,
  unique (provider, provider_event_id)
);

create table if not exists public.email_outbox (
  id uuid primary key default gen_random_uuid(),
  recipient_email text not null,
  template text not null,
  template_data jsonb not null default '{}'::jsonb,
  dedupe_key text not null unique,
  status text not null default 'pending' check (status in ('pending', 'sending', 'sent', 'failed')),
  attempt_count integer not null default 0 check (attempt_count >= 0),
  last_error text,
  created_at timestamptz not null default now(),
  sent_at timestamptz
);

create table if not exists public.payment_refund_requests (
  id uuid primary key default gen_random_uuid(),
  payment_id uuid not null references public.listing_payments(id) on delete restrict,
  user_id uuid references public.profiles(id) on delete set null,
  reason text not null check (char_length(reason) between 10 and 1000),
  status text not null default 'requested' check (status in ('requested', 'approved', 'rejected', 'completed')),
  decision_note text,
  created_at timestamptz not null default now(),
  decided_at timestamptz,
  completed_at timestamptz
);

create unique index if not exists payment_refund_open_request_idx
  on public.payment_refund_requests (payment_id)
  where status in ('requested', 'approved');
create index if not exists email_outbox_pending_idx
  on public.email_outbox (status, created_at);

alter table public.payment_webhook_events enable row level security;
alter table public.email_outbox enable row level security;
alter table public.payment_refund_requests enable row level security;

revoke all on public.payment_webhook_events, public.email_outbox, public.payment_refund_requests
  from anon, authenticated;
grant all on public.payment_webhook_events, public.email_outbox, public.payment_refund_requests
  to service_role;
grant select on public.payment_refund_requests to authenticated;

drop policy if exists "Users can view own refund requests" on public.payment_refund_requests;
create policy "Users can view own refund requests" on public.payment_refund_requests
for select to authenticated using ((select auth.uid()) = user_id);

create or replace function public.enqueue_refund_email()
returns trigger
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_email text;
  v_template text;
begin
  select email into v_email from auth.users where id = new.user_id;
  if v_email is null then
    return new;
  end if;
  if tg_op = 'INSERT' then
    v_template := 'refund_request_received';
  elsif new.status is distinct from old.status and new.status in ('approved', 'rejected', 'completed') then
    v_template := 'refund_' || new.status;
  else
    return new;
  end if;
  insert into public.email_outbox (recipient_email, template, template_data, dedupe_key)
  values (
    v_email, v_template,
    jsonb_build_object('refund_request_id', new.id, 'payment_id', new.payment_id, 'status', new.status),
    v_template || ':' || new.id::text
  ) on conflict (dedupe_key) do nothing;
  return new;
end;
$$;

drop trigger if exists payment_refund_email_outbox on public.payment_refund_requests;
create trigger payment_refund_email_outbox
after insert or update of status on public.payment_refund_requests
for each row execute function public.enqueue_refund_email();

revoke all on function public.enqueue_refund_email() from public, anon, authenticated;

create or replace function public.process_placeholder_payment_webhook(
  p_event_id text,
  p_transaction_id text,
  p_vehicle_type text,
  p_listing_id text,
  p_status text,
  p_amount numeric,
  p_currency text,
  p_payload jsonb
) returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_payment public.listing_payments%rowtype;
  v_event_row_id uuid;
  v_email text;
  v_now timestamptz := now();
begin
  if p_vehicle_type not in ('bicycles', 'cars', 'motorbikes')
     or p_status not in ('paid', 'failed', 'refunded')
     or p_currency <> 'CHF' then
    raise exception 'Unsupported payment event';
  end if;

  select * into v_payment
  from public.listing_payments
  where vehicle_type = p_vehicle_type
    and listing_id = p_listing_id::uuid
  order by created_at desc
  limit 1
  for update;

  if not found then
    raise exception 'Payment not found';
  end if;
  if v_payment.amount <> p_amount or v_payment.currency <> p_currency then
    raise exception 'Payment amount or currency mismatch';
  end if;

  insert into public.payment_webhook_events (
    provider, provider_event_id, provider_transaction_id, event_status, payload
  ) values (
    'placeholder', p_event_id, p_transaction_id, p_status, p_payload
  ) on conflict (provider, provider_event_id) do nothing
  returning id into v_event_row_id;

  if v_event_row_id is null then
    return jsonb_build_object('processed', false, 'duplicate', true);
  end if;

  if p_status = 'paid' then
    update public.listing_payments
    set provider = 'placeholder', provider_transaction_id = p_transaction_id,
        provider_event_id = p_event_id, status = 'paid', paid_at = coalesce(paid_at, v_now),
        metadata = metadata || jsonb_build_object('last_event', p_payload)
    where id = v_payment.id;
    execute format(
      'update public.%I set payment_status = ''paid'', payment_reference = $1, paid_at = coalesce(paid_at, $2), updated_at = $2 where id = $3',
      p_vehicle_type
    ) using p_transaction_id, v_now, p_listing_id::uuid;

    select email into v_email from auth.users where id = v_payment.user_id;
    if v_email is not null then
      insert into public.email_outbox (recipient_email, template, template_data, dedupe_key)
      values (
        v_email,
        'payment_confirmation',
        jsonb_build_object(
          'payment_id', v_payment.id, 'listing_id', p_listing_id,
          'gross_amount', v_payment.amount, 'net_amount', v_payment.net_amount,
          'vat_amount', v_payment.vat_amount, 'vat_rate_percent', v_payment.vat_rate_percent,
          'currency', v_payment.currency, 'transaction_id', p_transaction_id
        ),
        'payment-confirmation:' || v_payment.id::text
      ) on conflict (dedupe_key) do nothing;
    end if;
  elsif p_status = 'failed' and v_payment.status = 'pending' then
    update public.listing_payments
    set provider = 'placeholder', provider_transaction_id = p_transaction_id,
        provider_event_id = p_event_id, status = 'failed',
        metadata = metadata || jsonb_build_object('last_event', p_payload)
    where id = v_payment.id;
    execute format(
      'update public.%I set payment_status = ''failed'', payment_reference = $1, updated_at = $2 where id = $3',
      p_vehicle_type
    ) using p_transaction_id, v_now, p_listing_id::uuid;
  elsif p_status = 'refunded' then
    if v_payment.status <> 'paid' then
      raise exception 'Only a paid payment can be refunded';
    end if;
    update public.listing_payments
    set provider_event_id = p_event_id, status = 'refunded', refunded_at = v_now,
        metadata = metadata || jsonb_build_object('last_event', p_payload)
    where id = v_payment.id;
    execute format(
      'update public.%I set payment_status = ''refunded'', status = case when status = ''active'' then ''suspended'' else status end, updated_at = $1 where id = $2',
      p_vehicle_type
    ) using v_now, p_listing_id::uuid;
    update public.payment_refund_requests
    set status = 'completed', completed_at = v_now
    where payment_id = v_payment.id and status in ('requested', 'approved');
  end if;

  update public.payment_webhook_events set processed_at = v_now where id = v_event_row_id;
  return jsonb_build_object('processed', true, 'duplicate', false, 'payment_status', p_status);
end;
$$;

revoke all on function public.process_placeholder_payment_webhook(text, text, text, text, text, numeric, text, jsonb)
  from public, anon, authenticated;
grant execute on function public.process_placeholder_payment_webhook(text, text, text, text, text, numeric, text, jsonb)
  to service_role;
