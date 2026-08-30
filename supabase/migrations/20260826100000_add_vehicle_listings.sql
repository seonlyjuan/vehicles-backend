create table if not exists public.bicycles (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles(id) on delete cascade,
  title text not null check (char_length(title) between 1 and 120),
  brand text not null check (char_length(brand) between 1 and 80),
  price numeric(12, 2) not null check (price >= 0),
  description text,
  status text not null default 'active' check (status in ('active', 'sold', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.cars (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles(id) on delete cascade,
  title text not null check (char_length(title) between 1 and 120),
  brand text not null check (char_length(brand) between 1 and 80),
  model text not null check (char_length(model) between 1 and 80),
  year integer check (year between 1886 and 2100),
  price numeric(12, 2) not null check (price >= 0),
  description text,
  status text not null default 'active' check (status in ('active', 'sold', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.motorbikes (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles(id) on delete cascade,
  title text not null check (char_length(title) between 1 and 120),
  brand text not null check (char_length(brand) between 1 and 80),
  model text not null check (char_length(model) between 1 and 80),
  year integer check (year between 1886 and 2100),
  price numeric(12, 2) not null check (price >= 0),
  description text,
  status text not null default 'active' check (status in ('active', 'sold', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.vehicle_images (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles(id) on delete cascade,
  vehicle_type text not null check (vehicle_type in ('bicycles', 'cars', 'motorbikes')),
  vehicle_id uuid not null,
  storage_path text not null unique,
  content_type text not null check (content_type in ('image/jpeg', 'image/png', 'image/webp')),
  sort_order integer not null default 0 check (sort_order >= 0),
  created_at timestamptz not null default now()
);

insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
) values (
  'vehicles-images',
  'vehicles-images',
  false,
  12582912,
  array['image/jpeg']
)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

create index if not exists vehicle_images_vehicle_idx
on public.vehicle_images (vehicle_type, vehicle_id, sort_order);

alter table public.bicycles enable row level security;
alter table public.cars enable row level security;
alter table public.motorbikes enable row level security;
alter table public.vehicle_images enable row level security;

create policy "Authenticated users can view bicycles" on public.bicycles for select to authenticated using (true);
create policy "Owners can create bicycles" on public.bicycles for insert to authenticated with check ((select auth.uid()) = profile_id);
create policy "Owners can update bicycles" on public.bicycles for update to authenticated using ((select auth.uid()) = profile_id) with check ((select auth.uid()) = profile_id);
create policy "Owners can delete bicycles" on public.bicycles for delete to authenticated using ((select auth.uid()) = profile_id);

create policy "Authenticated users can view cars" on public.cars for select to authenticated using (true);
create policy "Owners can create cars" on public.cars for insert to authenticated with check ((select auth.uid()) = profile_id);
create policy "Owners can update cars" on public.cars for update to authenticated using ((select auth.uid()) = profile_id) with check ((select auth.uid()) = profile_id);
create policy "Owners can delete cars" on public.cars for delete to authenticated using ((select auth.uid()) = profile_id);

create policy "Authenticated users can view motorbikes" on public.motorbikes for select to authenticated using (true);
create policy "Owners can create motorbikes" on public.motorbikes for insert to authenticated with check ((select auth.uid()) = profile_id);
create policy "Owners can update motorbikes" on public.motorbikes for update to authenticated using ((select auth.uid()) = profile_id) with check ((select auth.uid()) = profile_id);
create policy "Owners can delete motorbikes" on public.motorbikes for delete to authenticated using ((select auth.uid()) = profile_id);

create policy "Authenticated users can view vehicle images" on public.vehicle_images for select to authenticated using (true);
create policy "Owners can create vehicle images" on public.vehicle_images for insert to authenticated with check ((select auth.uid()) = profile_id);
create policy "Owners can update vehicle images" on public.vehicle_images for update to authenticated using ((select auth.uid()) = profile_id) with check ((select auth.uid()) = profile_id);
create policy "Owners can delete vehicle images" on public.vehicle_images for delete to authenticated using ((select auth.uid()) = profile_id);

create policy "Authenticated users can view private vehicle files"
on storage.objects for select to authenticated
using (bucket_id = 'vehicles-images');

create policy "Users can upload own vehicle files"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'vehicles-images'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

create policy "Users can update own vehicle files"
on storage.objects for update to authenticated
using (
  bucket_id = 'vehicles-images'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
)
with check (
  bucket_id = 'vehicles-images'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);

create policy "Users can delete own vehicle files"
on storage.objects for delete to authenticated
using (
  bucket_id = 'vehicles-images'
  and (storage.foldername(name))[1] = (select auth.uid()::text)
);
