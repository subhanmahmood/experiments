#!/usr/bin/env python3
"""
Migrate data from Qdrant SQLite storage to running Qdrant server.
"""

import sqlite3
import pickle
import time
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Source: SQLite file from local Qdrant
SQLITE_PATH = "qdrant_data/collection/islamic_books/storage.sqlite"

# Target: Running Qdrant server
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "islamic_books"
VECTOR_SIZE = 3072


def read_vectors_from_sqlite():
    """Read all vectors and payloads from SQLite storage."""
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, point FROM points")
    rows = cursor.fetchall()
    print(f"Found {len(rows)} rows")

    points = []
    for i, (point_id, point_blob) in enumerate(rows):
        try:
            data = pickle.loads(point_blob)

            vector = data.vector
            if isinstance(vector, dict):
                vector = vector.get('') or list(vector.values())[0]

            if hasattr(vector, 'tolist'):
                vector = vector.tolist()
            elif not isinstance(vector, list):
                vector = list(vector)

            points.append({
                "id": i,
                "vector": vector,
                "payload": data.payload or {}
            })

        except Exception as e:
            print(f"Error on point {i}: {e}")

    conn.close()
    print(f"Decoded {len(points)} points")
    return points


def migrate_to_server(points):
    """Upload points to Qdrant server."""
    client = QdrantClient(
        url=QDRANT_URL,
        timeout=120,  # Longer timeout
        check_compatibility=False  # Skip version check
    )

    # Check if collection exists
    try:
        info = client.get_collection(COLLECTION_NAME)
        if info.points_count > 0:
            print(f"Collection already has {info.points_count} points")
            response = input("Delete and recreate? (y/n): ")
            if response.lower() != 'y':
                print("Aborting")
                return
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection")
    except:
        pass

    # Create collection
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"Created collection {COLLECTION_NAME}")

    # Upload in smaller batches
    batch_size = 50  # Smaller batches
    delay_between_batches = 0.2

    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        try:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    PointStruct(
                        id=p["id"],
                        vector=p["vector"],
                        payload=p["payload"]
                    )
                    for p in batch
                ]
            )
            progress = min(i + batch_size, len(points))
            print(f"Uploaded {progress}/{len(points)} ({100*progress//len(points)}%)")
        except Exception as e:
            print(f"Error at batch {i}: {e}")
            time.sleep(2)
            continue
        time.sleep(delay_between_batches)

    # Verify
    info = client.get_collection(COLLECTION_NAME)
    print(f"Migration complete! Collection has {info.points_count} points")


if __name__ == "__main__":
    print("Reading from SQLite...")
    points = read_vectors_from_sqlite()

    if points:
        print(f"\nMigrating {len(points)} points to server...")
        migrate_to_server(points)
    else:
        print("No points found to migrate")
