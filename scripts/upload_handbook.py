"""Splits the handbook by section and uploads it to Pinecone.

Run from the repo root: python -m scripts.upload_handbook
Run it again whenever the handbook changes.
"""
import os
import time

from dotenv import load_dotenv
from pinecone import Pinecone

from app.handbook import read_handbook, to_records

load_dotenv()

INDEX_NAME = os.getenv("PINECONE_INDEX", "moonbean")
NAMESPACE = "handbook"
BATCH_SIZE = 90  # Pinecone doesn't allow more than 96 records at once


def main():
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

    if not pc.has_index(INDEX_NAME):
        print(f"Creating index {INDEX_NAME}")
        pc.create_index_for_model(
            name=INDEX_NAME,
            cloud="aws",
            region="us-east-1",
            embed={"model": "llama-text-embed-v2", "field_map": {"text": "chunk_text"}},
        )
        while not pc.describe_index(INDEX_NAME).status["ready"]:
            time.sleep(2)

    index = pc.Index(INDEX_NAME)
    records = to_records(read_handbook())
    for start in range(0, len(records), BATCH_SIZE):
        index.upsert_records(namespace=NAMESPACE, records=records[start : start + BATCH_SIZE])

    print(f"Uploaded {len(records)} sections to {INDEX_NAME}/{NAMESPACE}")


if __name__ == "__main__":
    main()
