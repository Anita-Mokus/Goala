"""
Command-line interface for querying the chatbot.
Interactive console application for testing the RAG system.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.chat import RAGService
from src.config import LLM_MODEL


def main():
    """Run the interactive query loop."""
    print("\n" + "=" * 60)
    print("AI Chat Flow - Interactive Query Tool")
    print(f"Using model: {LLM_MODEL}")
    print("=" * 60)
    print("\nSuccess! Chatbot is ready. Type 'exit' to quit.\n")
    
    # Initialize RAG service
    rag_service = RAGService()
    
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
