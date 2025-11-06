import os
import uuid
import threading
import re
from flask import Flask, render_template, request, jsonify, session, send_from_directory, Response, stream_with_context
from werkzeug.utils import secure_filename
from utils.file_processor import process_pdf, extract_audio_from_video, retriverPDF
from utils.whisper_transcribe import transcribe_audio, retriverVideo
import ollama
from dotenv import load_dotenv
from google import genai
import requests
import json
from queue import Queue

load_dotenv() 

client = genai.Client(api_key=os.getenv("GEMINI_API"))

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config.from_pyfile('config.py')

# Global variable to track processing status
processing_status = {}
chat_sessions = {}
Global_fileType = None

def format_chat_history(messages, max_pairs=2):
    """
    Format chat history for inclusion in prompts.
    Returns the last max_pairs Q&A pairs as a formatted string.
    """
    if not messages:
        return ""
    
    # Take last max_pairs*2 messages (each Q&A pair consists of 2 messages)
    max_messages = max_pairs * 2
    recent_messages = messages[-max_messages:] if len(messages) >= max_messages else messages
    
    chat_history_str = ""
    for i in range(0, len(recent_messages), 2):
        if i + 1 < len(recent_messages):
            user_msg = recent_messages[i]['content']
            assistant_msg = recent_messages[i + 1]['content']
            # Remove HTML tags and markdown formatting from assistant message for cleaner history
            clean_assistant_msg = re.sub(r'<[^>]+>', '', assistant_msg)  # Remove HTML tags
            clean_assistant_msg = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_assistant_msg)  # Remove bold markdown
            clean_assistant_msg = re.sub(r'\*(.*?)\*', r'\1', clean_assistant_msg)  # Remove italic markdown
            clean_assistant_msg = re.sub(r'`([^`]+)`', r'\1', clean_assistant_msg)  # Remove inline code markdown
            clean_assistant_msg = re.sub(r'```[\s\S]*?```', '', clean_assistant_msg)  # Remove code blocks
            clean_assistant_msg = re.sub(r'^#+\s*', '', clean_assistant_msg, flags=re.MULTILINE)  # Remove headers
            clean_assistant_msg = re.sub(r'\n\s*\n', '\n', clean_assistant_msg).strip()  # Clean up extra newlines
            chat_history_str += f"User: {user_msg}\nAssistant: {clean_assistant_msg}\n\n"
    
    return chat_history_str

@app.route('/')
def index():
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    if session_id not in chat_sessions:
        chat_sessions[session_id] = {
            'messages': [],
            'extracted_text': '',
            'is_processing': False,
            'listeners': []  # SSE listener queues
        }
    return render_template('index.html')

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if 'file' not in request.files:
#         return jsonify({'error': 'No file provided'}), 400
    
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'error': 'No file selected'}), 400
    
#     session_id = session.get('session_id')
#     if not session_id:
#         return jsonify({'error': 'Session expired'}), 400
    
#     # Set processing status
#     chat_sessions[session_id]['is_processing'] = True
#     processing_status[session_id] = "Processing your file..."
    
#     try:
#         # Save the uploaded file
#         if file.filename is None:
#             chat_sessions[session_id]['is_processing'] = False
#             return jsonify({'error': 'Invalid filename'}), 400
        
#         filename = secure_filename(file.filename)
#         file_extension = filename.rsplit('.', 1)[1].lower()
        
#         if file_extension == 'pdf':
#             filepath = os.path.join(app.config['UPLOAD_FOLDER_PDF'], filename)
#             file.save(filepath)
            
#             # Process PDF in a separate thread
#             thread = threading.Thread(
#                 target=process_pdf_file, 
#                 args=(session_id, filepath)
#             )
#             thread.start()
            
#         elif file_extension in ['mp4', 'mov', 'avi', 'mkv']:
#             filepath = os.path.join(app.config['UPLOAD_FOLDER_VIDEO'], filename)
#             file.save(filepath)
            
#             # Process video in a separate thread
#             thread = threading.Thread(
#                 target=process_video_file, 
#                 args=(session_id, filepath)
#             )
#             thread.start()
            
#         else:
#             chat_sessions[session_id]['is_processing'] = False
#             return jsonify({'error': 'Unsupported file type'}), 400
            
