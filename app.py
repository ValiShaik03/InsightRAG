import os, json
from pathlib import Path
import streamlit as st
import hashlib
import sqlite3
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
import os
from streamlit_option_menu import option_menu
from PyPDF2 import PdfReader
from langchain.document_loaders import PyPDFLoader


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = DATA_DIR / "faiss_index"
CONFIG_PATH = DATA_DIR / "embedding_config.json"
DB_NAME = "users.db"
UPLOAD_DIR = "user_uploaded_files"
load_dotenv()
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
                     user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                     FIRSTNAME TEXT NOT NULL,
                     LASTNAME TEXT NOT NULL,
                     date_of_birth TEXT NOT NULL,
                     email TEXT NOT NULL UNIQUE,
                     password TEXT NOT NULL)
""")
        
        conn.execute("""

        CREATE TABLE IF NOT EXISTS files (
                     file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER NOT NULL,
                     filename TEXT NOT NULL,
                     filepath TEXT NOT NULL,
                     FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
""")    
    print("Database and Tables Initialized")
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def sign_up(FIRSTNAME, LASTNAME, date_of_birth, email, password):
    with sqlite3.connect(DB_NAME) as conn:
        try:
            conn.execute("""
            INSERT INTO users (FIRSTNAME, LASTNAME, date_of_birth, email, password)
            VALUES (?, ?, ?, ?, ?)
            """, (FIRSTNAME, LASTNAME, date_of_birth, email, hash_password(password)))
            conn.commit()
            return True, "Account Created Successfully, Now you can login"
        except sqlite3.IntegrityError:
            return False, "Email already exists, Try Login"
def log_in(email, password):
    with sqlite3.connect(DB_NAME) as conn:
        user = conn.execute("""
        SELECT user_id, FIRSTNAME, LASTNAME FROM users WHERE email = ? AND password = ?
        """, (email, hash_password(password))).fetchone()                  
        return user if user else None
def save_file(user_id, filename, filepath):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        INSERT INTO files (user_id, filename, filepath)
        VALUES (?, ?, ?)
        """, (user_id, filename, filepath))
        conn.commit()
def get_user_files(user_id):
    with sqlite3.connect(DB_NAME) as conn:
        files = conn.execute("""
        SELECT filename, filepath FROM files WHERE user_id = ?
        """, (user_id,)).fetchall()
        return files
    
