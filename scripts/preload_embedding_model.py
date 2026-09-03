"""Preload the local multilingual embedding model into a container cache."""
from __future__ import annotations

import os

from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType

MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
FASTEMBED_MODEL = "pm/paraphrase-multilingual-mpnet-base-v2"
DIMENSIONS = 768

TextEmbedding.add_custom_model(
    model=FASTEMBED_MODEL,
    pooling=PoolingType.MEAN,
    normalization=True,
    sources=ModelSource(hf=MODEL),
    dim=DIMENSIONS,
    model_file="onnx/model.onnx",
)
TextEmbedding(model_name=FASTEMBED_MODEL, cache_dir=os.environ.get("PM_EMBEDDING_CACHE_DIR", "/app/model-cache"))
print(f"Preloaded {MODEL} ({DIMENSIONS} dimensions)")
