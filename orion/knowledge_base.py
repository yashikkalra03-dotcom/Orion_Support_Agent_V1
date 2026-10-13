from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

try:
    from orion.config import get_google_api_key
except ModuleNotFoundError:
    from config import get_google_api_key


KNOWLEDGE_FILE = Path(__file__).with_name("knowledge_base.md")
VECTOR_STORE_PATH = Path(__file__).resolve().parent.parent / ".orion_data" / "knowledge"
COLLECTION_NAME = "orion_customer_experience"
EMBEDDING_MODEL = "gemini-embedding-001"


class GeminiSupportEmbeddings(Embeddings):
    def __init__(self, api_key: str) -> None:
        self._documents = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=api_key,
            task_type="RETRIEVAL_DOCUMENT",
        )
        self._queries = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=api_key,
            task_type="RETRIEVAL_QUERY",
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._documents.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._queries.embed_query(text)


def load_knowledge_documents(path: Path = KNOWLEDGE_FILE) -> tuple[list[Document], str]:
    content = path.read_text(encoding="utf-8")
    fingerprint = hashlib.sha256(content.encode("utf-8")).hexdigest()
    sections = re.split(r"(?m)^##\s+", content)
    documents = []
    for section in sections[1:]:
        title, separator, body = section.partition("\n")
        page_content = body.strip()
        if not separator or not page_content:
            continue
        topic = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        documents.append(
            Document(
                page_content=f"{title.strip()}\n{page_content}",
                metadata={
                    "topic": title.strip(),
                    "source": path.name,
                    "knowledge_version": fingerprint,
                },
            )
        )
    if not documents:
        raise ValueError(f"No knowledge sections were loaded from {path}.")
    return documents, fingerprint


class KnowledgeBase:
    def __init__(self, persist_directory: Path = VECTOR_STORE_PATH) -> None:
        api_key = get_google_api_key()
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required to create Gemini embeddings.")

        documents, fingerprint = load_knowledge_documents()
        self._document_count = len(documents)
        self._fingerprint = fingerprint
        self._store = Chroma(
            collection_name=COLLECTION_NAME,
            persist_directory=str(persist_directory),
            embedding_function=GeminiSupportEmbeddings(api_key),
            collection_metadata={"hnsw:space": "cosine"},
        )
        self._synchronize_documents(documents, fingerprint)

    @property
    def document_count(self) -> int:
        return self._document_count

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    @property
    def is_active(self) -> bool:
        return self._store is not None

    def _synchronize_documents(self, documents: list[Document], fingerprint: str) -> None:
        current = self._store.get(include=["metadatas"])
        ids = current.get("ids", [])
        metadata = current.get("metadatas", [])
        current_versions = {item.get("knowledge_version") for item in metadata if item}
        if ids and current_versions == {fingerprint} and len(ids) == len(documents):
            return
        if ids:
            self._store.delete(ids=ids)
        document_ids = [
            f"{index}-{hashlib.sha1(document.metadata['topic'].encode()).hexdigest()[:12]}"
            for index, document in enumerate(documents)
        ]
        self._store.add_documents(documents, ids=document_ids)

    def retrieve(self, query: str, limit: int = 4) -> list[Document]:
        return self._store.similarity_search(query, k=min(limit, self._document_count))


@lru_cache(maxsize=1)
def get_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase()