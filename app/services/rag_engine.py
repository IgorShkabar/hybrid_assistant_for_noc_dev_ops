# RAG-engine
# Loads the .md files into Qdrant and finds a necessary reglament by the error text. 

import os
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings


class RAGEngine:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = "noc_runbooks"
        self._init_collection()

    def _simple_embedding(self, text: str) -> list[float]:
        """Легкий детерминированный эмбеддинг (32 измерения) без скачивания тяжелых ML-моделей."""
        """Lightweight deterministic embedding (32 dimensions) without the need to download heavy ML models."""
        words = text.lower().split()
        vec = [0.0] * 32
        for w in words:
            idx = int(hashlib.md5(w.encode()).hexdigest(), 16) % 32
            vec[idx] += 1.0
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]

    def _init_collection(self):
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=32, distance=Distance.COSINE),
            )
            self.index_knowledge_base()

    def index_knowledge_base(self, folder: str = "knowledge_base"):
        if not os.path.exists(folder):
            return
        points = []
        for idx, filename in enumerate(os.listdir(folder), start=1):
            if filename.endswith(".md"):
                path = os.path.join(folder, filename)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                points.append(
                    PointStruct(
                        id=idx,
                        vector=self._simple_embedding(content),
                        payload={"filename": filename, "content": content},
                    )
                )
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)

    def search_runbook(self, query_log: str) -> tuple[str, str]:
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=self._simple_embedding(query_log),
            limit=1,
        ).points
        if not results:
            return "Not found", "The policy/procedure document not found in the knowledge base."
        top = results[0].payload
        return top["filename"], top["content"]