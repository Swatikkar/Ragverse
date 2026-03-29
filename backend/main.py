# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apis.routes.upload import router as upload_router
from apis.routes.query import router as query_router
from config import UPLOAD_DIR
import os

app = FastAPI(
    title="RAGVerse API",
    description="Multimodal AI Research Assistant",
    version="1.0.0"
)

# CORS — allows Next.js frontend to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Serve uploaded images statically
# Frontend can access images via /uploads/{doc_id}/images/{filename}
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Routers
app.include_router(upload_router, prefix="/api", tags=["upload"])
app.include_router(query_router, prefix="/api", tags=["query"])

@app.get("/")
async def root():
    return {
        "message": "RAGVerse API is running",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}