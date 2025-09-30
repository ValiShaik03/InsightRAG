# RAG Document Search System

## Overview
This project is a **Retrieval-Augmented Generation (RAG) based Document Search Application**.  
It allows users to upload documents, transform them into vector embeddings, and perform semantic search with natural language queries. The system retrieves the most relevant parts of documents and combines them with a language model to generate accurate and context-aware answers.

The application is implemented as a **Streamlit web app** with FAISS for efficient vector search and SQLite (`users.db`) for user management.

---

## Features
- **User Authentication** – Stores user information in `users.db`.
- **Document Upload** – Supports uploading of PDFs and text files.
- **Embedding & Storage** – Documents are converted into embeddings and indexed in FAISS.
- **Semantic Search** – Queries are compared against embeddings for precise retrieval.
- **LLM-powered Responses** – Uses retrieved content to generate natural language answers.
- **Interactive Web Interface** – Built with Streamlit for easy interaction.

---

## Role of `ingest.py`
The `ingest.py` file is responsible for **preprocessing and storing documents**.  
- It splits documents into smaller chunks.  
- Generates embeddings for each chunk using a transformer model.  
- Saves these embeddings into a **FAISS vector index** inside the `data/faiss_index/` folder.  

This step ensures that later queries can quickly retrieve relevant chunks without reprocessing documents each time.

---

## Project Structure
