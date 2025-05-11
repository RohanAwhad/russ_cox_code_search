import numpy as np
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
    
    def encode(self, text: str) -> list[float]:
        return self.model.encode([text])[0].tolist()
    
    def similarity_search(self, query: str, docstrings: dict, top_k: int = 3) -> list[tuple[str, float]]:
        query_embedding = self.model.encode([query])[0]
        similarities = []
        for entry in docstrings.values():
            if 'embedding' in entry:
                doc_embedding = np.array(entry['embedding'])
                similarity = np.dot(query_embedding, doc_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
                )
                similarities.append((entry['filepath'], similarity))
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]
