"""Legacy compatibility entry point.

P&M uses a dependency-free deterministic 768-dimensional representation, so
there is no neural embedding model to preload into the container image.
"""

print("No neural embedding preload required; using local hashed embeddings.")
