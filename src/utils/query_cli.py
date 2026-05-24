"""
Command-line interface for querying the chatbot.
Interactive console application for testing the RAG system.
"""
import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.chat import RAGService
from src.config import DEFAULT_DATASET_KEY, LLM_MODEL, normalize_dataset_key


def main():
    """Run the interactive query loop."""
    parser = argparse.ArgumentParser(description="Query a dataset-specific RAG collection.")
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET_KEY,
        help="Dataset key to query (default: sapientia)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("AI Chat Flow - Interactive Query Tool")
    print(f"Using model: {LLM_MODEL}")
    print("=" * 60)
    print("\nSuccess! Chatbot is ready. Type 'exit' to quit.\n")
    
    # Initialize RAG service
    dataset_key = normalize_dataset_key(args.dataset)
    print(f"Dataset: {dataset_key}\n")
    rag_service = RAGService(dataset_key=dataset_key)
    
    while True:
        query = input("Ask a question about your hotel: ")
        
        if query.lower() in ['exit', 'quit', 'q']:
            print("\nGoodbye!")
            break
        
        if not query.strip():
            continue
        
        try:
            # Run the query
            result = rag_service.query(query)
            
            print("\n--- Answer ---")
            print(result)
            print("\n")
        except Exception as e:
            print(f"\nError: {str(e)}\n")


if __name__ == "__main__":
    main()
