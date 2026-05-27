import os
import uuid
from pathlib import Path
import sys


project_root = Path(__file__).parent.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def indexing_sapientia_txt_files(file_path: str) -> None:
    indexed_content: dict[str, uuid.UUID] = {}
    with open(f"{project_root}/shared/sapientia_indexed_content_txt_files.csv", "w") as f:
        for file in os.listdir(file_path):
            if file.endswith(".txt"):
                indexed_content[file] = uuid.uuid4()
                f.write(f"{indexed_content[file]}, {file}\n")
    
    print ("=" * 30)
    print (f"Indexed {len(indexed_content)} txt files")
    print ("=" * 30)

def indexing_sapientia_pdf_files(file_path: str) -> None:
    indexed_content: dict[str, uuid.UUID] = {}
    with open(f"{project_root}/shared/sapientia_indexed_content_pdf_files.csv", "w") as f:
        for file in os.listdir(file_path):
            if file.endswith(".pdf"):
                indexed_content[file] = uuid.uuid4()
                f.write(f"{indexed_content[file]}, {file}\n")

    print ("=" * 30)
    print (f"Indexed {len(indexed_content)} pdf files")
    print ("=" * 30)

if __name__ == "__main__":
    indexing_sapientia_txt_files(f"{project_root}/shared/sapientia")
    indexing_sapientia_pdf_files(f"{project_root}/shared/sapientia")
