alter table public.bicycles
  add column if not exists model text check (model is null or char_length(model) between 1 and 80),
  add column if not exists year integer check (year between 1886 and 2100);

alter table public.cars
  add column if not exists power integer check (power between 0 and 5000);

alter table public.motorbikes
  add column if not exists power integer check (power between 0 and 5000);

create index if not exists bicycles_listing_filters_idx on public.bicycles (brand, model, year, price);
create index if not exists cars_listing_filters_idx on public.cars (brand, model, year, price, power);
create index if not exists motorbikes_listing_filters_idx on public.motorbikes (brand, model, year, price, power);
