"""
Document chunking logic.
Handles semantic chunking and conversion to LangChain Documents.
"""
from typing import List
from unstructured.chunking.title import chunk_by_title
from langchain_core.documents import Document


def chunk_elements(
    elements: List,
    chunk_max_chars: int,
    chunk_new_after: int,
    chunk_overlap: int,
    multipage_sections: bool
) -> List:
    """
    Chunk elements using unstructured's chunk_by_title strategy.
    This preserves section boundaries and respects semantic structure.
    
    Args:
        elements: List of unstructured Element objects
        chunk_max_chars: Hard maximum chunk size
        chunk_new_after: Preferred chunk size
        chunk_overlap: Overlap between chunks
        multipage_sections: Allow sections to span pages
        
    Returns:
        List of chunked elements (CompositeElement, Table, or TableChunk)
    """
    try:
        chunks = chunk_by_title(
            elements,
            max_characters=chunk_max_chars,
            new_after_n_chars=chunk_new_after,
            overlap=chunk_overlap,
            multipage_sections=multipage_sections,
        )
        print(f"  → Created {len(chunks)} semantic chunks")
        return chunks
        
    except Exception as e:
        print(f"  ✗ Error chunking elements: {e}")
        raise


def elements_to_documents(
    chunks: List,
    source_file: str = None,
    dataset_key: str | None = None,
) -> List[Document]:
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
            'dataset': dataset_key,
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
