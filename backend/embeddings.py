from sentence_transformers import SentenceTransformer
import numpy as np
import os
from dotenv import load_dotenv 
load_dotenv()
import yaml

with open("backend/config.yaml") as f:
    CONFIG = yaml.safe_load(f)

embedding_model_name = CONFIG["models"]["embedding_model"]

class EmbeddingModel:
    def __init__(self, model_name: str = embedding_model_name):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        """
        Encode a list of texts into normalized float32 embeddings
        suitable for FAISS (cosine similarity via inner product).
        """
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embeddings.astype("float32")