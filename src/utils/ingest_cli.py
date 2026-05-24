"""
Command-line interface for ingesting documents.
Processes PDFs and TXT files from the shared Sapientia folder into the vector database.
"""
import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.ingest import IngestService
from src.config import DEFAULT_DATASET_KEY, get_dataset_folder, normalize_dataset_key


def main():
    """Run the document ingestion process."""
    parser = argparse.ArgumentParser(description="Ingest documents into a dataset-specific vector collection.")
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET_KEY,
        help="Dataset key to ingest (default: sapientia)",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Optional file path to ingest instead of the whole dataset folder.",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("AI Chat Flow - Document Ingestion Tool")
    print("=" * 60 + "\n")
    
    dataset_key = normalize_dataset_key(args.dataset)
    ingest_service = IngestService(dataset_key=dataset_key)
    
    try:
        dataset_folder = get_dataset_folder(dataset_key)
        print(f"Dataset: {dataset_key}")
        print(f"Dataset folder: {dataset_folder}")
        print(f"Collection: {ingest_service.collection_name}\n")

        # Check if specific file is provided
        if args.file:
            doc_path = args.file
            print(f"Ingesting specific file: {doc_path}\n")
            ingest_service.ingest_document(doc_path)
        else:
            # Ingest all documents from the dataset folder
            print("Ingesting all documents from the dataset folder...\n")
            ingest_service.ingest_all_documents()
        
        print("\n" + "=" * 60)
        print("Ingestion completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