#         return jsonify({'message': 'File uploaded successfully. Processing...'})
        
#     except Exception as e:
#         chat_sessions[session_id]['is_processing'] = False
#         return jsonify({'error': str(e)}), 500


@app.route('/test', methods=['GET'])
def test_endpoint():
    return jsonify({'status': 'ok'})

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Get the filename from the request body
        filename = request.data.decode('utf-8')
        if not filename:
            return jsonify({'error': 'No filename provided'}), 400

        # Ensure the filename is secure
        filename = secure_filename(filename)
        if '.' not in filename:
            return jsonify({'error': 'Invalid filename. File must have an extension.'}), 400

        # Determine the file path based on the extension
        file_extension = filename.rsplit('.', 1)[1].lower()
        print("file_extension", file_extension)
        if file_extension == 'pdf':
            Global_fileType = 'pdf'
            print("Global_fileType", Global_fileType)
            filepath = os.path.join('./uploads/pdf', filename)
        elif file_extension in ['mp4', 'mov', 'avi', 'mkv']:
            Global_fileType = 'video'
            filepath = os.path.join('./uploads/video', filename)
        elif file_extension in ['jpg', 'jpeg', 'png', 'webp']:
            Global_fileType = 'image'
            filepath = os.path.join('./uploads/image', filename)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400

        # print("new file type is", Global_fileType)

        chat_sessions[session.get('session_id')]['file_type'] = Global_fileType
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Simulate saving the file path (no actual file content is saved)
        # Start a thread for processing based on file type
        if file_extension == 'pdf':
            threading.Thread(target=process_pdf_file, args=(session.get('session_id'), filepath)).start()
        elif file_extension in ['mp4', 'mov', 'avi', 'mkv']:
            threading.Thread(target=process_video_file, args=(session.get('session_id'), filepath)).start()

        return jsonify({'message': f'Filename "{filename}" processed successfully.', 'path': filepath})

    except Exception as e:
        return jsonify({'error': f'Failed to process filename: {str(e.__traceback__)}'}), 500


def process_pdf_file(session_id, filepath):
    try:
        extracted_text = process_pdf(filepath)
        chat_sessions[session_id]['extracted_text'] = extracted_text
        processing_status[session_id] = "File processed successfully. You can now ask questions."
    except Exception as e:
        processing_status[session_id] = f"Error processing PDF: {str(e)}"
    finally:
        chat_sessions[session_id]['is_processing'] = False

def process_video_file(session_id, filepath):
    try:
        # Extract audio from video
        audio_path = extract_audio_from_video(
            filepath, 
            app.config['UPLOAD_FOLDER_TEMP']
        )
        
        # Transcribe audio with timestamps
        # transcription_result:dict = transcribe_audio(audio_path)
        transcribe_audio(audio_path)
        
        # Store both the full text and the segments with timestamps
        # extracted_text = transcription_result["chunks"]
        # segments = transcription_result.get("segments", [])
        
        # chat_sessions[session_id]['extracted_chunk'] = extracted_text
        # chat_sessions[session_id]['segments'] = segments  # Store segments with timestamps
        
        processing_status[session_id] = "File processed successfully. You can now ask questions."
        
        # Clean up temporary audio file
        os.remove(audio_path)
        
    except Exception as e:
        processing_status[session_id] = f"Error processing video: {str(e)}"
    finally:
        chat_sessions[session_id]['is_processing'] = False

@app.route('/ask', methods=['POST'])
def ask_question():
    session_id = session.get('session_id')
    if not session_id or session_id not in chat_sessions:
        return jsonify({'error': 'Session expired'}), 400
    
    if chat_sessions[session_id]['is_processing']:
        return jsonify({'error': 'System is still processing your file'}), 400
    
    data = request.get_json()
    question = data.get('question', '')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    # if not chat_sessions[session_id]['extracted_chunk']:
    #     return jsonify({'error': 'No document content available. Please upload a file first.'}), 400
    
    # Add user question to chat history
    chat_sessions[session_id]['messages'].append({
        'role': 'user',
        'content': question
    })
    
    # Set processing status
    chat_sessions[session_id]['is_processing'] = True
    processing_status[session_id] = "Generating answer..."
    
    # Process question in a separate thread
    thread = threading.Thread(
        target=generate_answer, 
        args=(session_id, question)
    )
    thread.start()
    
    return jsonify({'message': 'Question received. Processing...'})


