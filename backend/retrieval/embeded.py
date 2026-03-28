from langchain_ollama import OllamaEmbeddings
from config import EMBEDDING_MODEL

embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

def get_embeddings():
    
    return embeddings