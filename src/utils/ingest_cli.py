"""
Command-line interface for document ingestion.

Usage:
  # Ingest all files from shared/sapientia/ into the sapientia collection
  python -m src.utils.ingest_cli --dataset sapientia

  # Ingest a single file
  python -m src.utils.ingest_cli --dataset sapientia --file path/to/file.pdf

  # Ingest the LiveRAG/Benchmark HuggingFace dataset (no chunking)
  python -m src.utils.ingest_cli --liverag

  # LiveRAG with a custom dataset key (collection name)
  python -m src.utils.ingest_cli --liverag --dataset liverag_test --max-rows 100
"""
import argparse
from datetime import datetime
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import DEFAULT_DATASET_KEY
from src.ingest import IngestService, LiveRAGIngestService


def main():
    parser = argparse.ArgumentParser(
        description="Ingest documents into a dataset-specific vector collection."
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET_KEY,
        help=f"Dataset key / collection identifier (default: {DEFAULT_DATASET_KEY})",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Ingest a single file instead of the whole dataset folder (file-based mode only).",
    )
    parser.add_argument(
        "--liverag",
        action="store_true",
        help="Ingest the LiveRAG/Benchmark HuggingFace dataset (pre-chunked, no unstructured).",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Stop after N rows — useful for smoke-testing LiveRAG ingest.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of dataset rows to buffer before each embed+store flush (default: 100).",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Goala — Document Ingestion Tool")
    print("=" * 60 + "\n")

    start = datetime.now()
    print(f"Started at: {start.strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        if args.liverag:
            dataset_key = args.dataset if args.dataset != DEFAULT_DATASET_KEY else "liverag"
            print(f"Mode:    LiveRAG/Benchmark (HuggingFace, streaming, no chunking)")
            print(f"Dataset: {dataset_key}\n")
            service = LiveRAGIngestService(dataset_key=dataset_key)
            service.ingest(batch_size=args.batch_size, max_rows=args.max_rows)
        else:
            print(f"Mode:    File-based (PDF / TXT / DOCX via unstructured)")
            print(f"Dataset: {args.dataset}\n")
            service = IngestService(dataset_key=args.dataset)
            if args.file:
                print(f"Ingesting single file: {args.file}\n")
                service.ingest_document(args.file)
            else:
                print("Ingesting all documents from dataset folder...\n")
                service.ingest_all_documents()

        print("\n" + "=" * 60)
        print("Ingestion completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nERROR: {e}\n")
        sys.exit(1)

    completed = datetime.now()
    duration = completed - start
    
    print(f"Completed at: {completed.strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"Duration: {duration}")


if __name__ == "__main__":
    main()
