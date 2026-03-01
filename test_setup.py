from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Initialize the LLM
llm = ChatGroq(
    model="llama-3.1-8b-instant", 
    temperature=0
)

# Send a message and get a response
response = llm.invoke("Hello! Are you ready to help with my hotel project?")

# Print the response
print(response.content)


