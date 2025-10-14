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

response = ollama.chat(model='gpt-oss:20b-cloud', messages=[
            {'role': 'user', 'content': "Can you be a AGENT for my RAG application?"}
        ])
        
print(response['message']['content'])