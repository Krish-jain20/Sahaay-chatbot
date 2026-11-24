-- Service cards (docs/DATA_SCHEMA.md §2 and §2a) as rows, so they can be edited without a code change.
-- Apply in the Supabase SQL editor (or `supabase db push`). Safe to run twice: it only creates what is missing
-- and never drops or deletes anything.
--
-- One row per service. `data` is the whole record exactly as in data/schemes/*.json (kind 'record') or
-- data/directory/*.json (kind 'directory'): names and summaries in en/hi/hn, every fact with its source_ref,
-- sources with URL and date_checked, fees, timeline, steps. Freshness is worked out from the source dates.
-- The backend validates every row on load and falls back to the repo files if anything is wrong or missing.

create table if not exists public.services (
  id text primary key,
  kind text not null check (kind in ('record', 'directory')),
  data jsonb not null,
  enabled boolean not null default true,
  updated_at timestamptz not null default now(),
  constraint services_id_matches_data check (data ->> 'id' = id)
);

create or replace function public.services_touch() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists services_touch on public.services;
create trigger services_touch before update on public.services
  for each row execute function public.services_touch();

-- Read-only for everyone (service information is public); writes only through the service role.
alter table public.services enable row level security;

drop policy if exists "services are public to read" on public.services;
create policy "services are public to read" on public.services
  for select to anon, authenticated using (enabled);

-- No insert, update or delete policies exist, so anon and signed-in users cannot write.
-- service_role bypasses row-level security and is what the backend and the seed script use.
grant usage on schema public to anon, authenticated, service_role;
grant select on public.services to anon, authenticated;
grant all on public.services to service_role;
revoke insert, update, delete on public.services from anon, authenticated;
