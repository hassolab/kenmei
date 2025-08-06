-- Function to create a profile entry when a new user signs up in auth.users
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, credits)
  values (new.id, 10); -- Match the default credits from the table definition
  return new;
end;
$$;

-- Trigger to call the function after a new user is inserted into auth.users
create or replace trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Optional: Grant usage on the function to postgres and anon roles if needed,
-- though security definer should handle permissions correctly.
-- grant execute on function public.handle_new_user() to postgres;
-- grant execute on function public.handle_new_user() to anon;
