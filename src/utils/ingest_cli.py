"""
Command-line interface for ingesting documents.
Processes PDFs and TXT files from the data folder into the vector database.

Usage:
    python -m src.utils.ingest_cli            # full ingest
    python -m src.utils.ingest_cli 200        # only first 200 rows (smoke-test)
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

#from src.services import IngestService
from src.services.ingest_liverag import IngestLiveRAG


def main():
    """Run the document ingestion process."""
    print("\n" + "=" * 60)
    print("AI Chat Flow - Document Ingestion Tool")
    print("=" * 60 + "\n")

    max_rows = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if max_rows is not None:
        print(f"⚠  max_rows={max_rows} — partial ingest for testing\n")

    ingest_liveRAG_service = IngestLiveRAG()
    
    try:
        ingest_liveRAG_service.ingest(max_rows=max_rows)
        print("\n" + "=" * 60)
        print("Ingestion completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
