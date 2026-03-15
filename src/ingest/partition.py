"""
Document partitioning logic.
Handles routing to appropriate unstructured partitioner based on file type.
"""
import os
from typing import List
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.text import partition_text
from unstructured.partition.auto import partition


def partition_file(file_path: str, pdf_strategy: str, languages: List[str] = None) -> List:
    """
    Partition a document file using unstructured library.
    Automatically routes to the appropriate partitioner based on file extension.
    
    Args:
        file_path: Path to the document file
        pdf_strategy: Strategy for PDF partitioning (auto/fast/hi_res/ocr_only)
        languages: List of languages for OCR (e.g., ['hun'])
        
    Returns:
        List of unstructured Element objects
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_extension == '.pdf':
            print(f"  Partitioning PDF with strategy='{pdf_strategy}', languages={languages}")
            elements = partition_pdf(
                filename=file_path,
                strategy=pdf_strategy,
                languages=languages,
                include_page_breaks=True,
            )
        elif file_extension == '.txt':
            print(f"  Partitioning TXT file")
            elements = partition_text(
                filename=file_path,
            )
        else:
            print(f"  Using auto-detection for {file_extension} file")
            elements = partition(
                filename=file_path,
                languages=languages,
            )
        
        print(f"  → Extracted {len(elements)} elements")
        return elements
        
    except Exception as e:
        print(f"  ✗ Error partitioning file: {e}")
        raise