def delete_file(user_id,filename):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        DELETE FROM files WHERE user_id = ? AND filename = ?
        """, (user_id,filename)).fetchall()
        conn.commit()

init_db()
def get_embeddings_from_config():
    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)
    if cfg["provider"] == "hf":
        return HuggingFaceEmbeddings(model_name=cfg["model"])
    return OpenAIEmbeddings(model=cfg["model"])

st.set_page_config(page_title="HealthMate", page_icon="🩺", layout="wide")

if 'messages' not in st.session_state:
    st.session_state.messages = {}

# --- Sidebar Menu ---
with st.sidebar:
    selected = option_menu(
        "Menu", ["Landing Page", "Login/Signup", "Chat With Docs"],
        icons=["house", "person", "chat-dots"],
        menu_icon="cast", default_index=0
    )

# --- Landing Page ---
if selected == "Landing Page":
    st.markdown("<h1 style='text-align: center; color: #4B8BBE;'>Welcome to DocFriend 📚</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #306998;'>Your AI-powered PDF & Document Chat Assistant</h3>", unsafe_allow_html=True)
    st.write("---")

    st.markdown("## Features")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📄 Upload Documents")
        st.write("Upload your PDFs or documents securely and get them ready for AI-based queries.")

    with col2:
        st.markdown("### 🤖 Chat With Your Documents")
        st.write("Ask questions about the content of your documents and get precise AI-generated answers instantly.")

    with col3:
        st.markdown("### 🔎 Smart Search & Summarization")
        st.write("The AI can summarize documents, extract key points, or answer detailed questions.")

    st.write("---")

    st.image(
        "C:/Users/mdval/OneDrive/Desktop/rag-doc-search-main/rag-doc-search-main/image.webp",
        caption="Your Chat with Documents Made Easy!",
        use_container_width=True
    )

    st.markdown("### Get started by selecting **Login/Signup** from the sidebar, upload your PDFs, and start chatting with them!")


# --- Login/Signup Page ---
elif selected == "Login/Signup":
    st.header("Login/ Signup")
    if "user_id" in st.session_state:
        st.info(f"You are logged in as {st.session_state['FIRSTNAME']} {st.session_state['LASTNAME']}")
        if st.button("Logout"):
            st.session_state.clear()
            st.success("Logged Out Successfully!")
    else:
        action = st.selectbox("Select an action", ['Login', 'Sign Up'])
        if action == "Sign Up":
            st.subheader("Sign Up")
            first_name = st.text_input("First Name")
            last_name = st.text_input("Last Name")
            dob = st.date_input("Date Of Birth")
            email = st.text_input("Email")
            password = st.text_input("Password", type='password')
            if st.button("Sign Up"):
                success, msg = sign_up(first_name, last_name, dob, email, password)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
        elif action == "Login":
            st.subheader("Login")
            email = st.text_input("Email")
            password = st.text_input("Password", type='password')
            if st.button("Login"):
                user = log_in(email, password)
                if user:
                    st.session_state['user_id'], st.session_state['FIRSTNAME'], st.session_state['LASTNAME'] = user
                    st.success(f"Logged in as: {user[1]} {user[2]}!")
                    st.session_state.messages[st.session_state['user_id']] = []
                else:
                    st.error("Invalid Email or Password")

# --- Chat With Docs Page ---
elif selected == "Chat With Docs":
    if "user_id" not in st.session_state:
        st.warning("Please login first to chat with your documents.")
    else:
        st.title("📚 Chat With Your Documents")

        # --- Upload PDFs ---
        st.subheader("Upload Your PDF Documents")
        uploaded_files = st.file_uploader(
            "Choose PDF files", type=["pdf"], accept_multiple_files=True
        )

        # Ensure user directory exists
        user_upload_dir = os.path.join(UPLOAD_DIR, f"user_{st.session_state['user_id']}")
        os.makedirs(user_upload_dir, exist_ok=True)

        if uploaded_files:
            embedder = get_embeddings_from_config()

            # Prepare user-specific FAISS index directory
            user_index_dir = os.path.join(INDEX_DIR, f"user_{st.session_state['user_id']}")
            os.makedirs(user_index_dir, exist_ok=True)

            all_docs = []
            for uploaded_file in uploaded_files:
                file_path = os.path.join(user_upload_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                save_file(st.session_state["user_id"], uploaded_file.name, file_path)

                # --- Load document safely ---
                from langchain_community.document_loaders import PyPDFLoader
                loader = PyPDFLoader(file_path)
                docs = loader.load()

                # Skip empty PDFs
                non_empty_docs = [d for d in docs if d.page_content.strip()]
                if not non_empty_docs:
                    st.warning(f"Skipped empty document: {uploaded_file.name}")
                    continue

                all_docs.extend(non_empty_docs)
                st.success(f"Uploaded {uploaded_file.name} successfully!")

            # --- Create or update FAISS index ---
            if all_docs:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
                splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                chunks = splitter.split_documents(all_docs)

                from langchain_community.vectorstores import FAISS
                vs = FAISS.from_documents(chunks, embedder)
                vs.save_local(user_index_dir)
                st.success("Documents indexed successfully!")

        # --- Chat with Documents ---
        user_index_dir = os.path.join(INDEX_DIR, f"user_{st.session_state['user_id']}")
        if not os.path.exists(user_index_dir):
            st.info("Upload some PDFs first to start chatting.")
        else:
            embedder = get_embeddings_from_config()
            vs = FAISS.load_local(user_index_dir, embedder, allow_dangerous_deserialization=True)
            retriever = vs.as_retriever(search_kwargs={"k": 4})
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

            if "history" not in st.session_state:
                st.session_state.history = []

            user_q = st.chat_input("Ask about your documents...")
            if user_q:
                docs = retriever.get_relevant_documents(user_q)
                context = "\n\n".join([d.page_content for d in docs])
                from langchain_core.prompts import ChatPromptTemplate
                prompt = ChatPromptTemplate.from_template(
                    "Use this context to answer:\n{context}\n\nQuestion: {question}"
                )
                resp = llm.invoke(prompt.format_messages(context=context, question=user_q))
                st.session_state.history.append(("user", user_q))
                st.session_state.history.append(("assistant", resp.content))

            for role, msg in st.session_state.history:
                with st.chat_message(role):
                    st.markdown(msg)
