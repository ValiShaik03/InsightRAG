import os, json
from pathlib import Path
from dotenv import load_dotenv
from tqdm import tqdm
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
DATA_DIR = BASE_DIR / "data"
CONFIG_PATH = DATA_DIR / "embedding_config.json"

def get_embeddings():
    provider = os.getenv("EMBEDDINGS_PROVIDER", "openai").lower()
    model = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
    if provider == "hf":
        return "hf", model, HuggingFaceEmbeddings(model_name=model)
    return "openai", model, OpenAIEmbeddings(model=model)

def load_documents():
    loaders = [
        DirectoryLoader(str(DOCS_DIR), glob="**/*.pdf", loader_cls=PyPDFLoader),
        DirectoryLoader(str(DOCS_DIR), glob="**/*.txt", loader_cls=TextLoader),
        DirectoryLoader(str(DOCS_DIR), glob="**/*.md", loader_cls=TextLoader),
        DirectoryLoader(str(DOCS_DIR), glob="**/*.docx", loader_cls=Docx2txtLoader),
    ]
    docs = []
    for loader in loaders:
        loaded_docs = loader.load()
        print(f"Loaded {len(loaded_docs)} documents from {loader.glob}")
        # Filter out empty documents
        for doc in loaded_docs:
            if doc.page_content.strip():  # Only keep documents with text
                docs.append(doc)
            else:
                print(f"Skipped empty document: {doc.metadata.get('source', 'unknown')}")
    return docs

def main():
    load_dotenv()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # --- Load documents ---
    docs = load_documents()
    if not docs:
        print("No valid documents found in the docs folder! Exiting.")
        return

    # --- Split into chunks ---
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    print(f"Total chunks created: {len(chunks)}")
    if not chunks:
        print("No chunks generated from documents! Exiting.")
        return

    # --- Create embeddings and FAISS index ---
    provider, model, embedder = get_embeddings()
    vs = FAISS.from_documents(chunks, embedder)
    index_path = DATA_DIR / "faiss_index"
    vs.save_local(str(index_path))
    print(f"FAISS index saved to {index_path}")

    # --- Save config ---
    with open(CONFIG_PATH, "w") as f:
        json.dump({"provider": provider, "model": model}, f)
    print(f"Embedding config saved to {CONFIG_PATH}")

if __name__ == "__main__":
    main()
