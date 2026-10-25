-- Auth + RBAC for job-hunt-agent (shared with rag-doc-chatbot via user_roles).
-- Idempotent: safe to re-run. Uses the same user_roles definition as rag-doc-chatbot.

-- Shared roles table (identical definition in rag-doc-chatbot repo)
create table if not exists public.user_roles (
  user_id uuid references auth.users on delete cascade,
  app text check (app in ('rag-doc-chatbot', 'job-hunt-agent')),
  role text check (role in ('admin', 'client')),
  primary key (user_id, app)
);

create index if not exists user_roles_app_idx on public.user_roles (app);
create index if not exists user_roles_role_idx on public.user_roles (role);

alter table public.user_roles enable row level security;

-- Ownership columns (jobs_cache stays shared — no user_id)
alter table public.resumes
  add column if not exists user_id uuid references auth.users (id) on delete cascade;

alter table public.tracker
  add column if not exists user_id uuid references auth.users (id) on delete cascade;

alter table public.agent_runs
  add column if not exists user_id uuid references auth.users (id) on delete set null;

create index if not exists resumes_user_id_idx on public.resumes (user_id);
create index if not exists tracker_user_id_idx on public.tracker (user_id);
create index if not exists agent_runs_user_id_idx on public.agent_runs (user_id);

-- Helper: current JWT role for this app (used by RLS)
create or replace function public.current_app_role(p_app text)
returns text
language sql
stable
security definer
set search_path = public
as $$
  select role
  from public.user_roles
  where user_id = auth.uid()
    and app = p_app
  limit 1;
$$;

-- RLS: user_roles — users can read their own rows; writes via service role only
drop policy if exists user_roles_select_own on public.user_roles;
create policy user_roles_select_own on public.user_roles
  for select
  using (user_id = auth.uid());

-- RLS: resumes — own rows for clients; all for admin of job-hunt-agent
drop policy if exists resumes_select on public.resumes;
create policy resumes_select on public.resumes
  for select
  using (
    user_id = auth.uid()
    or public.current_app_role('job-hunt-agent') = 'admin'
  );

drop policy if exists resumes_insert on public.resumes;
create policy resumes_insert on public.resumes
  for insert
  with check (
    user_id = auth.uid()
    or public.current_app_role('job-hunt-agent') = 'admin'
  );

drop policy if exists resumes_update on public.resumes;
create policy resumes_update on public.resumes
  for update
  using (
    user_id = auth.uid()
    or public.current_app_role('job-hunt-agent') = 'admin'
  );

drop policy if exists resumes_delete on public.resumes;
create policy resumes_delete on public.resumes
  for delete
  using (
    user_id = auth.uid()
    or public.current_app_role('job-hunt-agent') = 'admin'
  );

-- RLS: tracker
drop policy if exists tracker_select on public.tracker;
create policy tracker_select on public.tracker
  for select
  using (
    user_id = auth.uid()
    or public.current_app_role('job-hunt-agent') = 'admin'
  );

drop policy if exists tracker_insert on public.tracker;
create policy tracker_insert on public.tracker
  for insert
  with check (
    user_id = auth.uid()
    or public.current_app_role('job-hunt-agent') = 'admin'
  );

drop policy if exists tracker_update on public.tracker;
create policy tracker_update on public.tracker
  for update
  using (
    user_id = auth.uid()
    or public.current_app_role('job-hunt-agent') = 'admin'
  );

drop policy if exists tracker_delete on public.tracker;
create policy tracker_delete on public.tracker
  for delete
  using (
    user_id = auth.uid()
    or public.current_app_role('job-hunt-agent') = 'admin'
  );

-- RLS: agent_runs
drop policy if exists agent_runs_select on public.agent_runs;
create policy agent_runs_select on public.agent_runs
  for select
  using (
    user_id = auth.uid()
    or public.current_app_role('job-hunt-agent') = 'admin'
  );

drop policy if exists agent_runs_insert on public.agent_runs;
create policy agent_runs_insert on public.agent_runs
  for insert
  with check (
    user_id = auth.uid()
    or public.current_app_role('job-hunt-agent') = 'admin'
  );

drop policy if exists agent_runs_update on public.agent_runs;
create policy agent_runs_update on public.agent_runs
  for update
  using (
    user_id = auth.uid()
    or public.current_app_role('job-hunt-agent') = 'admin'
  );

-- jobs_cache remains shared (no per-user policies beyond existing RLS with no anon grants).
