-- Sahaay S0-06: core tables with row-level security (docs/ARCHITECTURE.md §9).
-- Apply in the Supabase SQL editor (or `supabase db push`). No files or full PII are ever stored.

create table if not exists public.profile_facts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  key text not null,
  value jsonb,
  source text not null check (source in ('user_said', 'form_input', 'document_extracted')),
  confirmed boolean not null default false,
  updated_at timestamptz not null default now(),
  unique (user_id, key)
);

create table if not exists public.cases (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  service_id text not null,
  journey_step int not null default 0,
  state_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.case_events (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  step int not null,
  note text,
  at timestamptz not null default now()
);

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  doc_type text not null,
  fields_masked_json jsonb not null default '{}'::jsonb,
  issue_date date,
  confirmed_at timestamptz
);

create table if not exists public.submissions (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.cases(id) on delete cascade,
  reference_no_masked text,
  submitted_on date
);

create table if not exists public.corrections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  service_id text not null,
  note text not null,
  status text not null default 'open',
  created_at timestamptz not null default now()
);

create table if not exists public.usage (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  day date not null,
  tokens_in bigint not null default 0,
  tokens_out bigint not null default 0,
  unique (user_id, day)
);

create index if not exists cases_user_idx on public.cases (user_id);
create index if not exists case_events_case_idx on public.case_events (case_id);
create index if not exists documents_case_idx on public.documents (case_id);
create index if not exists submissions_case_idx on public.submissions (case_id);

-- Row-level security: a user sees only their own rows. The backend uses the service
-- (secret) key, which bypasses RLS, and always filters by the user id from the verified JWT.
alter table public.profile_facts enable row level security;
alter table public.cases enable row level security;
alter table public.case_events enable row level security;
alter table public.documents enable row level security;
alter table public.submissions enable row level security;
alter table public.corrections enable row level security;
alter table public.usage enable row level security;

create policy "own facts" on public.profile_facts for all
  using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own cases" on public.cases for all
  using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own case events" on public.case_events for all
  using (exists (select 1 from public.cases c where c.id = case_id and c.user_id = auth.uid()))
  with check (exists (select 1 from public.cases c where c.id = case_id and c.user_id = auth.uid()));
create policy "own documents" on public.documents for all
  using (exists (select 1 from public.cases c where c.id = case_id and c.user_id = auth.uid()))
  with check (exists (select 1 from public.cases c where c.id = case_id and c.user_id = auth.uid()));
create policy "own submissions" on public.submissions for all
  using (exists (select 1 from public.cases c where c.id = case_id and c.user_id = auth.uid()))
  with check (exists (select 1 from public.cases c where c.id = case_id and c.user_id = auth.uid()));
create policy "own corrections" on public.corrections for all
  using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "own usage" on public.usage for select using (user_id = auth.uid());
