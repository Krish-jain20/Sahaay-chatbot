-- Newer Supabase projects do not give API roles access to tables created in the SQL editor.
-- The backend uses service_role (secret key); signed-in users (guests included) use authenticated.
-- Row-level security from 0001 still limits each signed-in user to their own rows.
grant usage on schema public to service_role, authenticated;

grant all on public.profile_facts, public.cases, public.case_events, public.documents,
  public.submissions, public.corrections, public.usage to service_role;

grant select, insert, update, delete on public.profile_facts, public.cases, public.case_events,
  public.documents, public.submissions, public.corrections to authenticated;
grant select on public.usage to authenticated;

-- Signed-out visitors get nothing.
revoke all on public.profile_facts, public.cases, public.case_events, public.documents,
  public.submissions, public.corrections, public.usage from anon;
