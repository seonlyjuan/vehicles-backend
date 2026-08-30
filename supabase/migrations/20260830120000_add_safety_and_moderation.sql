create table if not exists public.user_blocks (
  id uuid primary key default gen_random_uuid(),
  blocker_id uuid not null references public.profiles(id) on delete cascade,
  blocked_user_id uuid not null references public.profiles(id) on delete cascade,
  created_at timestamptz not null default now(),
  check (blocker_id <> blocked_user_id),
  unique (blocker_id, blocked_user_id)
);

create table if not exists public.content_reports (
  id uuid primary key default gen_random_uuid(),
  reporter_id uuid references public.profiles(id) on delete set null,
  subject_type text not null check (subject_type in ('listing', 'message', 'user')),
  vehicle_type text check (vehicle_type is null or vehicle_type in ('bicycles', 'cars', 'motorbikes')),
  listing_id uuid,
  message_id uuid references public.messages(id) on delete set null,
  reported_user_id uuid references public.profiles(id) on delete set null,
  reason text not null check (reason in ('fraud', 'stolen_vehicle', 'false_information', 'dealer_as_private', 'illegal_content', 'copyright', 'harassment', 'spam', 'other')),
  description text check (description is null or char_length(description) <= 2000),
  status text not null default 'open' check (status in ('open', 'reviewing', 'resolved', 'rejected')),
  priority text not null default 'normal' check (priority in ('normal', 'high', 'urgent')),
  moderator_id uuid references public.profiles(id) on delete set null,
  decision text check (decision is null or char_length(decision) <= 2000),
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  constraint content_reports_subject_check check (
    (subject_type = 'listing' and vehicle_type is not null and listing_id is not null)
    or subject_type = 'message'
    or (subject_type = 'user' and reported_user_id is not null)
  )
);

alter table public.content_reports drop constraint if exists content_reports_check;
alter table public.content_reports drop constraint if exists content_reports_subject_check;
alter table public.content_reports add constraint content_reports_subject_check check (
  (subject_type = 'listing' and vehicle_type is not null and listing_id is not null)
  or subject_type = 'message'
  or (subject_type = 'user' and reported_user_id is not null)
);

create table if not exists public.moderation_actions (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references public.profiles(id) on delete set null,
  action text not null,
  target_type text not null,
  target_id text not null,
  reason text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists user_blocks_blocker_idx on public.user_blocks (blocker_id, created_at desc);
create index if not exists user_blocks_blocked_idx on public.user_blocks (blocked_user_id, created_at desc);
create index if not exists content_reports_status_idx on public.content_reports (status, priority, created_at);
create index if not exists content_reports_reporter_idx on public.content_reports (reporter_id, created_at desc);
create index if not exists moderation_actions_target_idx on public.moderation_actions (target_type, target_id, created_at desc);

alter table public.user_blocks enable row level security;
alter table public.content_reports enable row level security;
alter table public.moderation_actions enable row level security;

drop policy if exists "Users can view own blocks" on public.user_blocks;
create policy "Users can view own blocks" on public.user_blocks
for select to authenticated using ((select auth.uid()) = blocker_id);
drop policy if exists "Users can create own blocks" on public.user_blocks;
create policy "Users can create own blocks" on public.user_blocks
for insert to authenticated with check ((select auth.uid()) = blocker_id);
drop policy if exists "Users can delete own blocks" on public.user_blocks;
create policy "Users can delete own blocks" on public.user_blocks
for delete to authenticated using ((select auth.uid()) = blocker_id);

drop policy if exists "Users can view own reports" on public.content_reports;
create policy "Users can view own reports" on public.content_reports
for select to authenticated using ((select auth.uid()) = reporter_id);
drop policy if exists "Users can create own reports" on public.content_reports;
create policy "Users can create own reports" on public.content_reports
for insert to authenticated with check ((select auth.uid()) = reporter_id);

alter table public.messages alter column sender_id drop not null;
alter table public.messages drop constraint if exists messages_sender_id_fkey;
alter table public.messages add constraint messages_sender_id_fkey
  foreign key (sender_id) references public.profiles(id) on delete set null;

alter table public.conversations alter column buyer_id drop not null;
alter table public.conversations alter column seller_id drop not null;
alter table public.conversations drop constraint if exists conversations_buyer_id_fkey;
alter table public.conversations drop constraint if exists conversations_seller_id_fkey;
alter table public.conversations add constraint conversations_buyer_id_fkey
  foreign key (buyer_id) references public.profiles(id) on delete set null;
alter table public.conversations add constraint conversations_seller_id_fkey
  foreign key (seller_id) references public.profiles(id) on delete set null;
