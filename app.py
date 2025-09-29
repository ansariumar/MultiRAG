import os
import uuid
import threading
import re
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from werkzeug.utils import secure_filename
from utils.file_processor import process_pdf, extract_audio_from_video
from utils.whisper_transcribe import transcribe_audio, retrival
import ollama
from dotenv import load_dotenv
from google import genai

load_dotenv() 

client = genai.Client(api_key=os.getenv("GEMINI_API"))

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config.from_pyfile('config.py')

# Global variable to track processing status
processing_status = {}
chat_sessions = {}

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
            'is_processing': False
        }
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'Session expired'}), 400
    
    # Set processing status
    chat_sessions[session_id]['is_processing'] = True
    processing_status[session_id] = "Processing your file..."
    
    try:
        # Save the uploaded file
        if file.filename is None:
            chat_sessions[session_id]['is_processing'] = False
            return jsonify({'error': 'Invalid filename'}), 400
        
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        if file_extension == 'pdf':
            filepath = os.path.join(app.config['UPLOAD_FOLDER_PDF'], filename)
            file.save(filepath)
            
            # Process PDF in a separate thread
            thread = threading.Thread(
                target=process_pdf_file, 
                args=(session_id, filepath)
            )
            thread.start()
            
        elif file_extension in ['mp4', 'mov', 'avi', 'mkv']:
            filepath = os.path.join(app.config['UPLOAD_FOLDER_VIDEO'], filename)
            file.save(filepath)
            
            # Process video in a separate thread
            thread = threading.Thread(
                target=process_video_file, 
                args=(session_id, filepath)
            )
            thread.start()
            
        else:
            chat_sessions[session_id]['is_processing'] = False
            return jsonify({'error': 'Unsupported file type'}), 400
            
        return jsonify({'message': 'File uploaded successfully. Processing...'})
        
    except Exception as e:
        chat_sessions[session_id]['is_processing'] = False
        return jsonify({'error': str(e)}), 500

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
        
        # the extracted text is array of objects, each object having two elements "timestamp" and "text", eg [{timestamp:(), text:""}, {}...]
        # extracted_text:list = chat_sessions[session_id]['extracted_chunk']
        retrived_text = retrival(question)
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
        prompt = f"""
        You are a helpful RAG assistant. Answer the user's question using the provided extracted text as your primary source.

        Guidelines:
        - Prioritize information from the extracted text
        - Use conversation history for context when relevant  
        - Be honest when information is insufficient or missing
        - Provide clear, helpful responses in a conversational tone

        Previous conversation:
        {chat_history_str}

        Question: {question}

        Source material:
        {retrived_text}

        Answer:"""
        
        print("##################################################################")
        # print("The Chat history so far is: " + chat_history_str)
        print("##################################################################")
        
        # with open("transcript.txt", "w", encoding="utf-8") as f:
        #     f.write(str(extracted_text))
        # Get response from Ollama
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",  # or another model name
            contents=prompt
        )
        
        # response = ollama.chat(model='hf.co/unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_XL', messages=[
        #     {'role': 'user', 'content': prompt}
        # ], think=False)
        
        answer = response.text
        
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
            'content': f"Sorry, I encountered an error while processing your question: {str(e)}"
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