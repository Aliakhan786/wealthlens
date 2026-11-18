-- Runs once when the Postgres container is first created.
-- pgvector enables the planned upgrade from hashing embeddings to neural embeddings (see docs/DECISIONS.md).
CREATE EXTENSION IF NOT EXISTS vector;
