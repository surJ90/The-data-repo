import streamlit as st
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

# --- Helper Function to Format Retrieved Documents ---
def format_docs(docs):
    """Combines retrieved documents into a single string."""
    return "\n\n".join(doc.page_content for doc in docs)

# --- Main RAG and Generation Logic ---
def create_rag_chain(api_key, context_documents):
    """
    Sets up the RAG pipeline based on the user's provided context.
    This corresponds to the "RAG Pipeline" in your diagram.
    """
    # 1. Set up the LLM (Gemini) and Embedding Model
    # This corresponds to the "LLM Model" and "Embedding Model" boxes
    os.environ["GOOGLE_API_KEY"] = api_key
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # 2. Text Splitting and Chunking
    # This corresponds to the "Text Splitting" -> "Chunking" boxes
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_text(context_documents)

    # 3. Embedding and Storing in Vector DB
    # This corresponds to "Embedding" -> "Vector DB"
    try:
        vectorstore = Chroma.from_texts(texts=splits, embedding=embeddings)
    except Exception as e:
        st.error(f"Error creating vector store: {e}")
        st.stop()
        
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3}) # Retrieve top 3 chunks

    # 4. Define the Prompt Template
    # This corresponds to the "Prompt + Query + Retrieved Enhanced content" logic
    template = """
    You are an assistant for generating test cases.
    Answer the user's request based ONLY on the following context:
    
    {context}
    
    Request: {question}
    
    Answer:
    """
    prompt = ChatPromptTemplate.from_template(template)

    # 5. Build the RAG Chain using LCEL (LangChain Expression Language)
    # This combines the entire "Retrieval Pipeline" flow
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain

# --- Streamlit Frontend ---
st.set_page_config(page_title="Simple RAG App", layout="wide")
st.title("🤖 AI Test Case Generator (from your diagram)")

# 1. Get API Key in the sidebar
with st.sidebar:
    st.header("Configuration")
    google_api_key = st.text_input("Enter your Google API Key:", type="password")
    if not google_api_key:
        st.warning("Please enter your Google API Key to proceed.")
        st.stop()

# 2. Main app layout
st.header("1. Provide Your Knowledge Base")
st.write("This is the 'Uploading Bricks Template' from your diagram.")
context_text = st.text_area("Paste your 'Bricks Template' content here:", height=200, 
                            placeholder="Paste all your technical documentation, knowledge, or 'bricks' here...")

st.header("2. Provide Your Query")
st.write("This is the 'Uploading Test Case Template' (as a query) from your diagram.")
query_text = st.text_input("Enter your 'Test Case' prompt or query:",
                           placeholder="e.g., 'Generate a test case for user login functionality based on the bricks.'")

# 3. Generate Button
if st.button("Generate Content", type="primary"):
    if not context_text or not query_text:
        st.error("Please provide both the 'Bricks Template' context and a query.")
    else:
        with st.spinner("Processing... (Chunking, Embedding, and Generating)"):
            try:
                # Create the RAG chain (this does the RAG Pipeline part)
                rag_chain = create_rag_chain(google_api_key, context_text)
                
                # Run the Retrieval Pipeline
                st.session_state.answer = rag_chain.invoke(query_text)
                
                st.subheader("✅ Generated Content")
                st.markdown(st.session_state.answer)
            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.exception(e)
