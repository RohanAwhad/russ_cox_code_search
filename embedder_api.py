import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from typing import Any, List, Dict, Tuple, Optional

app = FastAPI(title="Embedder API", description="API for text embedding and similarity search")


class EmbedRequest(BaseModel):
  texts: List[str]


class SimilaritySearchRequest(BaseModel):
  query: str
  docstrings: Dict[str, Dict[str, Any]]
  top_k: int = 3


class SimilarityResult(BaseModel):
  filepath: str
  similarity: float


class Embedder:

  def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
    self.model = SentenceTransformer(model_name)

  def encode(self, texts: List[str], batch_size: int = 8) -> List[List[float]]:
    embeddings = []
    for i in range(0, len(texts), batch_size):
      batch = texts[i:i + batch_size]
      batch_embeddings = self.model.encode(batch).tolist()
      embeddings.extend(batch_embeddings)
    return embeddings

  def similarity_search(self, query: str, docstrings: dict, top_k: int = 3) -> List[Tuple[str, float]]:
    query_embedding = self.model.encode([query], batch_size=8)[0]

    similarities = []
    for entry in docstrings.values():
      if 'embedding' in entry:
        doc_embedding = np.array(entry['embedding'])
        similarity = np.dot(query_embedding,
                            doc_embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding))
        similarities.append((entry['filepath'], similarity))
    return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]


embedder = Embedder()


@app.get("/")
def read_root():
  return {"message": "Embedder API is running"}


@app.post("/encode", response_model=List[List[float]])
def encode_text(request: EmbedRequest):
  try:
    return embedder.encode(request.texts, batch_size=8)
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error encoding text: {str(e)}")


@app.post("/similarity-search", response_model=List[SimilarityResult])
def similarity_search(request: SimilaritySearchRequest):
  try:
    results = embedder.similarity_search(request.query, request.docstrings, request.top_k)
    return [SimilarityResult(filepath=filepath, similarity=similarity) for filepath, similarity in results]
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error in similarity search: {str(e)}")


if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)
