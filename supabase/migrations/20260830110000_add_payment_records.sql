create table if not exists public.listing_payments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete set null,
  vehicle_type text not null check (vehicle_type in ('bicycles', 'cars', 'motorbikes')),
  listing_id uuid not null,
  provider text not null default 'placeholder',
  provider_transaction_id text,
  provider_event_id text,
  status text not null default 'pending' check (status in ('pending', 'paid', 'failed', 'refunded')),
  amount numeric(12, 2) not null check (amount >= 0),
  currency text not null default 'CHF' check (currency = 'CHF'),
  created_at timestamptz not null default now(),
  paid_at timestamptz,
  refunded_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create unique index if not exists listing_payments_provider_transaction_idx
  on public.listing_payments (provider, provider_transaction_id)
  where provider_transaction_id is not null;
create unique index if not exists listing_payments_provider_event_idx
  on public.listing_payments (provider, provider_event_id)
  where provider_event_id is not null;
create index if not exists listing_payments_listing_idx
  on public.listing_payments (vehicle_type, listing_id, created_at desc);
create index if not exists listing_payments_user_idx
  on public.listing_payments (user_id, created_at desc);

alter table public.listing_payments enable row level security;

drop policy if exists "Users can view own listing payments" on public.listing_payments;
create policy "Users can view own listing payments" on public.listing_payments
for select to authenticated using ((select auth.uid()) = user_id);
