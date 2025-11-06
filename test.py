# # from chromadb.utils.embedding_functions.ollama_embedding_function import (
# #     OllamaEmbeddingFunction,
# # )

# # ollama_ef = OllamaEmbeddingFunction(
# #     url="http://localhost:11434",
# #     model_name="embeddinggemma",
# # )

# # embeddings = ollama_ef(["This is my first text to embed",
# #                         "This is my second document"])
# # print(embeddings)


import ollama
from ollama import chat


# import requests

# OLLAMA_SERVER = "http://10.51.122.75:11434"
        
# MODEL = "gpt-oss:20b"   

# url = f"{OLLAMA_SERVER}/api/generate"
# payload = {
#     "model": MODEL,
#     "prompt": "Hello from Python backend!"
# }

# response = requests.post(
#     url, 
#     json={
#         "model": "gpt-oss:20b",
#         "prompt": "hi",
#         "stream": False
# })

# data = response.json()

# # Print the generated text
# print(data)

# # for line in response.iter_lines():
# #     if line:
# #         print(line.decode("utf-8"))

# response = ollama.chat(model='gpt-oss:20b-cloud', messages=[
#             {'role': 'user', 'content': "Can you be a AGENT for my RAG application?"}
#         ])
        
# print(response['message']['content'])

# response = chat(
#   model='qwen3-vl:235b-cloud',
#   messages=[
#     {
#       'role': 'user',
#       'content': 'This is a bill, Extract all the important information from it. and also find out what kind of bill is this? Answer is structured json format and null for missing fields. ',
#       'images': ['rapidoTest.jpg'],
#     }
#   ],
# )

# print(response.message.content)


from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.embeddings import OllamaEmbeddings  # or OpenAIEmbeddings

# embeddings = OllamaEmbeddings(model="embeddinggemma")

# splitter = SemanticChunker(embeddings, breakpoint_threshold_type="percentile", breakpoint_threshold_amount=60)

# chunks = splitter.split_text(pdf_text)
# print(f"Total chunks created: {len(chunks)}")

# for chunk in chunks:
#     print(chunk)
#     print("--------------------------------\n")

# import PyPDF2


# def process_pdf(filepath):
#     """Extract text from PDF file and keep page-wise data"""
#     pages_data = []
#     try:
#         with open(filepath, 'rb') as file:
#             pdf_reader = PyPDF2.PdfReader(file)
#             for i, page in enumerate(pdf_reader.pages, start=1):
#                 text = page.extract_text()
#                 if text and text.strip():
#                     pages_data.append({"page": i, "text": text.strip()})
#         chunks = semantic_split_pdf_text(pages_data)
#         return chunks
#     except Exception as e:
#         raise Exception(f"Failed to process PDF: {str(e)}")
    


# def semantic_split_pdf_text(pages_data):
#     """Split each PDF page semantically, preserving page metadata"""
    
#     embeddings = OllamaEmbeddings(model="nomic-embed-text")
#     splitter = SemanticChunker(
#         embeddings,
#         breakpoint_threshold_type="percentile",
#         breakpoint_threshold_amount=70  # adjust 60–80 as needed
#     )

#     chunks = []
#     for page in pages_data:
#         # Semantic splitting per page
#         semantic_chunks = splitter.split_text(page["text"])
#         for chunk in semantic_chunks:
#             chunks.append({
#                 "text": chunk,
#                 "page": page["page"]
#             })
#     return chunks


# print(process_pdf('uploads/pdf/24303.pdf')[4])

from ollama import chat

stream = chat(
  model='phi4-mini:3.8b',
  messages=[{'role': 'user', 'content': 'Give me a detailed explanation of the theory of relativity.'}],
  stream=True,
)

in_thinking = False
content = ''
thinking = ''
for chunk in stream:
  if chunk.message.thinking:
    if not in_thinking:
      in_thinking = True
      print('Thinking:\n', end='', flush=True)
    print(chunk.message.thinking, end='', flush=True)
    # accumulate the partial thinking 
    thinking += chunk.message.thinking
  elif chunk.message.content:
    if in_thinking:
      in_thinking = False
      print('\n\nAnswer:\n', end='', flush=True)
    print(chunk.message.content, end='', flush=True)
    # accumulate the partial content
    content += chunk.message.content

  # append the accumulated fields to the messages for the next request
  new_messages = [{ "role": 'assistant', "thinking": thinking, "content": content }]