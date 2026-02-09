"""
Document Ingestion Service.
Handles loading PDFs and TXT files and creating vector embeddings in PostgreSQL with pgvector.
"""
import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text

from src.core.config import DATA_FOLDER, DATABASE_URL, EMBEDDING_MODEL, PGVECTOR_COLLECTION_NAME


class IngestService:
    """Service for ingesting documents into the vector database."""
    
    def __init__(self):
        """Initialize the ingest service."""
        self.embedding_function = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=300
        )
        self.connection_string = DATABASE_URL
        self.collection_name = PGVECTOR_COLLECTION_NAME
    
    def _ensure_extension_exists(self) -> None:
        """Ensure pgvector extension exists."""
        try:
            engine = create_engine(self.connection_string, echo=False)
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            engine.dispose()
            print("✓ pgvector extension confirmed")
        except Exception as e:
            print(f"ℹ Extension check: {type(e).__name__}")
    
    def _create_vector_store(self, documents: list) -> PGVector:
        """Create or update the vector store with documents."""
        try:
            vector_store = PGVector.from_documents(
                documents=documents,
                embedding=self.embedding_function,
                connection=self.connection_string,
                collection_name=self.collection_name,
                use_jsonb=True,
                pre_delete_collection=False,
            )
            return vector_store
        except Exception as e:
            print(f"Error creating vector store: {e}")
            raise
    
    def check_collection_exists(self) -> bool:
        """Check if the vector collection already has documents."""
        try:
            self._ensure_extension_exists()
            
            vector_store = PGVector(
                embeddings=self.embedding_function,
                connection=self.connection_string,
                collection_name=self.collection_name,
                use_jsonb=True,
            )
            # Try a simple similarity search to check if collection has data
            results = vector_store.similarity_search("test", k=1)
            return len(results) > 0
        except Exception:
            return False
    
    def ingest_document(self, doc_path: str = None) -> None:
        """
        Ingest a document file (PDF or TXT) into the vector database.
        
        Args:
            doc_path: Path to the document file. If None, uses first PDF or TXT in DATA_FOLDER.
        """
        if not os.path.exists(DATA_FOLDER):
            raise FileNotFoundError(
                f"ERROR: Folder '{DATA_FOLDER}' not found. Please create it and add a document."
            )
        
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
        
        if doc_path.endswith('.pdf'):
            loader = PyPDFLoader(doc_path)
        elif doc_path.endswith('.txt'):
            loader = TextLoader(doc_path, encoding='utf-8')
        else:
            raise ValueError("ERROR: Only PDF and TXT files are supported.")
        
        docs = loader.load()
        splits = self.text_splitter.split_documents(docs)
        print(f"Split document into {len(splits)} chunks.")
        
        print("Initializing embedding model...")
        print("Saving to PostgreSQL with pgvector...")
        self._create_vector_store(splits)
        
        print("Done! Vector embeddings saved to PostgreSQL.")
    
    def ingest_all_documents(self) -> None:
        """Ingest all PDF and TXT files from the data folder."""
        if not os.path.exists(DATA_FOLDER):
            raise FileNotFoundError(
                f"ERROR: Folder '{DATA_FOLDER}' not found. Please create it and add documents."
            )
        
        pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.pdf')]
        txt_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.txt')]
        
        if not pdf_files and not txt_files:
            raise FileNotFoundError("ERROR: No PDF or TXT files found in 'data/' folder.")
        
        all_files = pdf_files + txt_files
        print(f"Found {len(pdf_files)} PDF file(s) and {len(txt_files)} TXT file(s). Processing...")
        
        all_splits = []
        for doc_file in all_files:
            doc_path = os.path.join(DATA_FOLDER, doc_file)
            print(f"\nLoading: {doc_file}...")
            
            if doc_file.endswith('.pdf'):
                loader = PyPDFLoader(doc_path)
            else:
                loader = TextLoader(doc_path, encoding='utf-8')
            
            docs = loader.load()
            splits = self.text_splitter.split_documents(docs)
            all_splits.extend(splits)
            print(f"  → {len(splits)} chunks")
        
        print(f"\nTotal chunks: {len(all_splits)}")
        print("Saving to PostgreSQL with pgvector...")
        
        self._create_vector_store(all_splits)
        
        print("Done! Vector embeddings saved to PostgreSQL.")
