create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  vehicle_type text not null check (vehicle_type in ('bicycles', 'cars', 'motorbikes')),
  listing_id uuid not null,
  buyer_id uuid not null references public.profiles(id) on delete cascade,
  seller_id uuid not null references public.profiles(id) on delete cascade,
  status text not null default 'active' check (status in ('active', 'closed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (buyer_id <> seller_id),
  unique (vehicle_type, listing_id, buyer_id, seller_id)
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  sender_id uuid not null references public.profiles(id) on delete cascade,
  content text not null check (char_length(content) between 1 and 1000),
  created_at timestamptz not null default now()
);

create index if not exists conversations_buyer_idx on public.conversations (buyer_id, updated_at desc);
create index if not exists conversations_seller_idx on public.conversations (seller_id, updated_at desc);
create index if not exists messages_conversation_idx on public.messages (conversation_id, created_at desc);

alter table public.conversations enable row level security;
alter table public.messages enable row level security;

create policy "Participants can view conversations" on public.conversations
for select to authenticated using ((select auth.uid()) in (buyer_id, seller_id));

create policy "Participants can view messages" on public.messages
for select to authenticated using (
  exists (
    select 1 from public.conversations conversation
    where conversation.id = conversation_id
      and (select auth.uid()) in (conversation.buyer_id, conversation.seller_id)
  )
);

create policy "Participants can create messages" on public.messages
for insert to authenticated with check (
  sender_id = (select auth.uid())
  and exists (
    select 1 from public.conversations conversation
    where conversation.id = conversation_id
      and (select auth.uid()) in (conversation.buyer_id, conversation.seller_id)
  )
);
