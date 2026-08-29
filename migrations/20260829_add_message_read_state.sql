alter table public.conversations
  add column if not exists buyer_last_read_at timestamptz,
  add column if not exists seller_last_read_at timestamptz;

create index if not exists conversations_buyer_unread_idx
  on public.conversations (buyer_id, buyer_last_read_at, updated_at desc);

create index if not exists conversations_seller_unread_idx
  on public.conversations (seller_id, seller_last_read_at, updated_at desc);
