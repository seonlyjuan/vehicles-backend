do $$
declare
  vehicle_table text;
begin
  foreach vehicle_table in array array['bicycles', 'cars', 'motorbikes']
  loop
    execute format('alter table public.%I drop constraint if exists %I', vehicle_table, vehicle_table || '_status_check');
    execute format(
      'alter table public.%I add constraint %I check (status in (''draft'', ''active'', ''sold'', ''archived''))',
      vehicle_table,
      vehicle_table || '_status_check'
    );
    execute format(
      'alter table public.%I add column if not exists payment_status text not null default ''paid'' check (payment_status in (''pending'', ''paid'', ''failed''))',
      vehicle_table
    );
    execute format('alter table public.%I add column if not exists payment_reference text', vehicle_table);
    execute format('alter table public.%I add column if not exists paid_at timestamptz', vehicle_table);
    execute format('alter table public.%I alter column payment_status set default ''pending''', vehicle_table);
    execute format('create index if not exists %I on public.%I (status, payment_status)', vehicle_table || '_publication_idx', vehicle_table);
  end loop;
end $$;
