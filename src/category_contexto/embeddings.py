import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100


def get_openai_client() -> OpenAI:
    return OpenAI()


def generate_embeddings(blurbs: dict[str, str]) -> dict[str, np.ndarray]:
    client = get_openai_client()
    entity_ids = list(blurbs.keys())
    texts = [blurbs[eid] for eid in entity_ids]
    result = {}

    for i in range(0, len(texts), BATCH_SIZE):
        batch_ids = entity_ids[i : i + BATCH_SIZE]
        batch_texts = texts[i : i + BATCH_SIZE]

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch_texts,
        )
        for j, embedding_obj in enumerate(response.data):
            result[batch_ids[j]] = np.array(embedding_obj.embedding)

    return result


def compute_embedding_similarity(
    embeddings: dict[str, np.ndarray], entity_a: str, entity_b: str
) -> float:
    vec_a = embeddings[entity_a]
    vec_b = embeddings[entity_b]
    dot = np.dot(vec_a, vec_b)
    norm = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if norm == 0:
        return 0.0
    return float(dot / norm)
