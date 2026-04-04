# import os
# from dotenv import load_dotenv

# load_dotenv()

# # Environment
# ENV = (os.getenv("ENV") or os.getenv("RAILWAY_ENVIRONMENT_NAME", "local")).lower()

# UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
# CHROMA_DIR = os.getenv("CHROMA_DIR", "/app/chroma_db")
# CACHE_DIR = os.getenv("CACHE_DIR", "/app/cache")

# # Paths
# UPLOAD_DIR = "./uploads"
# CHROMA_DIR = "./chroma_db"
# CACHE_DIR = "./cache"

# # Chunking
# CHUNKING_STRATEGY = "recursive"
# CHUNK_SIZE = 500
# CHUNK_OVERLAP = 50

# # Upload settings
# MAX_FILE_SIZE_MB = 10
# MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
# ALLOWED_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".csv", ".pptx"]

# # RAG settings
# TOP_K_RESULTS = 8

# if ENV == "local":
#     # Ollama local models
#     LLM_MODEL = "llama3.2"
#     VISION_MODEL = "qwen3-vl:2b"
#     EMBEDDING_MODEL = "nomic-embed-text"
#     # OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
#     # API keys not needed locally
#     GROQ_API_KEY = None
#     GEMINI_API_KEY = None
#     COHERE_API_KEY = None

# elif ENV == "production":
#     # Cloud free tier models
#     LLM_MODEL = "llama-3.3-70b-versatile"
#     VISION_MODEL = "gemini-2.5-flash"
#     EMBEDDING_MODEL = "embed-english-light-v3.0"
#     OLLAMA_BASE_URL = None

#     # API keys from environment
#     GROQ_API_KEY = os.getenv("GROQ_API_KEY")
#     GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
#     COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# # Create dirs if they don't exist
# for path in [UPLOAD_DIR, CHROMA_DIR, CACHE_DIR]:
#     os.makedirs(path, exist_ok=True)


import os
from dotenv import load_dotenv

load_dotenv()

ENV = (os.getenv("ENV") or os.getenv("RAILWAY_ENVIRONMENT_NAME", "local")).lower()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
CACHE_DIR = os.getenv("CACHE_DIR", "./cache")

CHUNKING_STRATEGY = "recursive"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".csv", ".pptx"]

TOP_K_RESULTS = 8

if ENV == "local":
    LLM_MODEL = "llama3.2"
    VISION_MODEL = "qwen3-vl:2b"
    EMBEDDING_MODEL = "nomic-embed-text"
    GROQ_API_KEY = None
    GEMINI_API_KEY = None
    COHERE_API_KEY = None
    # OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

elif ENV == "production":
    LLM_MODEL = "llama-3.3-70b-versatile"
    VISION_MODEL = "gemini-2.5-flash"
    EMBEDDING_MODEL = "embed-english-light-v3.0"
    OLLAMA_BASE_URL = None
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")

else:
    raise ValueError(f"Unsupported ENV: {ENV}")

for path in [UPLOAD_DIR, CHROMA_DIR, CACHE_DIR]:
    os.makedirs(path, exist_ok=True)