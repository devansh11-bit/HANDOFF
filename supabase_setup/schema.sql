-- Run once in the Supabase SQL Editor before deploying HANDOFF.
-- The Streamlit server keeps SUPABASE_KEY server-side; it is never rendered
-- into the browser. This MVP uses project codes as invite tokens and does not
-- provide account authentication or fine-grained authorization.

create extension if not exists pgcrypto;

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text not null default '',
  project_code text not null unique,
  owner_name text not null default 'You',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.project_members (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  member_name text not null,
  member_identifier text not null,
  role text not null default 'member',
  joined_at timestamptz not null default now(),
  unique(project_id, member_identifier)
);
create table if not exists public.files (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  filename text not null, file_type text not null, path text not null,
  extracted_text text default '', uploaded_at timestamptz not null default now(),
  analysis_status text not null default 'Pending', analysis_error text default '',
  created_by text not null default 'You'
);
create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  role text not null, content text not null, member_name text not null default 'You',
  created_at timestamptz not null default now()
);
create table if not exists public.memory_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  category text not null, content text not null, source text default '',
  confidence double precision default 1, created_by text not null default 'You',
  created_at timestamptz not null default now(),
  unique(project_id, category, content)
);
create table if not exists public.decisions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  title text not null, description text default '', reason text default '',
  source text default '', added_by text not null default 'You',
  created_at timestamptz not null default now()
);
create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  title text not null, status text not null default 'Pending',
  assignee text default '', source text default '',
  created_by text not null default 'You', completed_by text,
  created_at timestamptz not null default now()
);
create table if not exists public.activity (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  event_type text not null, description text not null,
  member_name text not null default 'You', created_at timestamptz not null default now()
);

-- App server only: use the Supabase service role key as SUPABASE_KEY when
-- running this schema as written. Keep it in deployment secrets, never Git.
-- The anon key cannot bypass RLS and is intentionally not granted table access.
alter table public.projects enable row level security;
alter table public.project_members enable row level security;
alter table public.files enable row level security;
alter table public.messages enable row level security;
alter table public.memory_items enable row level security;
alter table public.decisions enable row level security;
alter table public.tasks enable row level security;
alter table public.activity enable row level security;

insert into storage.buckets (id, name, public)
values ('project-files', 'project-files', false)
on conflict (id) do nothing;
