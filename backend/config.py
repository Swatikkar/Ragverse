import os

#paths
UPLOAD_DIR = "./uploads"
CHROMA_DIR = "./chroma_db"
CACHE_DIR = "./cache"

#models
EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "llama3.2"
VISION_MODEL = "qwen3-vl:2b"

#chunking
CHUNKING_STRATEGY = "recursive"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

#file details
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = [".pdf",".docx",".xlsx", ".csv"]

#retrieval
TOP_K_RESULTS = 8

for path in [UPLOAD_DIR, CHROMA_DIR, CACHE_DIR]:
    os.makedirs(path, exist_ok=True)