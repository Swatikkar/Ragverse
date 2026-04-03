from config import ENV, EMBEDDING_MODEL

def get_embeddings():
    if ENV == "local":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model=EMBEDDING_MODEL
        )

    elif ENV == "production":
        from langchain_cohere import CohereEmbeddings
        from config import COHERE_API_KEY
        return CohereEmbeddings(
            model=EMBEDDING_MODEL,
            cohere_api_key=COHERE_API_KEY
        )