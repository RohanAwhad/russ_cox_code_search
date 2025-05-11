import pytest
from fastapi.testclient import TestClient
from embedder_api import app

client = TestClient(app)


def test_encode_endpoint():
    test_texts = ["This is a test sentence", "Another test sentence"]
    response = client.post("/encode", json={"texts": test_texts})
    
    assert response.status_code == 200
    embeddings = response.json()
    assert isinstance(embeddings, list)
    assert len(embeddings) == len(test_texts)
    assert all(isinstance(embedding, list) for embedding in embeddings)
    assert all(isinstance(value, float) for embedding in embeddings for value in embedding)


def test_similarity_search_endpoint():
    # Test data
    sample_texts = [
        "This is the first sample document",
        "This is the second sample document", 
        "This is the third completely different text"
    ]
    query = "sample document"
    
    # First, get embeddings for the sample texts
    embed_response = client.post("/encode", json={"texts": sample_texts})
    assert embed_response.status_code == 200
    embeddings = embed_response.json()
    
    # Prepare docstrings with real embeddings
    docstrings = {
        f"doc{i+1}": {
            "filepath": f"path/to/file{i+1}.py",
            "embedding": embedding
        } for i, embedding in enumerate(embeddings)
    }
    
    # Now test similarity search
    response = client.post(
        "/similarity-search", 
        json={
            "query": query,
            "docstrings": docstrings,
            "top_k": 2
        }
    )

    
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) <= 2  # Should return at most top_k results
    
    # Verify structure of results
    for result in results:
        assert "filepath" in result
        assert "similarity" in result
        assert isinstance(result["filepath"], str)
        assert isinstance(result["similarity"], float)
        assert 0 <= result["similarity"] <= 1  # Similarity should be between 0 and 1
