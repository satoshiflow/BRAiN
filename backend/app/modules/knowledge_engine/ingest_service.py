from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

import httpx


EMBEDDING_DIM = 256


def extract_text_from_input(raw_text: str | None, url: str | None, code: str | None, document_text: str | None) -> str:
    if raw_text and raw_text.strip():
        return raw_text.strip()
    if code and code.strip():
        return code.strip()
    if document_text and document_text.strip():
        return document_text.strip()
    if url and url.strip():
        return _fetch_url_text(url.strip())
    raise ValueError("No ingestable input provided")


def _fetch_url_text(url: str) -> str:
    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        body = response.text
    body = re.sub(r"<script[\s\S]*?</script>", " ", body, flags=re.IGNORECASE)
    body = re.sub(r"<style[\s\S]*?</style>", " ", body, flags=re.IGNORECASE)
    body = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", body).strip()


def chunk_content(content: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    text = re.sub(r"\s+", " ", content).strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    step = max(1, max_chars - overlap)
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return chunks


def _tokenize(text: str) -> Iterable[str]:
    return re.findall(r"[a-zA-Z0-9_\-]{2,}", text.lower())


def generate_embeddings(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    vec = [0.0] * dim
    tokens = list(_tokenize(text))
    if not tokens:
        return vec

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + (digest[5] / 255.0)
        vec[idx] += sign * weight

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def vector_to_pgvector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in vector) + "]"
