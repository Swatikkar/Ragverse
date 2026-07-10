create extension if not exists vector with schema extensions;

create table if not exists public.users (
  id uuid primary key,
  email text not null unique,
  hashed_password text not null,
  full_name text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.documents (
  doc_id text primary key,
  user_id uuid not null references public.users(id) on delete cascade,
  doc_name text not null,
  source_type text not null default 'document',
  file_type text,
  source_url text,
  status text not null default 'indexed',
  storage_path text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.document_artifacts (
  id bigserial primary key,
  doc_id text not null references public.documents(doc_id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  artifact_type text not null,
  storage_path text,
  content_type text,
  size_bytes bigint not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists public.document_chunks (
  id bigserial primary key,
  doc_id text not null references public.documents(doc_id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  chunk_id text not null,
  chunk_index integer not null default 0,
  type text not null default 'text',
  content text,
  text_preview text,
  metadata jsonb not null default '{}'::jsonb,
  embedding extensions.vector(3072),
  created_at timestamptz not null default now(),
  unique (doc_id, chunk_id)
);

create table if not exists public.chat_sessions (
  session_id text primary key,
  user_id uuid not null references public.users(id) on delete cascade,
  title text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.chat_messages (
  id bigserial primary key,
  session_id text not null references public.chat_sessions(session_id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  sources jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.active_documents (
  session_id text not null references public.chat_sessions(session_id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  doc_id text not null references public.documents(doc_id) on delete cascade,
  doc_name text not null,
  activated_at timestamptz not null default now(),
  primary key (session_id, user_id, doc_id)
);

alter table public.document_chunks add column if not exists content text;
alter table public.document_chunks add column if not exists metadata jsonb not null default '{}'::jsonb;
alter table public.document_chunks add column if not exists embedding extensions.vector(3072);

create index if not exists users_email_idx on public.users(email);
create index if not exists documents_user_id_idx on public.documents(user_id);
create index if not exists document_artifacts_user_doc_idx on public.document_artifacts(user_id, doc_id);
create index if not exists document_chunks_user_doc_idx on public.document_chunks(user_id, doc_id);
create index if not exists document_chunks_embedding_idx on public.document_chunks using hnsw (embedding extensions.vector_cosine_ops);
create index if not exists chat_sessions_user_id_idx on public.chat_sessions(user_id);
create index if not exists chat_messages_session_idx on public.chat_messages(session_id, created_at);
create index if not exists active_documents_session_idx on public.active_documents(user_id, session_id);

create or replace function public.match_document_chunks(
  match_user_id uuid,
  match_doc_ids text[],
  query_embedding extensions.vector(3072),
  match_count int default 8
)
returns table (
  doc_id text,
  chunk_id text,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    dc.doc_id,
    dc.chunk_id,
    coalesce(dc.content, dc.text_preview, '') as content,
    dc.metadata,
    1 - (dc.embedding <=> query_embedding) as similarity
  from public.document_chunks dc
  where dc.user_id = match_user_id
    and dc.embedding is not null
    and (match_doc_ids is null or dc.doc_id = any(match_doc_ids))
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;

alter table public.users enable row level security;
alter table public.documents enable row level security;
alter table public.document_artifacts enable row level security;
alter table public.document_chunks enable row level security;
alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;
alter table public.active_documents enable row level security;
