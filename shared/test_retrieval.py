"""
Quick test script to verify retrieval quality.
Run with: python test_retrieval.py
Or in Docker: docker-compose exec api python test_retrieval.py
"""
from src.services.rag_service import get_rag_service

# Test questions that were failing
test_questions = [
    "Mely promóciókat vonja vissza a 3. módosítás, és mikor ér véget?",
    'Hasonlítsa össze a "Kártya Mánia!" Visa bankkártya igénylést és a "Kártyára Fel!" Visa bankkártya igénylést.',
    "Magyarázza el a különbséget a Promóció Szervezője és a Kedvezmény juttatója között.",
]

print("\n" + "="*70)
print("RAG RETRIEVAL QUALITY TEST")
print("="*70)

rag = get_rag_service()

for question in test_questions:
    print(f"\n{'='*70}")
    print(f"Q: {question}\n")
    
    # Get retrieved chunks
    results = rag.retriever.get_relevant_documents(question)
    print(f"Retrieved {len(results)} chunks:\n")
    
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get('source', 'unknown')
        elem_type = doc.metadata.get('element_type', 'unknown')
        page = doc.metadata.get('page_number', '?')
        content_preview = doc.page_content[:150].replace('\n', ' ')
        
        print(f"[{i}] {source} | Page {page} | {elem_type}")
        print(f"    {content_preview}...\n")
    
    # Get full answer
    print("Full Answer:")
    answer = rag.query(question)
    print(f"{answer}\n")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
