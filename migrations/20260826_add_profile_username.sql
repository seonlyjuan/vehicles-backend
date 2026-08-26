alter table public.profiles
add column if not exists username text;

create unique index if not exists profiles_username_unique
on public.profiles (lower(username))
where username is not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'profiles_username_format'
      and conrelid = 'public.profiles'::regclass
  ) then
    alter table public.profiles
    add constraint profiles_username_format
    check (username is null or username ~ '^[a-zA-Z0-9_]{3,30}$');
  end if;
end;
$$;

create or replace function public.set_username(requested_username text)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  normalized_username text := pg_catalog.lower(pg_catalog.btrim(requested_username));
begin
  if auth.uid() is null then
    raise exception 'Nicht angemeldet.' using errcode = '42501';
  end if;

  if normalized_username !~ '^[a-zA-Z0-9_]{3,30}$' then
    raise exception 'Ungültiger Username.' using errcode = '22023';
  end if;

  insert into public.profiles (id, username)
  values (auth.uid(), normalized_username)
  on conflict (id) do update
  set username = excluded.username
  returning username into normalized_username;

  return normalized_username;
end;
$$;

grant execute on function public.set_username(text) to authenticated;

do $$
begin
  if not exists (
    select 1
    from pg_policies
    where schemaname = 'public'
      and tablename = 'profiles'
      and policyname = 'Users can create their own profile'
  ) then
    create policy "Users can create their own profile"
    on public.profiles for insert
    to authenticated
    with check ((select auth.uid()) = id);
  end if;
end;
$$;