def generate_answer(session_id, question):
    try:
        Global_fileType = chat_sessions[session_id]['file_type']
        print("here generate_answer", Global_fileType)
        # the extracted text is array of objects, each object having two elements "timestamp" and "text", eg [{timestamp:(), text:""}, {}...]
        # extracted_text:list = chat_sessions[session_id]['extracted_chunk']
        if Global_fileType == 'video':
            print("here video", Global_fileType)
            retrived_text = retriverVideo(question)
        elif Global_fileType == 'pdf':
            print("here pdf", Global_fileType)
            retrived_text = retriverPDF(question)
        print(chat_sessions)
        
        
        
        # print("##################################################################")
        print(f"\033[92mThe Retrieved thext is   :  {retrived_text} \033[0m")
        # print("##################################################################")
        
        # Get chat history (excluding the current question which was just added)
        messages = chat_sessions[session_id]['messages'][:-1]  # Exclude the current question
        
        # Format chat history using helper function
        chat_history_str = format_chat_history(messages, max_pairs=2)

        print("Transcript saved to transcript.txt")
        
        # Prepare prompt for the AI model with chat history
        if Global_fileType == 'video':
            prompt = f"""
        You are a friendly, expert educational assistant. Your primary goal is to help the user learn and understand the subject matter. You have been given a Video Transcript and a Image. Use the transcript.

        Guidelines:
        - Read and properly analyse the `USER'S QUESTION`.
        - Prioritize Extracted Context: Your answer MUST be based on the provided `EXTRACTED TEXT` and `CONVERSATION HISTORY`. If the context contains a direct answer, use it and cite the source if possible.
        - The timestamps are in the format (start_time, end_time) in seconds, convert it to proper hh:mm:ss format if asked
        - Go Beyond for Clarity: If the user asks for a simplification ("explain in easy English," "give an example") or asks a related general knowledge question that is not fully covered in the provided context, you may use your general knowledge to provide a helpful, simple, and complete answer.  
        - Be honest when information is insufficient or missing
        - Provide clear, helpful responses in a conversational tone

        CONVERSATION HISTORY:
        {chat_history_str}

        USER'S QUESTION: {question}

        EXTRACTED TEXT:
        {retrived_text}

        Answer:"""

        elif Global_fileType == 'pdf':
            prompt = f"""
            You are a friendly, expert educational assistant. Your primary goal is to help the user learn and understand the subject matter. You have been given a PDF's Text . Use the PDF to answer the question.

            Guidelines:
            - Read and properly analyse the `USER'S QUESTION`.
            - Prioritize Extracted Context: Your answer MUST be based on the provided `EXTRACTED TEXT` and `CONVERSATION HISTORY`. If the context contains a direct answer, use it and cite the page numbers if possible(small unassuming page numbers).
            - Go Beyond for Clarity: If the user asks for a simplification ("explain in easy English," "give an example") or asks a related general knowledge question that is not fully covered in the provided context, you may use your general knowledge to provide a helpful, simple, and complete answer.  
            - Be honest when information is insufficient or missing
            - Provide clear, helpful responses in a conversational tone

            CONVERSATION HISTORY:
            {chat_history_str}

            USER'S QUESTION: {question}
            EXTRACTED TEXT:
            {retrived_text}

            Answer:"""
        
        else:
            processing_status[session_id] = "Error: Unsupported file type"
            return jsonify({'error': 'Unsupported file type'}), 400

        print("##################################################################")
        # print("The Chat history so far is: " + chat_history_str)
        print("##################################################################")
        
        # with open("transcript.txt", "w", encoding="utf-8") as f:
        #     f.write(str(extracted_text))
        # Get response from Ollama
        
        #---------------------- For Local Ollama model (streaming)
        def broadcast_to_listeners(payload: dict):
            listeners = chat_sessions.get(session_id, {}).get('listeners', [])
            if not listeners:
                return
            data = json.dumps(payload, ensure_ascii=False)
            for q in list(listeners):
                try:
                    q.put_nowait(data)
                except Exception:
                    # best-effort; drop if full
                    pass

        accumulated_thinking = ''
        accumulated_content = ''

        stream = ollama.chat(
            model='gpt-oss:20b-cloud',
            messages=[{'role': 'user', 'content': prompt}],
            stream=True,
            think='low',
        )

        in_thinking = False
        for chunk in stream:
            # The python client exposes chunk.message.thinking/content
            thinking_part = getattr(chunk.message, 'thinking', None)
            content_part = getattr(chunk.message, 'content', None)

            if thinking_part:
                in_thinking = True
                accumulated_thinking += thinking_part
                broadcast_to_listeners({'type': 'thinking', 'delta': thinking_part})
            elif content_part:
                if in_thinking:
                    in_thinking = False
                accumulated_content += content_part
                broadcast_to_listeners({'type': 'delta', 'delta': content_part})

        answer = accumulated_content
        broadcast_to_listeners({'type': 'done'})
        # -------------------------------------------
        
        #---------------------- For Google Gemini model
        # response = client.models.generate_content(
        #     model="gemini-2.5-flash",  # or another model name
        #     contents=prompt
        # )
        # answer = response.text
        # -------------------------------------------
        
        
        #---------------------- For Remote Ollama model
        # OLLAMA_SERVER = "http://10.51.122.75:11434"
        # url = f"{OLLAMA_SERVER}/api/generate"
        
        # response = requests.post(
        #     url, 
        #     json={
        #         "model": "gpt-oss:20b",
        #         "prompt": prompt,
        #         "stream": False
        # })
        
        # data = response.json()
        # think_answer = f"{data['thinking']} /n /n {data['response']}"
        # answer = think_answer
        # -------------------------------------------
        
        
        
        # Add AI response to chat history
        chat_sessions[session_id]['messages'].append({
            'role': 'assistant',
            'content': answer
        })
        
        processing_status[session_id] = "Answer generated successfully."
        
    except Exception as e:
        processing_status[session_id] = f"Error generating answer: {str(e)}"
        
        # Add error message to chat history
        chat_sessions[session_id]['messages'].append({
            'role': 'assistant',
            'content': f"Sorry, I encountered an error while processing your question: {str(e)} \n Err"
        })
        
    finally:
        chat_sessions[session_id]['is_processing'] = False

