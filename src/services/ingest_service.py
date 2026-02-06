"""
Document Ingestion Service.
Handles loading PDFs and TXT files and creating vector embeddings in ChromaDB.
"""
import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from src.core.config import DATA_FOLDER, CHROMA_PATH, EMBEDDING_MODEL


class IngestService:
    """Service for ingesting documents into the vector database."""
    
    def __init__(self):
        """Initialize the ingest service."""
        self.embedding_function = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=300
        )
    
    def ingest_document(self, doc_path: str = None) -> None:
        """
        Ingest a document file (PDF or TXT) into the vector database.
        
        Args:
            doc_path: Path to the document file. If None, uses first PDF or TXT in DATA_FOLDER.
        """
        # Validate data folder exists
        if not os.path.exists(DATA_FOLDER):
            raise FileNotFoundError(
                f"ERROR: Folder '{DATA_FOLDER}' not found. Please create it and add a document."
            )
        
        # Find document file
        if doc_path is None:
            pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.pdf')]
            txt_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.txt')]
            
            if pdf_files:
                doc_path = os.path.join(DATA_FOLDER, pdf_files[0])
            elif txt_files:
                doc_path = os.path.join(DATA_FOLDER, txt_files[0])
            else:
                raise FileNotFoundError("ERROR: No PDF or TXT files found in 'data/' folder.")
        
        print(f"Loading file: {doc_path}...")
        
        # Load document based on file type
        if doc_path.endswith('.pdf'):
            loader = PyPDFLoader(doc_path)
        elif doc_path.endswith('.txt'):
            loader = TextLoader(doc_path, encoding='utf-8')
        else:
            raise ValueError("ERROR: Only PDF and TXT files are supported.")
        
        docs = loader.load()
        
        # Split into chunks
        splits = self.text_splitter.split_documents(docs)
        print(f"Split document into {len(splits)} chunks.")
        
        # Initialize embeddings
        print("Initializing embedding model...")
        
        # Create and save vector database
        print("Saving to ChromaDB...")
        Chroma.from_documents(
            documents=splits,
            embedding=self.embedding_function,
            persist_directory=CHROMA_PATH
        )
        
        print(f"Done! Vector database created at '{CHROMA_PATH}'.")
    
    def ingest_all_documents(self) -> None:
        """Ingest all PDF and TXT files from the data folder."""
        if not os.path.exists(DATA_FOLDER):
            raise FileNotFoundError(
                f"ERROR: Folder '{DATA_FOLDER}' not found. Please create it and add documents."
            )
        
        pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.pdf')]
        txt_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.txt')]
        
        # If no PDFs found, search for TXT files
        if not pdf_files and not txt_files:
            raise FileNotFoundError("ERROR: No PDF or TXT files found in 'data/' folder.")
        
        all_files = pdf_files + txt_files
        print(f"Found {len(pdf_files)} PDF file(s) and {len(txt_files)} TXT file(s). Processing...")
        
        all_splits = []
        for doc_file in all_files:
            doc_path = os.path.join(DATA_FOLDER, doc_file)
            print(f"\nLoading: {doc_file}...")
            
            # Load based on file type
            if doc_file.endswith('.pdf'):
                loader = PyPDFLoader(doc_path)
            else:  # .txt
                loader = TextLoader(doc_path, encoding='utf-8')
            
            docs = loader.load()
            
            splits = self.text_splitter.split_documents(docs)
            all_splits.extend(splits)
            print(f"  → {len(splits)} chunks")
        
        print(f"\nTotal chunks: {len(all_splits)}")
        print("Saving to ChromaDB...")
        
        Chroma.from_documents(
            documents=all_splits,
            embedding=self.embedding_function,
            persist_directory=CHROMA_PATH
        )
        
        print(f"Done! Vector database created at '{CHROMA_PATH}'.")
