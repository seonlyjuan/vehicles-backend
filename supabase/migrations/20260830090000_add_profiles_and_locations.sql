alter table public.profiles
  add column if not exists seller_type text not null default 'private',
  add column if not exists platform_role text not null default 'user',
  add column if not exists account_status text not null default 'active',
  add column if not exists company_name text,
  add column if not exists business_address text,
  add column if not exists business_postal_code text,
  add column if not exists business_locality text,
  add column if not exists business_canton text,
  add column if not exists uid_number text,
  add column if not exists commercial_register_number text,
  add column if not exists business_email text,
  add column if not exists business_phone text,
  add column if not exists dealer_verification_status text not null default 'not_requested',
  add column if not exists dealer_verified_at timestamptz,
  add column if not exists deletion_requested_at timestamptz,
  add column if not exists updated_at timestamptz not null default now();

alter table public.profiles drop constraint if exists profiles_seller_type_check;
alter table public.profiles add constraint profiles_seller_type_check
  check (seller_type in ('private', 'dealer'));

alter table public.profiles drop constraint if exists profiles_platform_role_check;
alter table public.profiles add constraint profiles_platform_role_check
  check (platform_role in ('user', 'moderator', 'admin'));

alter table public.profiles drop constraint if exists profiles_account_status_check;
alter table public.profiles add constraint profiles_account_status_check
  check (account_status in ('active', 'deletion_requested', 'suspended'));

alter table public.profiles drop constraint if exists profiles_dealer_verification_check;
alter table public.profiles add constraint profiles_dealer_verification_check
  check (dealer_verification_status in ('not_requested', 'pending', 'verified', 'rejected', 'suspended'));

create table if not exists public.swiss_postal_codes (
  postal_code text not null check (postal_code ~ '^[1-9][0-9]{3}$'),
  locality text not null check (char_length(locality) between 1 and 120),
  canton text not null check (canton ~ '^[A-Z]{2}$'),
  primary key (postal_code, locality, canton)
);

create index if not exists swiss_postal_codes_search_idx
  on public.swiss_postal_codes (postal_code, locality);

alter table public.swiss_postal_codes enable row level security;

drop policy if exists "Authenticated users can view Swiss postal codes"
  on public.swiss_postal_codes;
create policy "Authenticated users can view Swiss postal codes"
  on public.swiss_postal_codes for select to authenticated using (true);

grant select on public.swiss_postal_codes to authenticated;
