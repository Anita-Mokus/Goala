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
    try:
        run(output_dir=output_dir)
        print("\n" + "=" * 60)
        print("Scraping completed. Run the ingest CLI to index the results.")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\nERROR: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
