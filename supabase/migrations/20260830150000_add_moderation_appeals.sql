create table if not exists public.moderation_appeals (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references public.content_reports(id) on delete cascade,
  appellant_id uuid references public.profiles(id) on delete set null,
  statement text not null check (char_length(statement) between 10 and 2000),
  status text not null default 'open' check (status in ('open', 'accepted', 'rejected')),
  reviewer_id uuid references public.profiles(id) on delete set null,
  decision text check (decision is null or char_length(decision) <= 2000),
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  unique (report_id, appellant_id)
);

create index if not exists moderation_appeals_status_idx
  on public.moderation_appeals (status, created_at);

alter table public.moderation_appeals enable row level security;

drop policy if exists "Users can view own moderation appeals" on public.moderation_appeals;
create policy "Users can view own moderation appeals" on public.moderation_appeals
for select to authenticated using ((select auth.uid()) = appellant_id);

revoke insert, update, delete on public.moderation_appeals from authenticated;
grant select on public.moderation_appeals to authenticated;
