import PyPDF2
import os
import subprocess
import uuid
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.embeddings import OllamaEmbeddings 
import chromadb
from chromadb.utils.embedding_functions.ollama_embedding_function import (
    OllamaEmbeddingFunction,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Embedding function for ChromaDB
ollama_ef = OllamaEmbeddingFunction(
    url="http://localhost:11434",
    model_name="qwen3-embedding:4b",
)

client = chromadb.Client()
collection = client.create_collection(name="pdf_collection", embedding_function=ollama_ef)


def process_pdf(filepath):
    """Extract text from PDF file and keep page-wise data"""
    pages_data = []
    try:
        with open(filepath, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for i, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text()
                if text and text.strip():
                    pages_data.append({"page": i, "text": text.strip()})

        chunks = hybrid_split_pdf_text(pages_data)
        print(chunks)
        store_pdf_in_DB(chunks)
        return
    except Exception as e:
        raise Exception(f"Failed to process PDF: {str(e)}")


def hybrid_split_pdf_text(pages_data):
    """
    First split semantically, then normalize with RecursiveCharacterTextSplitter.
    Preserves page metadata.
    """

    # Step 1: Semantic splitting
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    semantic_splitter = SemanticChunker(
        embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=80  # adjust 60–80 as needed
    )

    # Step 2: Recursive splitter for normalization
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,     # adjust based on your LLM context window
        chunk_overlap=50,   # overlap for context preservation
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = []
    for page in pages_data:
        # Semantic splitting per page
        semantic_chunks = semantic_splitter.split_text(page["text"])

        for sem_chunk in semantic_chunks:
            # Normalize each semantic chunk into smaller recursive chunks
            recursive_chunks = recursive_splitter.split_text(sem_chunk)

            for rec_chunk in recursive_chunks:
                # Filter out very tiny chunks (optional)
                if len(rec_chunk.split()) > 4:  # ignore chunks < 3 words
                    chunks.append({
                        "text": rec_chunk,
                        "page": page["page"]
                    })

    return chunks


def store_pdf_in_DB(chunks):
    try:
        print(f"\033[92m Storing PDF chunks in ChromaDB... \033[0m")

        collection.add(
            documents=[c['text'] for c in chunks],
            metadatas=[{'page': c['page']} for c in chunks],
            ids=[str(uuid.uuid4()) for _ in chunks]
        )

        print("\033[92m PDF data stored in DB successfully. \033[0m")
    except Exception as e:
        print(f"Error storing PDF in DB: {e}")


def retriverPDF(query: str) -> list[str]:
    try:
        results = collection.query(
            query_texts=[query],
            n_results=10
        )
        print("results", results)

        retrieved_result = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        for doc, meta in zip(documents, metadatas):
            retrieved_result.append({
                "text": doc,
                "metadata": meta
            })

        return retrieved_result

    except Exception as e:
        print(f"Error during retrieval: {e}")
        return []
# -----------------------------------------------------------All the above functions are connected--------------------------------
def extract_audio_from_video(video_path, output_dir):
    """Extract audio from video file using ffmpeg"""
    try:
        output_path = os.path.join(output_dir, f"audio_{os.path.basename(video_path)}.wav")
        command = [
            'ffmpeg', '-i', video_path, 
            '-vn', '-acodec', 'pcm_s16le', 
            '-ar', '16000', '-ac', '1', 
            output_path, '-y'
        ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except Exception as e:
        raise Exception(f"Failed to extract audio from video: {str(e)}")