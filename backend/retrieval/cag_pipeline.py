# from langchain_ollama import ChatOllama
# from langchain_core.messages import HumanMessage, SystemMessage
# from config import LLM_MODEL

# llm = ChatOllama(model=LLM_MODEL)

# SYSTEM_PROMPT = """You are RAGverse, an expert AI research assistant.
# Answer questions using ONLY the provided document context.
# Cite sources as [Source N] for every claim.
# If the answer is not in the context say so clearly."""

# def build_full_context(cached_docs: list) -> str:
#     context_blocks = []
#     for i, doc in enumerate(cached_docs):
#         context_blocks.append(
#             f"[Document {i+1}: {doc['doc_name']}]\n{doc['full_text']}"
#         )
#     return "\n\n---\n\n".join(context_blocks)

# def answer(question: str, cached_docs: list) -> dict:
#     if not cached_docs:
#         return {
#             "answer": "No cached documents found.",
#             "sources": []
#         }

#     # Build full context from cached docs
#     context = build_full_context(cached_docs)

#     messages = [
#         SystemMessage(content=SYSTEM_PROMPT),
#         HumanMessage(content=f"""FULL DOCUMENT CONTEXT:
# {context}

# QUESTION: {question}

# Answer with citations:""")
#     ]

#     response = llm.invoke(messages)

#     # Sources are entire docs not chunks
#     sources = [{
#         "doc_id": doc["doc_id"],
#         "doc_name": doc["doc_name"],
#         "type": "cached_document",
#         "image_path": None
#     } for doc in cached_docs]

#     return {
#         "answer": response.content,
#         "sources": sources
#     }