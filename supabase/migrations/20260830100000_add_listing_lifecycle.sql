do $$
declare
  vehicle_table text;
begin
  foreach vehicle_table in array array['bicycles', 'cars', 'motorbikes']
  loop
    execute format('alter table public.%I drop constraint if exists %I', vehicle_table, vehicle_table || '_status_check');
    execute format(
      'alter table public.%I add constraint %I check (status in (''draft'', ''active'', ''sold'', ''archived'', ''expired'', ''suspended'', ''deleted''))',
      vehicle_table,
      vehicle_table || '_status_check'
    );
    execute format('alter table public.%I add column if not exists postal_code text', vehicle_table);
    execute format('alter table public.%I add column if not exists locality text', vehicle_table);
    execute format('alter table public.%I add column if not exists canton text', vehicle_table);
    execute format('alter table public.%I add column if not exists condition text', vehicle_table);
    execute format('alter table public.%I add column if not exists known_defects text', vehicle_table);
    execute format('alter table public.%I add column if not exists mileage integer', vehicle_table);
    execute format('alter table public.%I add column if not exists first_registration date', vehicle_table);
    execute format('alter table public.%I add column if not exists expires_at timestamptz', vehicle_table);
    execute format('alter table public.%I add column if not exists sold_at timestamptz', vehicle_table);
    execute format('alter table public.%I add column if not exists archived_at timestamptz', vehicle_table);
    execute format('alter table public.%I add column if not exists suspended_at timestamptz', vehicle_table);
    execute format('alter table public.%I add column if not exists deleted_at timestamptz', vehicle_table);
    execute format('alter table public.%I drop constraint if exists %I', vehicle_table, vehicle_table || '_postal_code_check');
    execute format(
      'alter table public.%I add constraint %I check (postal_code is null or postal_code ~ ''^[1-9][0-9]{3}$'')',
      vehicle_table,
      vehicle_table || '_postal_code_check'
    );
    execute format('alter table public.%I drop constraint if exists %I', vehicle_table, vehicle_table || '_canton_check');
    execute format(
      'alter table public.%I add constraint %I check (canton is null or canton ~ ''^[A-Z]{2}$'')',
      vehicle_table,
      vehicle_table || '_canton_check'
    );
    execute format('alter table public.%I drop constraint if exists %I', vehicle_table, vehicle_table || '_condition_check');
    execute format(
      'alter table public.%I add constraint %I check (condition is null or condition in (''new'', ''used'', ''damaged''))',
      vehicle_table,
      vehicle_table || '_condition_check'
    );
    execute format('alter table public.%I drop constraint if exists %I', vehicle_table, vehicle_table || '_mileage_check');
    execute format(
      'alter table public.%I add constraint %I check (mileage is null or mileage >= 0)',
      vehicle_table,
      vehicle_table || '_mileage_check'
    );
    execute format('alter table public.%I drop constraint if exists %I', vehicle_table, vehicle_table || '_known_defects_check');
    execute format(
      'alter table public.%I add constraint %I check (known_defects is null or char_length(known_defects) <= 5000)',
      vehicle_table,
      vehicle_table || '_known_defects_check'
    );
    execute format(
      'create index if not exists %I on public.%I (postal_code, canton, status)',
      vehicle_table || '_location_status_idx',
      vehicle_table
    );
    execute format(
      'create index if not exists %I on public.%I (profile_id, status, created_at desc)',
      vehicle_table || '_owner_status_idx',
      vehicle_table
    );
  end loop;
end $$;
