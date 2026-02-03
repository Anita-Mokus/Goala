"""
Display the project structure in a tree format.
"""
import os
from pathlib import Path


def print_tree(directory, prefix="", ignore_dirs=None, ignore_files=None):
    """Print directory tree structure."""
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__pycache__', '.venv', 'venv', 'chroma_db', '.vscode'}
    if ignore_files is None:
        ignore_files = {'.gitattributes', '.gitignore'}
    
    try:
        entries = sorted(Path(directory).iterdir(), key=lambda x: (not x.is_dir(), x.name))
    except PermissionError:
        return
    
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        
        # Skip ignored items
        if entry.name in ignore_dirs or entry.name in ignore_files:
            continue
        
        # Prepare tree symbols
        current = "└── " if is_last else "├── "
        extension = "    " if is_last else "│   "
        
        # Print entry
        if entry.is_dir():
            print(f"{prefix}{current}📁 {entry.name}/")
            print_tree(entry, prefix + extension, ignore_dirs, ignore_files)
        else:
            # Add emoji based on file type
            emoji = "📄"
            if entry.suffix == ".py":
                emoji = "🐍"
            elif entry.suffix in [".md", ".txt"]:
                emoji = "📝"
            elif entry.suffix in [".bat", ".sh"]:
                emoji = "🚀"
            elif entry.suffix in [".json", ".yaml", ".yml"]:
                emoji = "⚙️"
            elif entry.name == ".env":
                emoji = "🔐"
            
            print(f"{prefix}{current}{emoji} {entry.name}")


def main():
    """Display project structure."""
    print("\n" + "=" * 70)
    print("  AI CHAT FLOW - PROJECT STRUCTURE")
    print("=" * 70 + "\n")
    
    project_root = Path(__file__).parent
    print(f"📁 {project_root.name}/")
    print_tree(project_root)
    
    print("\n" + "=" * 70)
    print("Legend:")
    print("  📁 = Directory")
    print("  🐍 = Python file")
    print("  📝 = Documentation")
    print("  🚀 = Executable script")
    print("  🔐 = Environment config")
    print("  📄 = Other file")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
