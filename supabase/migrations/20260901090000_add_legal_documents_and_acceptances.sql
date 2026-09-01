create table if not exists public.legal_documents (
  id uuid primary key default gen_random_uuid(),
  document_type text not null check (document_type in ('terms', 'privacy', 'imprint')),
  version text not null check (char_length(version) between 1 and 40),
  display_version text not null check (char_length(display_version) between 1 and 80),
  language text not null default 'de' check (language ~ '^[a-z]{2}$'),
  title text not null check (char_length(title) between 1 and 160),
  public_path text not null check (public_path like '/legal/%'),
  content_sha256 text not null check (content_sha256 ~ '^[0-9a-f]{64}$'),
  status text not null default 'draft' check (status in ('draft', 'published', 'retired')),
  effective_from timestamptz,
  created_at timestamptz not null default now(),
  unique (document_type, version, language)
);

create table if not exists public.legal_acceptances (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete set null,
  document_id uuid not null references public.legal_documents(id) on delete restrict,
  document_version text not null check (char_length(document_version) between 1 and 40),
  document_sha256 text not null check (document_sha256 ~ '^[0-9a-f]{64}$'),
  context text not null check (char_length(context) between 1 and 80),
  vehicle_type text not null check (vehicle_type in ('bicycles', 'cars', 'motorbikes')),
  listing_id uuid not null,
  accepted_at timestamptz not null default now(),
  unique (user_id, document_id, context, vehicle_type, listing_id)
);

create index if not exists legal_documents_current_idx
  on public.legal_documents (document_type, language, status, effective_from desc);

create index if not exists legal_acceptances_user_idx
  on public.legal_acceptances (user_id, accepted_at desc);

create index if not exists legal_acceptances_listing_idx
  on public.legal_acceptances (vehicle_type, listing_id, accepted_at desc);

alter table public.legal_documents enable row level security;
alter table public.legal_acceptances enable row level security;

drop policy if exists "Users can view own legal acceptances" on public.legal_acceptances;
create policy "Users can view own legal acceptances"
on public.legal_acceptances for select
to authenticated
using ((select auth.uid()) = user_id);

revoke all on public.legal_documents from anon, authenticated;
revoke all on public.legal_acceptances from anon, authenticated;
grant select on public.legal_acceptances to authenticated;

insert into public.legal_documents (
  document_type,
  version,
  display_version,
  language,
  title,
  public_path,
  content_sha256,
  status
) values (
  'terms',
  '0.1-draft',
  'Entwurf 0.1',
  'de',
  'Allgemeine Geschäftsbedingungen',
  '/legal/agb',
  '8b4f955128b0dc2990a3062e24a70aaf0a1fa39afe87c4eb03089b430f796435',
  'draft'
)
on conflict (document_type, version, language) do nothing;
