create table if not exists public.users (
  id text primary key,
  email text not null unique,
  hashed_password text not null,
  full_name text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.documents (
  doc_id text primary key,
  user_id text not null references public.users(id) on delete cascade,
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
  user_id text not null references public.users(id) on delete cascade,
  artifact_type text not null,
  storage_path text,
  content_type text,
  size_bytes bigint not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists public.document_chunks (
  id bigserial primary key,
  doc_id text not null references public.documents(doc_id) on delete cascade,
  user_id text not null references public.users(id) on delete cascade,
  chunk_id text not null,
  chunk_index integer not null default 0,
  type text not null default 'text',
  text_preview text,
  created_at timestamptz not null default now(),
  unique (doc_id, chunk_id)
);

create index if not exists users_email_idx on public.users(email);
create index if not exists documents_user_id_idx on public.documents(user_id);
create index if not exists document_artifacts_user_doc_idx on public.document_artifacts(user_id, doc_id);
create index if not exists document_chunks_user_doc_idx on public.document_chunks(user_id, doc_id);
