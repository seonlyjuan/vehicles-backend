create table if not exists public.user_notifications (
  id uuid primary key default gen_random_uuid(),
  recipient_id uuid not null references public.profiles(id) on delete cascade,
  kind text not null check (kind in ('listing_expiring', 'listing_expired', 'moderation', 'dealer_review', 'appeal')),
  title text not null check (char_length(title) between 1 and 160),
  body text not null check (char_length(body) between 1 and 1000),
  link text check (link is null or char_length(link) <= 500),
  dedupe_key text not null,
  created_at timestamptz not null default now(),
  read_at timestamptz,
  unique (recipient_id, dedupe_key)
);

create index if not exists user_notifications_recipient_idx
  on public.user_notifications (recipient_id, created_at desc);
create index if not exists user_notifications_unread_idx
  on public.user_notifications (recipient_id, created_at desc) where read_at is null;

alter table public.user_notifications enable row level security;

drop policy if exists "Users can view own platform notifications" on public.user_notifications;
create policy "Users can view own platform notifications" on public.user_notifications
for select to authenticated using ((select auth.uid()) = recipient_id);

revoke insert, update, delete on public.user_notifications from authenticated;
grant select on public.user_notifications to authenticated;

do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime')
    and not exists (
      select 1 from pg_publication_tables
      where pubname = 'supabase_realtime'
        and schemaname = 'public'
        and tablename = 'user_notifications'
    )
  then
    alter publication supabase_realtime add table public.user_notifications;
  end if;
end;
$$;
