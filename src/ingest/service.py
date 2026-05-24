"""
Document Ingestion Service.
Handles loading documents, creating semantic chunks, and storing vector embeddings.
"""
import os
import traceback
from langchain_postgres import PGVector

from src.config import (
    DATABASE_URL,
    DEFAULT_DATASET_KEY,
    get_dataset_collection_name,
    get_dataset_folder,
    normalize_dataset_key,
)
from src.config.settings import (
    get_current_pdf_language,
    get_current_pdf_strategy,
    get_current_chunk_max_characters,
    get_current_chunk_new_after_n_chars,
    get_current_chunk_overlap,
)
from src.config.env import CHUNK_MULTIPAGE_SECTIONS
from src.embeddings import get_embeddings
from src.ingest.partition import partition_file
from src.ingest.chunking import chunk_elements, elements_to_documents
from src.ingest.vector_store import ensure_extension_exists, create_vector_store


class IngestService:
    """Service for ingesting documents into the vector database."""
    
    def __init__(self, dataset_key: str = DEFAULT_DATASET_KEY):
        """Initialize the ingest service with embedding model and chunking config."""
        self.dataset_key = normalize_dataset_key(dataset_key)
        self.embedding_function = get_embeddings()
        self.connection_string = DATABASE_URL
        self.collection_name = get_dataset_collection_name(self.dataset_key)
        self.data_folder = get_dataset_folder(self.dataset_key)
        
        # Get current chunking configuration
        self.chunk_max_chars = get_current_chunk_max_characters()
        self.chunk_new_after = get_current_chunk_new_after_n_chars()
        self.chunk_overlap = get_current_chunk_overlap()
        self.multipage_sections = CHUNK_MULTIPAGE_SECTIONS
        
        # Get current partitioning configuration
        self.pdf_strategy = get_current_pdf_strategy()
        pdf_language = get_current_pdf_language()
        self.languages = [pdf_language] if pdf_language else None
    
    def check_collection_exists(self) -> bool:
        """
        Check if the vector collection already has documents.
        
        Returns:
            True if collection exists and has documents, False otherwise
        """
        try:
            ensure_extension_exists(self.connection_string)
            
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
        Ingest a single document file into the vector database.
        
        Args:
            doc_path: Path to the document file. If None, uses the first supported file in the dataset folder.
        """
        data_folder = str(self.data_folder)
        if not os.path.exists(data_folder):
            raise FileNotFoundError(
                f"ERROR: Folder '{data_folder}' not found. Please create it and add a document."
            )
        
        # Auto-detect first supported file if no path provided
        if doc_path is None:
            supported_extensions = ['.pdf', '.txt', '.docx', '.html', '.csv']
            files = [
                f for f in os.listdir(data_folder)
                if any(f.lower().endswith(ext) for ext in supported_extensions)
            ]
            
            if not files:
                raise FileNotFoundError(
                    f"ERROR: No supported files found in '{data_folder}' folder. "
                    f"Supported: {', '.join(supported_extensions)}"
                )
            
            doc_path = os.path.join(data_folder, files[0])
        
        print(f"Loading file: {doc_path}...")
        
        # Partition the document
        elements = partition_file(doc_path, self.pdf_strategy, self.languages)
        
        # Chunk the elements
        chunks = chunk_elements(
            elements,
            self.chunk_max_chars,
            self.chunk_new_after,
            self.chunk_overlap,
            self.multipage_sections
        )
        
        # Convert to LangChain Documents
        documents = elements_to_documents(
            chunks,
            source_file=os.path.basename(doc_path),
            dataset_key=self.dataset_key,
        )
        print(f"  → Converted to {len(documents)} document chunks")
        
        # Create vector store
        print("Saving to PostgreSQL with pgvector...")
        create_vector_store(
            documents,
            self.embedding_function,
            self.connection_string,
            self.collection_name
        )
        
        print("✓ Done! Vector embeddings saved to PostgreSQL.")
    
    def ingest_all_documents(self) -> None:
        """Ingest all supported files from the data folder with per-file error handling."""
        data_folder = str(self.data_folder)
        if not os.path.exists(data_folder):
            raise FileNotFoundError(
                f"ERROR: Folder '{data_folder}' not found. Please create it and add documents."
            )
        
        # Find all supported files
        supported_extensions = ['.pdf', '.txt', '.docx', '.html', '.csv']
        all_files = [
            f for f in os.listdir(data_folder)
            if any(f.lower().endswith(ext) for ext in supported_extensions)
        ]
        
        if not all_files:
            raise FileNotFoundError(
                f"ERROR: No supported files found in '{data_folder}' folder. "
                f"Supported: {', '.join(supported_extensions)}"
            )
        
        print(f"Found {len(all_files)} file(s). Processing...")
        
        # Process all files with error isolation
        all_documents = []
        successful_files = []
        failed_files = []
        
        for doc_file in all_files:
            doc_path = os.path.join(data_folder, doc_file)
            print(f"\nProcessing: {doc_file}")
            
            try:
                # Partition the document
                elements = partition_file(doc_path, self.pdf_strategy, self.languages)
                
                # Chunk the elements
                chunks = chunk_elements(
                    elements,
                    self.chunk_max_chars,
                    self.chunk_new_after,
                    self.chunk_overlap,
                    self.multipage_sections
                )
                
                # Convert to LangChain Documents
                documents = elements_to_documents(
                    chunks,
                    source_file=doc_file,
                    dataset_key=self.dataset_key,
                )
                
                all_documents.extend(documents)
                successful_files.append(doc_file)
                print(f"  ✓ {doc_file} processed successfully ({len(documents)} chunks)")
                
            except Exception as e:
                failed_files.append((doc_file, str(e)))
                print(f"  ✗ Failed to process {doc_file}: {e}")
                print(f"  Traceback: {traceback.format_exc()}")
                continue
        
        # Summary
        print(f"\n{'='*60}")
        print(f"Processing summary:")
        print(f"  Successful: {len(successful_files)}/{len(all_files)} files")
        print(f"  Failed: {len(failed_files)}/{len(all_files)} files")
        print(f"  Total chunks: {len(all_documents)}")
        
        if failed_files:
            print(f"\nFailed files:")
            for filename, error in failed_files:
                print(f"  - {filename}: {error}")
        
        if not all_documents:
            raise RuntimeError("ERROR: No documents were successfully processed. Cannot create vector store.")
        
        # Create vector store with all successfully processed documents
        print(f"\n{'='*60}")
        print("Saving to PostgreSQL with pgvector...")
        create_vector_store(
            all_documents,
            self.embedding_function,
            self.connection_string,
            self.collection_name
        )
        
        print("✓ Done! Vector embeddings saved to PostgreSQL.")
        print(f"{'='*60}")
