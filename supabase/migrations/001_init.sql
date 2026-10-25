-- Job Hunt Agent schema
-- Run in Supabase SQL Editor (Dashboard → SQL → New query).
-- Skip Vercel's Supabase integration; use Project Settings → API Keys → Secret keys (sb_secret_...).

create extension if not exists "pgcrypto";

-- Resumes pasted/uploaded by the candidate
create table if not exists public.resumes (
  id uuid primary key default gen_random_uuid(),
  title text not null default 'My Resume',
  content text not null,
  skills jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Cached job search results (TTL enforced in API)
create table if not exists public.jobs_cache (
  cache_key text primary key,
  jobs jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

-- Application tracker
create table if not exists public.tracker (
  id uuid primary key default gen_random_uuid(),
  job_id text not null,
  title text not null,
  company text not null,
  apply_url text not null,
  source text not null check (source in ('Himalayas', 'Jobicy', 'JSearch')),
  status text not null default 'saved'
    check (status in ('saved', 'applied', 'interview', 'offer', 'rejected')),
  score int check (score is null or (score >= 0 and score <= 100)),
  notes text,
  cover_letter text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists tracker_status_idx on public.tracker (status);
create index if not exists tracker_updated_idx on public.tracker (updated_at desc);

-- Agent run traces
create table if not exists public.agent_runs (
  id uuid primary key default gen_random_uuid(),
  query text,
  resume_id uuid references public.resumes (id) on delete set null,
  status text not null default 'running',
  steps jsonb not null default '[]'::jsonb,
  result jsonb not null default '{}'::jsonb,
  model_used text,
  duration_ms int,
  created_at timestamptz not null default now()
);

create index if not exists agent_runs_created_idx on public.agent_runs (created_at desc);

-- Service role key bypasses RLS; enable RLS anyway for defense in depth.
alter table public.resumes enable row level security;
alter table public.jobs_cache enable row level security;
alter table public.tracker enable row level security;
alter table public.agent_runs enable row level security;

-- No anon policies — API uses service role (secret) key only.
