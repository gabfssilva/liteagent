import numpy as np
from collections import Counter

def text_to_vector(text: str, vocabulary: list[str]) -> np.ndarray:
    word_counts = Counter(text.lower().split())
    return np.array([word_counts.get(word, 0) for word in vocabulary], dtype=np.float32)

def cosine_sim(text1: str, text2: str) -> float:
    words = set(text1.lower().split()) | set(text2.lower().split())
    vocabulary = sorted(words)

    v1 = text_to_vector(text1, vocabulary)
    v2 = text_to_vector(text2, vocabulary)

    norm1 = float(np.linalg.norm(v1))
    norm2 = float(np.linalg.norm(v2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return np.dot(v1, v2) / (norm1 * norm2)
