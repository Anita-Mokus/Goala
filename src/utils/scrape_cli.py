"""
Command-line interface for scraping ms.sapientia.ro Felvételi section.
Saves each page as a .txt file into the data/ folder for ingestion.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.scraper.runner import run, DEFAULT_OUTPUT_DIR


def main():
    print("\n" + "=" * 60)
    print("Goala — Sapientia Felvételi Scraper")
    print("=" * 60 + "\n")

    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT_DIR
    max_pages = None
    max_pdfs = None
    if len(sys.argv) > 2:
        max_pages = int(sys.argv[2])
        if max_pages <= 0:
            raise ValueError("max_pages must be > 0")
    if len(sys.argv) > 3:
        max_pdfs = int(sys.argv[3])
        if max_pdfs <= 0:
            raise ValueError("max_pdfs must be > 0")
    elif max_pages is not None:
        max_pdfs = max_pages
    try:
        run(output_dir=output_dir, max_pages=max_pages, max_pdfs=max_pdfs)
        print("\n" + "=" * 60)
        print("Scraping completed. Run the ingest CLI to index the results.")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\nERROR: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
