create or replace function public.match_document_chunks_for_docs(
  match_user_id uuid,
  match_doc_ids text[],
  query_embedding extensions.vector(3072),
  per_doc_count int default 2
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
  with ranked as (
    select
      dc.doc_id,
      dc.chunk_id,
      coalesce(dc.content, dc.text_preview, '') as content,
      dc.metadata,
      1 - (dc.embedding <=> query_embedding) as similarity,
      row_number() over (
        partition by dc.doc_id
        order by dc.embedding <=> query_embedding
      ) as document_rank
    from public.document_chunks dc
    where dc.user_id = match_user_id
      and dc.embedding is not null
      and dc.doc_id = any(match_doc_ids)
  )
  select
    ranked.doc_id,
    ranked.chunk_id,
    ranked.content,
    ranked.metadata,
    ranked.similarity
  from ranked
  where ranked.document_rank <= greatest(per_doc_count, 1)
  order by ranked.similarity desc;
$$;

create or replace function public.append_chat_message(message_row jsonb)
returns void
language plpgsql
as $$
begin
  insert into public.chat_messages (session_id, user_id, role, content, sources)
  values (
    message_row->>'session_id',
    (message_row->>'user_id')::uuid,
    message_row->>'role',
    message_row->>'content',
    coalesce(message_row->'sources', '[]'::jsonb)
  );

  update public.chat_sessions
  set updated_at = now()
  where session_id = message_row->>'session_id'
    and user_id = (message_row->>'user_id')::uuid;
end;
$$;
