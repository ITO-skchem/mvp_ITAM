import pickle
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


class AssetSearchService:
    def __init__(self, path="var/asset_index.pkl", model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Index file not found: {self.path}")

        with open(self.path, "rb") as f:
            data = pickle.load(f)

        self.texts = data["texts"]
        self.meta = data["meta"]
        self.model = SentenceTransformer(model_name)
        self.index = faiss.deserialize_index(data["raw_index"])

    def search(self, query: str, k=5):
        emb = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        distances, indices = self.index.search(emb, k)
        return [
            {"score": float(distances[0][i]), "text": self.texts[idx], "meta": self.meta[idx]}
            for i, idx in enumerate(indices[0])
            if idx != -1
        ]
