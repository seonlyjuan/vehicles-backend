revoke insert, update, delete on public.profiles from authenticated;
revoke select on public.profiles from authenticated;
grant select (id, username, seller_type, company_name, dealer_verification_status)
  on public.profiles to authenticated;
revoke insert, update, delete on public.bicycles, public.cars, public.motorbikes from authenticated;
revoke insert, update, delete on public.vehicle_images from authenticated;
revoke insert, update, delete on public.conversations, public.messages from authenticated;
revoke insert, update, delete on public.user_blocks, public.content_reports from authenticated;
revoke all on public.moderation_actions from authenticated;
revoke all on public.listing_payments from authenticated;
grant select on public.listing_payments to authenticated;

grant select on public.vehicle_images to authenticated;
revoke select on public.bicycles, public.cars, public.motorbikes from authenticated;
grant select (
  id, profile_id, title, brand, model, year, price, description, status,
  created_at, updated_at, postal_code, locality, canton, condition,
  known_defects, mileage, first_registration, expires_at
) on public.bicycles to authenticated;
grant select (
  id, profile_id, title, brand, model, year, power, price, description, status,
  created_at, updated_at, postal_code, locality, canton, condition,
  known_defects, mileage, first_registration, expires_at
) on public.cars, public.motorbikes to authenticated;
grant select on public.conversations, public.messages, public.message_notifications to authenticated;
grant select on public.user_blocks, public.content_reports to authenticated;

drop policy if exists "Authenticated users can view bicycles" on public.bicycles;
drop policy if exists "Users can view active or own bicycles" on public.bicycles;
create policy "Users can view active or own bicycles" on public.bicycles
for select to authenticated using (status = 'active' or (select auth.uid()) = profile_id);

drop policy if exists "Authenticated users can view cars" on public.cars;
drop policy if exists "Users can view active or own cars" on public.cars;
create policy "Users can view active or own cars" on public.cars
for select to authenticated using (status = 'active' or (select auth.uid()) = profile_id);

drop policy if exists "Authenticated users can view motorbikes" on public.motorbikes;
drop policy if exists "Users can view active or own motorbikes" on public.motorbikes;
create policy "Users can view active or own motorbikes" on public.motorbikes
for select to authenticated using (status = 'active' or (select auth.uid()) = profile_id);

drop policy if exists "Authenticated users can view vehicle images" on public.vehicle_images;
drop policy if exists "Users can view active or own vehicle images" on public.vehicle_images;
create policy "Users can view active or own vehicle images" on public.vehicle_images
for select to authenticated using (
  (select auth.uid()) = profile_id
  or (vehicle_type = 'bicycles' and exists (
    select 1 from public.bicycles listing where listing.id = vehicle_id and listing.status = 'active'
  ))
  or (vehicle_type = 'cars' and exists (
    select 1 from public.cars listing where listing.id = vehicle_id and listing.status = 'active'
  ))
  or (vehicle_type = 'motorbikes' and exists (
    select 1 from public.motorbikes listing where listing.id = vehicle_id and listing.status = 'active'
  ))
);

drop policy if exists "Participants can create messages" on public.messages;
create policy "Participants can create messages" on public.messages
for insert to authenticated with check (
  sender_id = (select auth.uid())
  and exists (
    select 1 from public.conversations conversation
    where conversation.id = conversation_id
      and conversation.status = 'active'
      and (select auth.uid()) in (conversation.buyer_id, conversation.seller_id)
      and not exists (
        select 1 from public.user_blocks block
        where (block.blocker_id = conversation.buyer_id and block.blocked_user_id = conversation.seller_id)
           or (block.blocker_id = conversation.seller_id and block.blocked_user_id = conversation.buyer_id)
      )
  )
);

drop policy if exists "Users can upload own vehicle files" on storage.objects;
drop policy if exists "Users can update own vehicle files" on storage.objects;
drop policy if exists "Users can delete own vehicle files" on storage.objects;
drop policy if exists "Authenticated users can view private vehicle files" on storage.objects;
