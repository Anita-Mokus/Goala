"""
Document Ingestion Service.
Handles loading PDFs and other documents, creating semantic chunks,
and storing vector embeddings in PostgreSQL with pgvector.

Refactored to use unstructured 0.18.32 directly for better partitioning
and semantic chunking with chunk_by_title strategy.
"""
import os
from typing import List
import traceback

from unstructured.partition.pdf import partition_pdf
from unstructured.partition.text import partition_text
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title
from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text

from src.core.config import (
    DATA_FOLDER,
    DATABASE_URL,
    PGVECTOR_COLLECTION_NAME,
    PDF_LANGUAGE,
    PDF_STRATEGY,
    CHUNK_MAX_CHARACTERS,
    CHUNK_NEW_AFTER_N_CHARS,
    CHUNK_OVERLAP,
    CHUNK_MULTIPAGE_SECTIONS,
)
from src.services.embeddings import get_embeddings


class IngestService:
    """Service for ingesting documents into the vector database."""
    
    def __init__(self):
        """Initialize the ingest service with embedding model and chunking config."""
        self.embedding_function = get_embeddings()
        self.connection_string = DATABASE_URL
        self.collection_name = PGVECTOR_COLLECTION_NAME
        
        # Chunking configuration
        self.chunk_max_chars = CHUNK_MAX_CHARACTERS
        self.chunk_new_after = CHUNK_NEW_AFTER_N_CHARS
        self.chunk_overlap = CHUNK_OVERLAP
        self.multipage_sections = CHUNK_MULTIPAGE_SECTIONS
        
        # Partitioning configuration
        self.pdf_strategy = PDF_STRATEGY
        self.languages = [PDF_LANGUAGE] if PDF_LANGUAGE else None
    
    def _partition_file(self, file_path: str) -> List:
        """
        Partition a document file using unstructured library.
        Automatically routes to the appropriate partitioner based on file extension.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            List of unstructured Element objects
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_extension == '.pdf':
                # Use partition_pdf with strategy and language configuration
                print(f"  Partitioning PDF with strategy='{self.pdf_strategy}', languages={self.languages}")
                elements = partition_pdf(
                    filename=file_path,
                    strategy=self.pdf_strategy,
                    languages=self.languages,
                    include_page_breaks=True,
                )
            elif file_extension == '.txt':
                # Use partition_text for plain text files
                print(f"  Partitioning TXT file")
                elements = partition_text(
                    filename=file_path,
                )
            else:
                # Use auto-detection for other file types
                print(f"  Using auto-detection for {file_extension} file")
                elements = partition(
                    filename=file_path,
                    languages=self.languages,
                )
            
            print(f"  → Extracted {len(elements)} elements")
            return elements
            
        except Exception as e:
            print(f"  ✗ Error partitioning file: {e}")
            raise
    
    def _chunk_elements(self, elements: List) -> List:
        """
        Chunk elements using unstructured's chunk_by_title strategy.
        This preserves section boundaries and respects semantic structure.
        
        Args:
            elements: List of unstructured Element objects
            
        Returns:
            List of chunked elements (CompositeElement, Table, or TableChunk)
        """
        try:
            chunks = chunk_by_title(
                elements,
                max_characters=self.chunk_max_chars,
                new_after_n_chars=self.chunk_new_after,
                overlap=self.chunk_overlap,
                multipage_sections=self.multipage_sections,
            )
            print(f"  → Created {len(chunks)} semantic chunks")
            return chunks
            
        except Exception as e:
            print(f"  ✗ Error chunking elements: {e}")
            raise
    
    def _elements_to_documents(self, chunks: List, source_file: str = None) -> List[Document]:
        """
        Convert unstructured chunks to LangChain Document objects.
        
        Args:
            chunks: List of unstructured chunk elements
            source_file: Optional source filename for metadata
            
        Returns:
            List of LangChain Document objects
        """
        documents = []
        
        for chunk in chunks:
            # Extract metadata from the chunk
            metadata = {
                'source': source_file or chunk.metadata.filename,
                'element_type': chunk.category if hasattr(chunk, 'category') else 'Unknown',
                'element_id': chunk.id if hasattr(chunk, 'id') else None,
            }
            
            # Add page number if available
            if hasattr(chunk.metadata, 'page_number') and chunk.metadata.page_number:
                metadata['page_number'] = chunk.metadata.page_number
            
            # Add filename and directory if available
            if hasattr(chunk.metadata, 'filename') and chunk.metadata.filename:
                metadata['filename'] = chunk.metadata.filename
            if hasattr(chunk.metadata, 'file_directory') and chunk.metadata.file_directory:
                metadata['file_directory'] = chunk.metadata.file_directory
            
            # Create LangChain Document
            doc = Document(
                page_content=chunk.text,
                metadata=metadata
            )
            documents.append(doc)
        
        return documents
    
    def _ensure_extension_exists(self) -> None:
        """Ensure pgvector extension exists in the database."""
        try:
            engine = create_engine(self.connection_string, echo=False)
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            engine.dispose()
            print("✓ pgvector extension confirmed")
        except Exception as e:
            print(f"ℹ Extension check: {type(e).__name__}")
    
    def _create_vector_store(self, documents: List[Document]) -> PGVector:
        """
        Create or update the vector store with documents.
        
        Args:
            documents: List of document chunks to store
            
        Returns:
            PGVector instance
        """
        try:
            vector_store = PGVector.from_documents(
                documents=documents,
                embedding=self.embedding_function,
                connection=self.connection_string,
                collection_name=self.collection_name,
                use_jsonb=True,
                pre_delete_collection=True  # Clear existing collection before adding
            )
            return vector_store
        except Exception as e:
            print(f"Error creating vector store: {e}")
            raise
    
    def check_collection_exists(self) -> bool:
        """
        Check if the vector collection already has documents.
        
        Returns:
            True if collection exists and has documents, False otherwise
        """
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
        Ingest a single document file into the vector database.
        
        Args:
            doc_path: Path to the document file. If None, uses first supported file in DATA_FOLDER.
        """
        if not os.path.exists(DATA_FOLDER):
            raise FileNotFoundError(
                f"ERROR: Folder '{DATA_FOLDER}' not found. Please create it and add a document."
            )
        
        # Auto-detect first supported file if no path provided
        if doc_path is None:
            supported_extensions = ['.pdf', '.txt', '.docx', '.html', '.csv']
            files = [
                f for f in os.listdir(DATA_FOLDER)
                if any(f.lower().endswith(ext) for ext in supported_extensions)
            ]
            
            if not files:
                raise FileNotFoundError(
                    f"ERROR: No supported files found in '{DATA_FOLDER}' folder. "
                    f"Supported: {', '.join(supported_extensions)}"
                )
            
            doc_path = os.path.join(DATA_FOLDER, files[0])
        
        print(f"Loading file: {doc_path}...")
        
        # Partition the document
        elements = self._partition_file(doc_path)
        
        # Chunk the elements
        chunks = self._chunk_elements(elements)
        
        # Convert to LangChain Documents
        documents = self._elements_to_documents(chunks, source_file=os.path.basename(doc_path))
        print(f"  → Converted to {len(documents)} document chunks")
        
        # Create vector store
        print("Saving to PostgreSQL with pgvector...")
        self._create_vector_store(documents)
        
        print("✓ Done! Vector embeddings saved to PostgreSQL.")
    
    def ingest_all_documents(self) -> None:
        """Ingest all supported files from the data folder with per-file error handling."""
        if not os.path.exists(DATA_FOLDER):
            raise FileNotFoundError(
                f"ERROR: Folder '{DATA_FOLDER}' not found. Please create it and add documents."
            )
        
        # Find all supported files
        supported_extensions = ['.pdf', '.txt', '.docx', '.html', '.csv']
        all_files = [
            f for f in os.listdir(DATA_FOLDER)
            if any(f.lower().endswith(ext) for ext in supported_extensions)
        ]
        
        if not all_files:
            raise FileNotFoundError(
                f"ERROR: No supported files found in '{DATA_FOLDER}' folder. "
                f"Supported: {', '.join(supported_extensions)}"
            )
        
        print(f"Found {len(all_files)} file(s). Processing...")
        
        # Process all files with error isolation
        all_documents = []
        successful_files = []
        failed_files = []
        
        for doc_file in all_files:
            doc_path = os.path.join(DATA_FOLDER, doc_file)
            print(f"\nProcessing: {doc_file}")
            
            try:
                # Partition the document
                elements = self._partition_file(doc_path)
                
                # Chunk the elements
                chunks = self._chunk_elements(elements)
                
                # Convert to LangChain Documents
                documents = self._elements_to_documents(chunks, source_file=doc_file)
                
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
        self._create_vector_store(all_documents)
        
        print("✓ Done! Vector embeddings saved to PostgreSQL.")
        print(f"{'='*60}")
