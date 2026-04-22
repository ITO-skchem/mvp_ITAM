from typing import List, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class AssetIndexer:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dim)
        self.texts = []
        self.meta = []

    def encode(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    def build(self, items: List[Tuple[str, dict]]):
        self.texts = [text for text, _ in items]
        self.meta = [meta for _, meta in items]
        if not self.texts:
            self.index.reset()
            return
        emb = self.encode(self.texts)
        self.index.reset()
        self.index.add(emb)

    def search(self, query: str, k=5):
        if self.index.ntotal == 0:
            return []
        q = self.encode([query])
        distances, indices = self.index.search(q, k)
        return [
            {"score": float(distances[0][i]), "text": self.texts[idx], "meta": self.meta[idx]}
            for i, idx in enumerate(indices[0])
            if idx != -1
        ]