@app.route('/status')
def get_status():
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'Session expired'}), 400
    
    status = processing_status.get(session_id, 'Ready')
    is_processing = chat_sessions.get(session_id, {}).get('is_processing', False)
    
    return jsonify({
        'status': status,
        'is_processing': is_processing
    })

@app.route('/messages')
def get_messages():
    session_id = session.get('session_id')
    if not session_id or session_id not in chat_sessions:
        return jsonify({'error': 'Session expired'}), 400

    # If stream=1, return Server-Sent Events stream of assistant deltas
    if request.args.get('stream') == '1':
        client_queue = Queue(maxsize=1024)
        chat_sessions[session_id]['listeners'].append(client_queue)

        def event_stream():
            try:
                # send a hello event so client can attach
                yield f"data: {json.dumps({'type': 'ready'})}\n\n"
                while True:
                    data = client_queue.get()
                    yield f"data: {data}\n\n"
            except GeneratorExit:
                pass
            finally:
                # cleanup listener
                try:
                    chat_sessions[session_id]['listeners'].remove(client_queue)
                except ValueError:
                    pass

        return Response(stream_with_context(event_stream()), mimetype='text/event-stream')

    # Default: return the whole messages history (non-streaming)
    return jsonify({
        'messages': chat_sessions[session_id]['messages']
    })

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    """Clear chat history for the current session"""
    session_id = session.get('session_id')
    if not session_id or session_id not in chat_sessions:
        return jsonify({'error': 'Session expired'}), 400
    
    # Clear only the messages, keep extracted content
    chat_sessions[session_id]['messages'] = []
    
    return jsonify({'message': 'Chat history cleared successfully'})

if __name__ == '__main__':
    # Create upload directories if they don't exist
    os.makedirs(app.config['UPLOAD_FOLDER_PDF'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_VIDEO'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_TEMP'], exist_ok=True)
    
    app.run(debug=True)