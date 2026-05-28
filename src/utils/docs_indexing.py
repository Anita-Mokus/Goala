import os
import uuid
from pathlib import Path
import sys
import json
import pypdf


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

def get_id_filename_from_csv(file_path: str) -> dict[uuid.UUID, str]:
    id_filename_map: dict[uuid.UUID, str] = {}
    with open(file_path, "r") as f:
        for line in f:
            id, filename = line.strip().split(",")
            id_filename_map[uuid.UUID(id)] = filename
    return id_filename_map

def get_content_from_txt(file_path: str) -> str:
    for encoding in ("utf-8", "cp1250", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError(f"Could not decode {file_path} with any known encoding")

def get_content_from_pdf(file_path: str) -> str:
    with open(file_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        return "\n".join(page.extract_text() or "" for page in reader.pages)


def creating_id_filename_content_json(
    csv_path: str,
    files_dir: str,
    output_path: str,
) -> None:
    id_filename_map = get_id_filename_from_csv(csv_path)
    records = []
    for doc_id, filename in id_filename_map.items():
        full_path = os.path.join(files_dir, filename.strip())
        try:
            if filename.strip().endswith(".pdf"):
                content = get_content_from_pdf(full_path)
            else:
                content = get_content_from_txt(full_path)
        except Exception as e:
            print(f"Skipping {filename.strip()}: {e}")
            content = ""
        records.append({"id": str(doc_id), "filename": filename.strip(), "content": content})

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print("=" * 30)
    print(f"Created {output_path} with {len(records)} records")
    print("=" * 30)


if __name__ == "__main__":
    sapientia_dir = f"{project_root}/shared/sapientia"

    creating_id_filename_content_json(
        csv_path=f"{project_root}/shared/sapientia_indexed_content_txt_files.csv",
        files_dir=sapientia_dir,
        output_path=f"{project_root}/shared/sapientia_txt_content.json",
    )
    creating_id_filename_content_json(
        csv_path=f"{project_root}/shared/sapientia_indexed_content_pdf_files.csv",
        files_dir=sapientia_dir,
        output_path=f"{project_root}/shared/sapientia_pdf_content.json",
    )
