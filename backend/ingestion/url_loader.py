from __future__ import annotations

from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException
from langchain_core.documents import Document

from config import MAX_URL_BYTES, URL_MAX_REDIRECTS, URL_TIMEOUT_SECONDS
from utils.security import sanitize_name, validate_public_url


def _fetch_url(url: str) -> tuple[str, str]:
    current_url = validate_public_url(url)
    session = requests.Session()
    headers = {"User-Agent": "RagverseBot/1.0"}

    for _ in range(URL_MAX_REDIRECTS + 1):
        response = session.get(
            current_url,
            headers=headers,
            timeout=URL_TIMEOUT_SECONDS,
            allow_redirects=False,
            stream=True,
        )
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            if not location:
                raise HTTPException(status_code=400, detail="URL redirect is missing a target.")
            current_url = validate_public_url(requests.compat.urljoin(current_url, location))
            continue

        content_type = response.headers.get("content-type", "").lower()
        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"URL returned status {response.status_code}.")
        if "text/html" not in content_type and "text/plain" not in content_type:
            raise HTTPException(status_code=400, detail="URL must point to readable HTML or text content.")

        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=65536):
            total += len(chunk)
            if total > MAX_URL_BYTES:
                raise HTTPException(status_code=400, detail="URL content is too large for free-tier ingestion.")
            chunks.append(chunk)
        response.encoding = response.encoding or "utf-8"
        return b"".join(chunks).decode(response.encoding, errors="replace"), current_url

    raise HTTPException(status_code=400, detail="URL redirected too many times.")


def _extract_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "nav", "footer", "form"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else "Web source"
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 2]
    extracted = "\n".join(lines)
    if len(extracted) < 100:
        raise HTTPException(status_code=400, detail="Could not extract enough readable text from this URL.")
    return title[:160], extracted


def load_url(url: str, doc_id: str) -> tuple[list[Document], dict]:
    html, final_url = _fetch_url(url)
    title, text = _extract_text(html)
    domain = urlparse(final_url).netloc
    doc_name = sanitize_name(title, fallback=domain or "url")

    return [
        Document(
            page_content=text,
            metadata={
                "doc_id": doc_id,
                "doc_name": doc_name,
                "file_type": "url",
                "source_type": "url",
                "source_url": final_url,
                "domain": domain,
                "source": final_url,
            },
        )
    ], {"title": title, "doc_name": doc_name, "source_url": final_url, "text": text}
