"""
Document Ingestion Service.
Handles loading PDFs and TXT files and creating vector embeddings in PostgreSQL with pgvector.
"""
import os
import re
from langchain_community.document_loaders import UnstructuredPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text

from src.core.config import DATA_FOLDER, DATABASE_URL, EMBEDDING_MODEL, PGVECTOR_COLLECTION_NAME, PDF_LANGUAGE


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
            chunk_overlap=200
        )
        self.connection_string = DATABASE_URL
        self.collection_name = PGVECTOR_COLLECTION_NAME
        # Improved regex pattern to remove MBH Bank header with all variations
        # Handles extra spaces, newlines, and different formatting
        self.header_pattern = re.compile(
            r"M\s*B\s*H\s+Bank\s+Nyrt\..*?(?:weboldal|Weboldal):\s*www\.mbhbank\.hu.*?(?:\d{8}-\d-\d{2}|\d{7,9}-\d-\d{2})\s*",
            re.DOTALL | re.IGNORECASE
        )
    
    def _remove_header(self, text: str) -> str:
        """
        Remove the MBH Bank header from text.
        Uses regex to handle variations in whitespace and formatting.
        
        Args:
            text: Text content to clean
            
        Returns:
            Text with header removed
        """
        cleaned = self.header_pattern.sub("", text)
        # Remove any leading/trailing whitespace that may be left
        return cleaned.strip() if cleaned != text else text
    
    def _combine_elements_by_page(self, documents: list) -> list:
        """
        Combine document elements by page number.
        UnstructuredLoader creates many tiny elements (titles, paragraphs, etc.).
        This method combines them back into page-level documents.
        
        Args:
            documents: List of document elements from UnstructuredLoader
            
        Returns:
            List of combined documents, one per page
        """
        from langchain.schema import Document
        
        # Group elements by page number
        pages = {}
        for doc in documents:
            # Get page number from metadata, default to 1 if not available
            page_num = doc.metadata.get('page_number', 1)
            
            if page_num not in pages:
                pages[page_num] = {
                    'content': [],
                    'metadata': doc.metadata.copy()
                }
            
            # Add content if it's not empty
            content = doc.page_content.strip()
            if content:
                pages[page_num]['content'].append(content)
        
        # Create combined documents
        combined_docs = []
        for page_num in sorted(pages.keys()):
            page_data = pages[page_num]
            # Join all content with double newline to preserve paragraph separation
            combined_content = '\n\n'.join(page_data['content'])
            
            if combined_content:  # Only add non-empty pages
                combined_doc = Document(
                    page_content=combined_content,
                    metadata=page_data['metadata']
                )
                combined_docs.append(combined_doc)
        
        return combined_docs
    
    def _clean_documents(self, documents: list) -> list:
        """
        Clean documents by removing repetitive headers.
        
        Args:
            documents: List of documents to clean
            
        Returns:
            List of cleaned documents
        """
        for doc in documents:
            doc.page_content = self._remove_header(doc.page_content)
        return documents
    
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
                pre_delete_collection=True  # Clear existing collection before adding new documents,
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
            loader = UnstructuredPDFLoader(doc_path)
        elif doc_path.endswith('.txt'):
            loader = TextLoader(doc_path, encoding='utf-8')
        else:
            raise ValueError("ERROR: Only PDF and TXT files are supported.")
        
        docs = loader.load()
        print(f"Loaded {len(docs)} elements from document.")
        
        # Combine elements by page first (fixes tiny chunk issue)
        combined_docs = self._combine_elements_by_page(docs)
        print(f"Combined into {len(combined_docs)} pages.")
        
        # Clean documents (remove headers)
        combined_docs = self._clean_documents(combined_docs)
        
        # Now split into semantic chunks
        splits = self.text_splitter.split_documents(combined_docs)
        print(f"Split into {len(splits)} chunks.")
        
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
                loader = UnstructuredPDFLoader(doc_path)
            else:
                loader = TextLoader(doc_path, encoding='utf-8')
            
            docs = loader.load()
            print(f"  → Loaded {len(docs)} elements")
            
            # Combine elements by page first (fixes tiny chunk issue)
            combined_docs = self._combine_elements_by_page(docs)
            print(f"  → Combined into {len(combined_docs)} pages")
            
            # Clean documents (remove headers)
            combined_docs = self._clean_documents(combined_docs)
            
            # Now split into semantic chunks
            splits = self.text_splitter.split_documents(combined_docs)
            all_splits.extend(splits)
            print(f"  → Split into {len(splits)} chunks")
        
        print(f"\nTotal chunks: {len(all_splits)}")
        print("Saving to PostgreSQL with pgvector...")
        
        self._create_vector_store(all_splits)
        
        print("Done! Vector embeddings saved to PostgreSQL.")
