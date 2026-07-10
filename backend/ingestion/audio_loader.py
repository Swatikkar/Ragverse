import os

from langchain_core.documents import Document

from providers import model_router


def load_audio_transcript(file_path: str, doc_id: str) -> list[Document]:
    result = model_router.transcribe_audio(file_path)
    transcript = (result.get("text") or "").strip()
    if not transcript:
        raise ValueError("Audio transcription did not return any text.")

    return [
        Document(
            page_content=transcript,
            metadata={
                "doc_id": doc_id,
                "doc_name": os.path.basename(file_path),
                "file_type": os.path.splitext(file_path)[-1].lower(),
                "source_type": "audio",
                "language": result.get("language"),
                "source": os.path.basename(file_path),
            },
        )
    ]
