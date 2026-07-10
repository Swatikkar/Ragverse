from __future__ import annotations

import time
from dataclasses import dataclass
from langchain_core.messages import AIMessage, BaseMessage

import config


ROLE_TO_SETTING = {
    "rag_chat": "RAG_CHAT_MODELS",
    "vision": "VISION_MODELS",
    "embedding": "EMBEDDING_MODELS",
    "transcription": "TRANSCRIPTION_MODELS",
}


class ProviderError(Exception):
    def __init__(self, provider: str, model: str, message: str):
        super().__init__(message)
        self.provider = provider
        self.model = model


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"


def parse_routes(raw: str) -> list[ModelRoute]:
    routes = []
    for item in (raw or "").split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        provider, model = item.split(":", 1)
        routes.append(ModelRoute(provider.strip().lower(), model.strip()))
    return routes


def _short_error(exc: Exception, limit: int = 400) -> str:
    message = str(exc).replace("\n", " ").strip()
    return message[:limit] + ("..." if len(message) > limit else "")


def _log(message: str):
    print(f"[model-router] {message}", flush=True)


class ModelRouter:
    def routes_for_role(self, role: str) -> list[ModelRoute]:
        setting_name = ROLE_TO_SETTING.get(role, "RAG_CHAT_MODELS")
        return parse_routes(getattr(config, setting_name))

    def llm_for_route(self, route: ModelRoute, streaming: bool = False):
        if route.provider == "groq":
            if not config.GROQ_API_KEY:
                raise ProviderError(route.provider, route.model, "GROQ_API_KEY is not configured.")
            from langchain_groq import ChatGroq

            return ChatGroq(
                model=route.model,
                api_key=config.GROQ_API_KEY,
                temperature=config.MODEL_TEMPERATURE,
                timeout=config.PROVIDER_TIMEOUT_SECONDS,
                max_retries=config.PROVIDER_MAX_RETRIES,
                streaming=streaming,
            )

        if route.provider == "gemini":
            if not config.GEMINI_API_KEY:
                raise ProviderError(route.provider, route.model, "GEMINI_API_KEY is not configured.")
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=route.model,
                google_api_key=config.GEMINI_API_KEY,
                temperature=config.MODEL_TEMPERATURE,
                timeout=config.PROVIDER_TIMEOUT_SECONDS,
            )

        if route.provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=route.model,
                base_url=config.OLLAMA_BASE_URL,
                temperature=config.MODEL_TEMPERATURE,
                keep_alive=300,
                streaming=streaming,
            )

        raise ProviderError(route.provider, route.model, f"Unsupported chat provider: {route.provider}")

    def invoke_chat(self, role: str, messages: list[BaseMessage]) -> tuple[AIMessage, dict]:
        errors = []
        for route in self.routes_for_role(role):
            started = time.perf_counter()
            try:
                _log(f"{role}: trying {route.label}")
                response = self.llm_for_route(route).invoke(messages)
                elapsed = round(time.perf_counter() - started, 2)
                return response, {"provider": route.provider, "model": route.model, "elapsed_seconds": elapsed, "fallback_errors": errors}
            except Exception as exc:
                elapsed = round(time.perf_counter() - started, 2)
                errors.append({"provider": route.provider, "model": route.model, "elapsed_seconds": elapsed, "error": _short_error(exc)})
                _log(f"{role}: {route.label} failed after {elapsed}s")

        return AIMessage(content="All configured model providers failed."), {"provider": "none", "model": "none", "fallback_errors": errors}

    async def stream_chat(self, role: str, messages: list[BaseMessage]):
        errors = []
        for route in self.routes_for_role(role):
            started = time.perf_counter()
            try:
                _log(f"{role}: streaming {route.label}")
                llm = self.llm_for_route(route, streaming=True)
                yield {"type": "provider_switch", "provider": route.provider, "model": route.model}
                async for chunk in llm.astream(messages):
                    content = getattr(chunk, "content", "")
                    if content:
                        yield {"type": "chunk", "content": content}
                elapsed = round(time.perf_counter() - started, 2)
                _log(f"{role}: stream success {route.label} in {elapsed}s")
                return
            except Exception as exc:
                elapsed = round(time.perf_counter() - started, 2)
                error = _short_error(exc)
                errors.append({"provider": route.provider, "model": route.model, "elapsed_seconds": elapsed, "error": error})
                yield {"type": "provider_switch", "provider": route.provider, "model": route.model, "error": error}

        yield {"type": "error", "content": "All configured model providers failed.", "errors": errors}

    def embeddings(self):
        errors = []
        for route in self.routes_for_role("embedding"):
            try:
                if route.provider == "gemini":
                    if not config.GEMINI_API_KEY:
                        raise ProviderError(route.provider, route.model, "GEMINI_API_KEY is not configured.")
                    from langchain_google_genai import GoogleGenerativeAIEmbeddings

                    return GoogleGenerativeAIEmbeddings(model=route.model, google_api_key=config.GEMINI_API_KEY)

                if route.provider == "cohere":
                    if not config.COHERE_API_KEY:
                        raise ProviderError(route.provider, route.model, "COHERE_API_KEY is not configured.")
                    from langchain_cohere import CohereEmbeddings

                    return CohereEmbeddings(model=route.model, cohere_api_key=config.COHERE_API_KEY)

                if route.provider == "ollama":
                    from langchain_ollama import OllamaEmbeddings

                    return OllamaEmbeddings(model=route.model, base_url=config.OLLAMA_BASE_URL)
            except Exception as exc:
                errors.append(f"{route.label}: {_short_error(exc)}")

        raise ProviderError("embedding", "none", "No embedding provider is configured. " + " | ".join(errors))

    def transcribe_audio(self, file_path: str) -> dict:
        errors = []
        for route in self.routes_for_role("transcription"):
            try:
                if route.provider != "groq":
                    raise ProviderError(route.provider, route.model, "Only Groq transcription is supported for now.")
                if not config.GROQ_API_KEY:
                    raise ProviderError(route.provider, route.model, "GROQ_API_KEY is not configured.")

                from groq import Groq

                client = Groq(api_key=config.GROQ_API_KEY)
                with open(file_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        file=audio_file,
                        model=route.model,
                        response_format="verbose_json",
                    )
                if isinstance(transcript, dict):
                    text = transcript.get("text", "")
                    language = transcript.get("language")
                else:
                    text = getattr(transcript, "text", "")
                    language = getattr(transcript, "language", None)
                return {
                    "text": text,
                    "language": language,
                    "provider": route.provider,
                    "model": route.model,
                }
            except Exception as exc:
                errors.append({"provider": route.provider, "model": route.model, "error": _short_error(exc)})

        raise ProviderError("transcription", "none", f"Audio transcription failed: {errors}")


model_router = ModelRouter()
