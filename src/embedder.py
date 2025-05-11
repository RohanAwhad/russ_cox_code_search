import httpx
import asyncio
from typing import List, Dict, Any


class AsyncEmbedderClient:

  def __init__(self, host: str = "localhost", port: int = 8000):
    self.base_url = f"http://{host}:{port}"
    self.client = httpx.AsyncClient(timeout=60.0)

  async def encode(self, texts: List[str]) -> List[List[float]]:
    """
        Encode texts to embeddings using the embedder API.
        
        Args:
            texts: List of texts to encode
            
        Returns:
            List of embeddings
        """
    url = f"{self.base_url}/encode"
    response = await self.client.post(url, json={"texts": texts})

    if response.status_code != 200:
      raise Exception(f"Error encoding text: {response.text}")

    return response.json()

  async def similarity_search(self, query: str, docstrings: Dict[str, Dict[str, Any]], top_k: int = 3):
    """
        Perform similarity search using the embedder API.
        
        Args:
            query: Query text
            docstrings: Dictionary of docstrings with embeddings
            top_k: Number of top results to return
            
        Returns:
            List of similarity results with filepath and similarity score
        """
    url = f"{self.base_url}/similarity-search"
    payload = {"query": query, "docstrings": docstrings, "top_k": top_k}

    response = await self.client.post(url, json=payload)

    if response.status_code != 200:
      raise Exception(f"Error in similarity search: {response.text}")

    return response.json()

  async def close(self):
    """Close the HTTP client session."""
    await self.client.aclose()


# Example usage
async def main():
  embedder = AsyncEmbedderClient(host="localhost", port=8000)
  try:
    embeddings = await embedder.encode(["Hello world", "How are you?"])
    print(f"Embeddings: {embeddings}")

    # Example similarity search
    docstrings = {
        "1": {
            "filepath": "file1.py",
            "embedding": embeddings[0]
        },
        "2": {
            "filepath": "file2.py",
            "embedding": embeddings[1]
        }
    }

    results = await embedder.similarity_search("hello", docstrings)
    print(f"Search results: {results}")
  finally:
    await embedder.close()


if __name__ == "__main__":
  asyncio.run(main())
