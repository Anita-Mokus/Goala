"""
Test script to verify Groq API setup and connection.
"""
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def test_groq_connection():
    """Test connection to Groq API."""
    print("\n" + "=" * 60)
    print("Testing Groq API Connection")
    print("=" * 60 + "\n")
    
    try:
        # Initialize the LLM
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0
        )
        
        # Send a test message
        print("Sending test message...")
        response = llm.invoke("Hello! Are you ready to help with my hotel project?")
        
        # Print the response
        print("\n--- Response ---")
        print(response.content)
        print("\n" + "=" * 60)
        print("✓ Connection successful!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}\n")
        raise


if __name__ == "__main__":
    test_groq_connection()
