"""
Command-line interface for ingesting documents.
Processes PDFs and TXT files from the data folder into the vector database.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.services import IngestService


def main():
    """Run the document ingestion process."""
    print("\n" + "=" * 60)
    print("AI Chat Flow - Document Ingestion Tool")
    print("=" * 60 + "\n")
    
    ingest_service = IngestService()
    
    try:
        # Check if specific file is provided
        if len(sys.argv) > 1:
            doc_path = sys.argv[1]
            print(f"Ingesting specific file: {doc_path}\n")
            ingest_service.ingest_document(doc_path)
        else:
            # Ingest all documents from data folder
            print("Ingesting all documents from data folder...\n")
            ingest_service.ingest_all_documents()
        
        print("\n" + "=" * 60)
        print("Ingestion completed successfully!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
