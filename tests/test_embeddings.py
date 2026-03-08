import numpy as np
from unittest.mock import patch, MagicMock
from category_contexto.embeddings import generate_embeddings, compute_embedding_similarity


def test_generate_embeddings():
    mock_embedding = [0.1] * 3072
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=mock_embedding, index=0),
        MagicMock(embedding=mock_embedding, index=1),
    ]

    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = mock_response

    blurbs = {"Q1": "Person A. President.", "Q2": "Person B. Senator."}

    with patch("category_contexto.embeddings.get_openai_client", return_value=mock_client):
        result = generate_embeddings(blurbs)

    assert "Q1" in result
    assert "Q2" in result
    assert len(result["Q1"]) == 3072


def test_compute_embedding_similarity():
    embeddings = {
        "Q1": np.array([1.0, 0.0, 0.0]),
        "Q2": np.array([1.0, 0.0, 0.0]),
        "Q3": np.array([0.0, 1.0, 0.0]),
    }
    assert compute_embedding_similarity(embeddings, "Q1", "Q2") == 1.0
    assert compute_embedding_similarity(embeddings, "Q1", "Q3") == 0.0


def test_compute_embedding_similarity_normalized():
    embeddings = {
        "Q1": np.array([3.0, 0.0, 0.0]),
        "Q2": np.array([0.0, 5.0, 0.0]),
    }
    sim = compute_embedding_similarity(embeddings, "Q1", "Q2")
    assert abs(sim - 0.0) < 1e-6
