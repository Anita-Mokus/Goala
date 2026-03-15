"""
RAG chain builder.
Constructs the LangChain pipeline: retriever → format → prompt → LLM → parse.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


def format_docs(docs):
    """Format retrieved documents for the prompt."""
    return "\n\n".join(doc.page_content for doc in docs)


def create_rag_chain(retriever, prompt_template: str, llm):
    """
    Create a RAG chain from components.
    
    Args:
        retriever: LangChain retriever (e.g., from PGVector)
        prompt_template: Prompt template string with {context} and {question}
        llm: LLM instance from provider
        
    Returns:
        Runnable chain that takes a question and returns an answer
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    
    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return chain
