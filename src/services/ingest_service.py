"""
Document Ingestion Service.
Handles loading PDFs and other documents, creating semantic chunks,
and storing vector embeddings in PostgreSQL with pgvector.

Refactored to use unstructured 0.18.32 directly for better partitioning
and semantic chunking with chunk_by_title strategy.
"""
import os
import re
from typing import List, Optional
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
    CHUNKING_STRATEGY,
    DEFINITION_CHUNK_MIN_CHARS,
    DEFINITION_CHUNK_MAX_CHARS,
    SEMANTIC_CHUNK_BREAKPOINT_TYPE,
    SEMANTIC_CHUNK_BREAKPOINT_AMOUNT,
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
        self.chunking_strategy = CHUNKING_STRATEGY
        self.definition_min_chars = DEFINITION_CHUNK_MIN_CHARS
        self.definition_max_chars = DEFINITION_CHUNK_MAX_CHARS
        self.semantic_breakpoint_type   = SEMANTIC_CHUNK_BREAKPOINT_TYPE
        self.semantic_breakpoint_amount = SEMANTIC_CHUNK_BREAKPOINT_AMOUNT
        
        # Partitioning configuration
        self.pdf_strategy = PDF_STRATEGY
        self.languages = [PDF_LANGUAGE] if PDF_LANGUAGE else None

        # Pre-compiled regex for definition/clause boundaries in Hungarian banking documents.
        # A match on the first non-whitespace characters of an element signals a new chunk.
        # Covers: 1.  1.1.  1.1.1.  |  a)  b)  |  (a)  (1)  |  I.  II.  III.  |  ## heading  |  1. §
        self._definition_boundary_re = re.compile(
            r'^\s*'
            r'(?:'
            r'\d+\.\d*\.?\d*\.?'      # 1.  /  1.1.  /  1.1.1.
            r'|[a-z]\)'               # a)  b)  c)
            r'|\([a-z0-9]+\)'         # (a)  (1)  (i)
            r'|[IVXLCDM]{1,6}\.'      # I.  II.  III.  (roman numerals)
            r'|#{1,4} '               # ## Markdown heading
            r'|\d+\.\s*§'            # 1. § (Hungarian law paragraph style)
            r')'
            r'\s*',
            re.MULTILINE,
        )
    
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
    
    @staticmethod
    def _extract_doc_id(filename: str) -> Optional[str]:
        """
        Extract a normalised regulation document ID from the source filename.

        Examples:
            'H-68-2024-20251120010000.pdf'   -> 'H-68/2024'
            'H-1339-2025-20251120010000.pdf' -> 'H-1339/2025'
            'H-776-2023-20251120010000.pdf'  -> 'H-776/2023'

        This value is stored in every chunk's metadata as ``doc_id`` and used
        by the retriever for metadata-filtered search.
        """
        if not filename:
            return None
        match = re.match(r'(H-\d+)-(\d{4})', filename, re.IGNORECASE)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        return None

    def _chunk_by_definition(self, elements: List) -> List[dict]:
        """
        Definition-level chunking: produce one chunk per glossary entry, numbered
        paragraph, or regulation clause — regardless of character count.

        Split triggers:
          - Element whose ``category`` is ``Title`` or ``Header``
          - Element whose text begins with a numbered/lettered boundary marker
            (1., 1.1., a), (1), I., §, ## heading …)

        Post-processing:
          - Fragments shorter than ``DEFINITION_CHUNK_MIN_CHARS`` are merged into
            the preceding chunk so very short headers don’t become orphan chunks.
          - Entries longer than ``DEFINITION_CHUNK_MAX_CHARS`` are hard-split on
            sentence boundaries to keep embeddings focused.

        Returns:
            List of dicts: {text, page_number, element_type}
        """
        # Collect (text, page_number, category) from raw elements, skipping blanks
        raw: List[tuple] = []
        for el in elements:
            t = (el.text or '').strip() if hasattr(el, 'text') else ''
            if not t:
                continue
            page = getattr(el.metadata, 'page_number', None) if hasattr(el, 'metadata') else None
            cat  = el.category if hasattr(el, 'category') else 'NarrativeText'
            raw.append((t, page, cat))

        if not raw:
            return []

        # ── Phase 1: split on boundaries ────────────────────────────────────────
        chunks:    List[dict] = []
        buf_texts: List[str]  = []
        buf_page = raw[0][1]
        buf_cat  = raw[0][2]

        def _flush():
            if not buf_texts:
                return
            merged = '\n'.join(buf_texts).strip()
            if merged:
                chunks.append({'text': merged, 'page_number': buf_page, 'element_type': buf_cat})

        for txt, page, cat in raw:
            is_title    = cat in ('Title', 'Header')
            is_boundary = bool(self._definition_boundary_re.match(txt))
            if is_title or is_boundary:
                _flush()
                buf_texts = [txt]
                buf_page  = page
                buf_cat   = cat
            else:
                buf_texts.append(txt)
                if page and buf_page is None:
                    buf_page = page

        _flush()  # flush the final accumulated chunk

        # ── Phase 2: merge tiny fragments & hard-split huge entries ─────────────
        refined: List[dict] = []
        for chunk in chunks:
            text = chunk['text']
            if len(text) < self.definition_min_chars and refined:
                # Absorb short fragment into the previous chunk
                refined[-1]['text'] += '\n' + text
            elif len(text) > self.definition_max_chars:
                # Hard-split on sentence boundaries
                sentences = re.split(r'(?<=[.!?])\s+', text)
                buf = ''
                for sent in sentences:
                    if buf and len(buf) + 1 + len(sent) > self.definition_max_chars:
                        refined.append({**chunk, 'text': buf.strip()})
                        buf = sent
                    else:
                        buf = (buf + ' ' + sent).strip() if buf else sent
                if buf.strip():
                    refined.append({**chunk, 'text': buf.strip()})
            else:
                refined.append(chunk)

        print(f"  → Created {len(refined)} definition-level chunks")
        return refined

    def _chunk_by_semantic(self, elements: List) -> List[dict]:
        """
        Semantic chunking: embed consecutive sentences with the same BGE-M3 model
        used at retrieval time, then split wherever cosine similarity drops sharply.
        One chunk = one coherent idea, regardless of character count.

        Tuning via config / .env:
          SEMANTIC_CHUNK_BREAKPOINT_TYPE   — "percentile" | "standard_deviation" |
                                             "interquartile" | "gradient"
          SEMANTIC_CHUNK_BREAKPOINT_AMOUNT — for "percentile": 0–100
                                             (95 = only the sharpest 5% drops become splits)

        Returns:
            List of dicts: {text, page_number, element_type}
        """
        from langchain_experimental.text_splitter import SemanticChunker

        # 1. Collect (text, page_number) from raw elements, skipping blanks
        raw: List[tuple] = []
        for el in elements:
            t = (el.text or '').strip() if hasattr(el, 'text') else ''
            if not t:
                continue
            page = getattr(el.metadata, 'page_number', None) if hasattr(el, 'metadata') else None
            raw.append((t, page))

        if not raw:
            return []

        # 2. Build full document text + char-offset → page_number lookup table
        page_map: List[tuple] = []  # [(char_start, page_number), ...]
        full_text = ''
        for txt, page in raw:
            page_map.append((len(full_text), page))
            full_text += txt + '\n'

        def _get_page(offset: int) -> Optional[int]:
            """Binary-search page_map for the page containing char offset."""
            lo, hi = 0, len(page_map) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if page_map[mid][0] <= offset:
                    lo = mid
                else:
                    hi = mid - 1
            return page_map[lo][1]

        # 3. Run SemanticChunker on the full document text
        chunker = SemanticChunker(
            self.embedding_function,
            breakpoint_threshold_type=self.semantic_breakpoint_type,
            breakpoint_threshold_amount=self.semantic_breakpoint_amount,
            add_start_index=True,   # stores char offset in chunk metadata['start_index']
        )

        docs = chunker.create_documents([full_text])

        # 4. Map each chunk back to its source page via the char-offset table
        result: List[dict] = []
        for doc in docs:
            chunk_text = doc.page_content.strip()
            if not chunk_text:
                continue
            # Prefer start_index injected by TextSplitter; fall back to string search
            offset = doc.metadata.get('start_index')
            if offset is None:
                probe = chunk_text[:80]
                offset = full_text.find(probe)
                if offset < 0:
                    offset = 0
            page = _get_page(offset)
            result.append({
                'text':         chunk_text,
                'page_number':  page,
                'element_type': 'SemanticChunk',
            })

        print(f"  → Created {len(result)} semantic chunks")
        return result

    def _elements_to_documents(self, chunks, source_file: str = None) -> List[Document]:
        """
        Convert chunks to LangChain Document objects.

        Handles both:
          - list of dicts  (output of ``_chunk_by_definition``)
          - list of unstructured Element objects  (output of ``_chunk_elements``)

        Always injects ``doc_id`` metadata extracted from the source filename
        (e.g. ``H-68/2024``) so that the retriever can filter by document.
        """
        doc_id = self._extract_doc_id(source_file) if source_file else None
        documents = []

        for chunk in chunks:
            # ── Dict chunks from definition-level chunking ─────────────────────
            if isinstance(chunk, dict):
                metadata: dict = {
                    'source':       source_file or 'unknown',
                    'element_type': chunk.get('element_type', 'Definition'),
                }
                if chunk.get('page_number'):
                    metadata['page_number'] = chunk['page_number']
                if source_file:
                    metadata['filename'] = source_file
                if doc_id:
                    metadata['doc_id'] = doc_id
                documents.append(Document(page_content=chunk['text'], metadata=metadata))
                continue

            # ── Unstructured Element objects from chunk_by_title ───────────────
            metadata = {
                'source':       source_file or getattr(chunk.metadata, 'filename', 'unknown'),
                'element_type': getattr(chunk, 'category', 'Unknown'),
                'element_id':   getattr(chunk, 'id', None),
            }
            if getattr(chunk.metadata, 'page_number', None):
                metadata['page_number'] = chunk.metadata.page_number
            if getattr(chunk.metadata, 'filename', None):
                metadata['filename'] = chunk.metadata.filename
            if getattr(chunk.metadata, 'file_directory', None):
                metadata['file_directory'] = chunk.metadata.file_directory
            if doc_id:
                metadata['doc_id'] = doc_id
            documents.append(Document(page_content=chunk.text, metadata=metadata))

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
        
        # Chunk using the configured strategy
        if self.chunking_strategy == 'semantic':
            print("  Using semantic chunking strategy (embedding-based)")
            chunks = self._chunk_by_semantic(elements)
        elif self.chunking_strategy == 'definition':
            print("  Using definition-level chunking strategy")
            chunks = self._chunk_by_definition(elements)
        else:
            print("  Using chunk_by_title strategy")
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
                
                # Chunk using the configured strategy
                if self.chunking_strategy == 'semantic':
                    chunks = self._chunk_by_semantic(elements)
                elif self.chunking_strategy == 'definition':
                    chunks = self._chunk_by_definition(elements)
                else:
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
