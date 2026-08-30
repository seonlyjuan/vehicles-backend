create table if not exists public.message_notifications (
  id uuid primary key default gen_random_uuid(),
  recipient_id uuid not null references public.profiles(id) on delete cascade,
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  message_id uuid references public.messages(id) on delete set null,
  kind text not null check (kind in ('new_conversation', 'new_message')),
  created_at timestamptz not null default now(),
  read_at timestamptz
);

create unique index if not exists message_notifications_conversation_idx
  on public.message_notifications (recipient_id, conversation_id);

create index if not exists message_notifications_recipient_idx
  on public.message_notifications (recipient_id, created_at desc);

create index if not exists message_notifications_unread_idx
  on public.message_notifications (recipient_id, conversation_id)
  where read_at is null;

alter table public.message_notifications enable row level security;

drop policy if exists "Recipients can view message notifications"
  on public.message_notifications;

create policy "Recipients can view message notifications"
  on public.message_notifications
  for select
  to authenticated
  using ((select auth.uid()) = recipient_id);

grant select on public.messages, public.message_notifications to authenticated;

create or replace function public.notify_new_conversation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.message_notifications (
    recipient_id,
    conversation_id,
    kind
  ) values (
    new.seller_id,
    new.id,
    'new_conversation'
  )
  on conflict (recipient_id, conversation_id) do update
  set message_id = null,
      kind = excluded.kind,
      created_at = now(),
      read_at = null;
  return new;
end;
$$;

drop trigger if exists conversation_notification_trigger
  on public.conversations;

create trigger conversation_notification_trigger
after insert on public.conversations
for each row execute function public.notify_new_conversation();

create or replace function public.notify_new_message()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  recipient uuid;
begin
  select case
    when new.sender_id = conversation.buyer_id then conversation.seller_id
    when new.sender_id = conversation.seller_id then conversation.buyer_id
  end
  into recipient
  from public.conversations as conversation
  where conversation.id = new.conversation_id;

  if recipient is not null then
    insert into public.message_notifications (
      recipient_id,
      conversation_id,
      message_id,
      kind
    ) values (
      recipient,
      new.conversation_id,
      new.id,
      'new_message'
    )
    on conflict (recipient_id, conversation_id) do update
    set message_id = excluded.message_id,
        kind = excluded.kind,
        created_at = now(),
        read_at = null;
  end if;

  return new;
end;
$$;

drop trigger if exists message_notification_trigger
  on public.messages;

create trigger message_notification_trigger
after insert on public.messages
for each row execute function public.notify_new_message();

insert into public.message_notifications (
  recipient_id,
  conversation_id,
  message_id,
  kind,
  created_at
)
select
  conversation.buyer_id,
  conversation.id,
  latest_message.id,
  'new_message',
  latest_message.created_at
from public.conversations as conversation
join lateral (
  select message.id, message.created_at
  from public.messages as message
  where message.conversation_id = conversation.id
    and message.sender_id <> conversation.buyer_id
  order by message.created_at desc
  limit 1
) as latest_message on true
where conversation.buyer_last_read_at is null
   or latest_message.created_at > conversation.buyer_last_read_at
on conflict (recipient_id, conversation_id) do update
set message_id = excluded.message_id,
    kind = excluded.kind,
    created_at = excluded.created_at,
    read_at = null;

insert into public.message_notifications (
  recipient_id,
  conversation_id,
  message_id,
  kind,
  created_at
)
select
  conversation.seller_id,
  conversation.id,
  latest_message.id,
  'new_message',
  latest_message.created_at
from public.conversations as conversation
join lateral (
  select message.id, message.created_at
  from public.messages as message
  where message.conversation_id = conversation.id
    and message.sender_id <> conversation.seller_id
  order by message.created_at desc
  limit 1
) as latest_message on true
where conversation.seller_last_read_at is null
   or latest_message.created_at > conversation.seller_last_read_at
on conflict (recipient_id, conversation_id) do update
set message_id = excluded.message_id,
    kind = excluded.kind,
    created_at = excluded.created_at,
    read_at = null;

insert into public.message_notifications (
  recipient_id,
  conversation_id,
  kind,
  created_at
)
select
  conversation.seller_id,
  conversation.id,
  'new_conversation',
  conversation.created_at
from public.conversations as conversation
where conversation.seller_last_read_at is null
  and not exists (
    select 1
    from public.messages as message
    where message.conversation_id = conversation.id
  )
on conflict (recipient_id, conversation_id) do nothing;

do $$
begin
  if exists (
    select 1 from pg_publication where pubname = 'supabase_realtime'
  ) then
    if not exists (
      select 1
      from pg_publication_tables
      where pubname = 'supabase_realtime'
        and schemaname = 'public'
        and tablename = 'messages'
    ) then
      alter publication supabase_realtime add table public.messages;
    end if;

    if not exists (
      select 1
      from pg_publication_tables
      where pubname = 'supabase_realtime'
        and schemaname = 'public'
        and tablename = 'message_notifications'
    ) then
      alter publication supabase_realtime add table public.message_notifications;
    end if;
  end if;
end;
$$;
