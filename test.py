from src.services.ingest_liverag import IngestLiveRAG
from datasets import load_dataset
from src.core.config import HUGGINGFACE_TOKEN


if __name__ == "__main__":
    ds = load_dataset(
            "LiveRAG/Benchmark",
            split="train",
            token=HUGGINGFACE_TOKEN or None,
        )
    print(type(ds))

    ingestor = IngestLiveRAG()
    ingestor._dataset_to_documents(ds)
    print("Dataset converted to documents:")
    
    # Load the 'question' field dataset into a list
    
    questions = ds["Question"]
    print(f"Loaded {len(questions)} questions from the dataset.")

