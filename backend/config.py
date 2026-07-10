import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


def env_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    return value.strip().strip('"').strip("'").strip()


ENV = env_value("ENV", "local").lower()
IS_PRODUCTION = ENV == "production"
AUTH_PROVIDER = env_value("AUTH_PROVIDER", "supabase" if IS_PRODUCTION else "local").lower()
STORAGE_MODE = env_value("STORAGE_MODE", "supabase" if IS_PRODUCTION else "local").lower()
DATABASE_URL = env_value("DATABASE_URL")
SQLITE_DB_PATH = env_value("SQLITE_DB_PATH", "./data/ragverse.db")
SUPABASE_URL = env_value("SUPABASE_URL")
SUPABASE_KEY = env_value("SUPABASE_KEY")
SUPABASE_BUCKET = env_value("SUPABASE_BUCKET", "ragverse")

JWT_SECRET_KEY = env_value("JWT_SECRET_KEY")
JWT_ALGORITHM = env_value("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_MINUTES = int(env_value("JWT_EXPIRY_MINUTES", "120"))

UPLOAD_DIR = env_value("UPLOAD_DIR", "./uploads")
CHROMA_DIR = env_value("CHROMA_DIR", "./chroma_db")
CACHE_DIR = env_value("CACHE_DIR", "./cache")
EMBEDDING_DIMENSION = int(env_value("EMBEDDING_DIMENSION", "3072"))
ENABLE_RERANKER = env_value("ENABLE_RERANKER", "false").lower() == "true"

CHUNKING_STRATEGY = "recursive"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

MAX_FILE_SIZE_MB = int(env_value("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_AUDIO_SIZE_MB = int(env_value("MAX_AUDIO_SIZE_MB", "25"))
MAX_AUDIO_SIZE_BYTES = MAX_AUDIO_SIZE_MB * 1024 * 1024
MAX_URL_BYTES = int(env_value("MAX_URL_BYTES", "2000000"))
URL_TIMEOUT_SECONDS = float(env_value("URL_TIMEOUT_SECONDS", "10"))
URL_MAX_REDIRECTS = int(env_value("URL_MAX_REDIRECTS", "4"))

DOCUMENT_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".csv", ".pptx"]
AUDIO_EXTENSIONS = [".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4"]
ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS + AUDIO_EXTENSIONS

TOP_K_RESULTS = 8

RAG_CHAT_MODELS = env_value(
    "RAG_CHAT_MODELS",
    "groq:llama-3.3-70b-versatile,gemini:gemini-2.5-flash,ollama:llama3.2",
)
VISION_MODELS = env_value(
    "VISION_MODELS",
    "gemini:gemini-2.5-flash,ollama:qwen3-vl:2b",
)
TRANSCRIPTION_MODELS = env_value("TRANSCRIPTION_MODELS", "groq:whisper-large-v3-turbo")
EMBEDDING_MODELS = env_value(
    "EMBEDDING_MODELS",
    "gemini:gemini-embedding-001,cohere:embed-english-light-v3.0,ollama:nomic-embed-text",
)

OLLAMA_BASE_URL = env_value("OLLAMA_BASE_URL", "http://localhost:11434")
PROVIDER_TIMEOUT_SECONDS = float(env_value("PROVIDER_TIMEOUT_SECONDS", "30"))
PROVIDER_MAX_RETRIES = int(env_value("PROVIDER_MAX_RETRIES", "0"))
MODEL_TEMPERATURE = float(env_value("MODEL_TEMPERATURE", "0.1"))

GROQ_API_KEY = env_value("GROQ_API_KEY")
GEMINI_API_KEY = env_value("GEMINI_API_KEY")
COHERE_API_KEY = env_value("COHERE_API_KEY")

def resolve_backend_path(path: str) -> str:
    return path if os.path.isabs(path) else str(BASE_DIR / path)


SQLITE_DB_PATH = resolve_backend_path(SQLITE_DB_PATH)

for path in [UPLOAD_DIR, CHROMA_DIR, CACHE_DIR, os.path.dirname(SQLITE_DB_PATH) or "."]:
    os.makedirs(path, exist_ok=True)
