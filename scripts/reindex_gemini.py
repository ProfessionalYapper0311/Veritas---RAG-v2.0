"""Script to re-embed and re-index all existing documents with Google Gemini."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.db import get_db_connection
from worker.ingest import process_s3_key

def reindex_all():
    with get_db_connection() as conn:
        docs = conn.execute(
            "SELECT id, title, s3_key, status FROM documents WHERE status IN ('ready', 'failed') ORDER BY created_at ASC"
        ).fetchall()

    total = len(docs)
    print(f"Found {total} document(s) to re-index with Google Gemini...")
    if total == 0:
        print("No documents require re-indexing.")
        return

    succeeded = 0
    failed = 0

    for idx, doc in enumerate(docs, start=1):
        print(f"[{idx}/{total}] Re-ingesting: {doc['title']} (id={doc['id']}, s3_key={doc['s3_key']})")
        # Reset status temporarily to pending so process_s3_key processes it
        with get_db_connection() as conn:
            conn.execute("UPDATE documents SET status = 'pending' WHERE id = %s", (doc['id'],))

        try:
            process_s3_key(doc['s3_key'])
            succeeded += 1
            print(f"  -> Successfully re-indexed: {doc['title']}")
        except Exception as exc:
            failed += 1
            print(f"  -> FAILED to re-index {doc['title']}: {exc}")

    print("\n--- Re-indexing Summary ---")
    print(f"Total:     {total}")
    print(f"Succeeded: {succeeded}")
    print(f"Failed:    {failed}")

if __name__ == '__main__':
    reindex_all()