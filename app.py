import os
import spacy
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings.spacy_embeddings import SpacyEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
import requests

# Load environment variables from a .env file (if exists)
load_dotenv()

# Load AI21 API key from environment variable or replace with your key
AI21_API_KEY = os.getenv("AI21_API_KEY", "Your_Key")
# Ensure the model is installed and loaded
nlp = spacy.load("en_core_web_sm")
embeddings = SpacyEmbeddings(model_name="en_core_web_sm")

def pdf_read(pdf_doc):
    text = ""
    for pdf in pdf_doc:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    return chunks

def vector_store(text_chunks):
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_db")

def get_conversational_response(context, question, api_key):
    try:
        url = "https://api.ai21.com/studio/v1/j2-jumbo-instruct/complete"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": f"Context: {context}\nQuestion: {question}\nAnswer:",
            "numResults": 1,
            "maxTokens": 200,
            "temperature": 0.7
        }

        response = requests.post(url, json=payload, headers=headers)
        response_json = response.json()
        
        if response.status_code == 200 and response_json.get('completions'):
            return response_json['completions'][0]['data']['text']
        else:
            print("Failed to get response from AI21. Check API key or model availability.")
            return "An error occurred."
    except Exception as e:
        print(f"Failed to create conversational response: {e}")
        return "An error occurred."

def user_input(user_question):
    new_db = FAISS.load_local("faiss_db", embeddings, allow_dangerous_deserialization=True)
    retriever = new_db.as_retriever()
    documents = retriever.invoke(user_question)  # Replace get_relevant_documents with invoke
    context = " ".join([doc.page_content for doc in documents])
    response = get_conversational_response(context, user_question, AI21_API_KEY)
    st.write("Reply: ", response)

def main():
    st.set_page_config("Chat PDF")
    st.header("NexaSync AI")

    user_question = st.text_input("Ask a Question from the PDF Files")

    if user_question:
        user_input(user_question)

    with st.sidebar:
        st.title("Menu:")
        pdf_doc = st.file_uploader("Upload your PDF Files and Click on the Submit & Process Button", accept_multiple_files=True)
        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                raw_text = pdf_read(pdf_doc)
                text_chunks = get_chunks(raw_text)
                vector_store(text_chunks)
                st.success("Done")

if __name__ == "__main__":
    main()
