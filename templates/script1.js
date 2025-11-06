document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element Selections ---
    const fileInput = document.getElementById('file-input');
    const pickFile = document.getElementById('pick-file');
    const uploadForm = document.getElementById('upload-form');
    const currentFilename = document.getElementById('current-filename');
    const fileSizeEl = document.getElementById('file-size');
    const videoWrap = document.getElementById('video-wrap');
    const videoPlayer = document.getElementById('video-player');
    const chatMessages = document.getElementById('chat-messages');
    const questionForm = document.getElementById('question-form');
    const questionInput = document.getElementById('question-input');
    const statusText = document.getElementById('status-text');
    const statusDot = document.getElementById('status-dot');
    const typingIndicator = document.getElementById('typing-indicator');

    // UX Feature: Resizing elements
    const mainContainer = document.getElementById('main-container');
    const videoColumn = document.getElementById('video-column');
    const chatColumn = document.getElementById('chat-column');
    const resizer = document.getElementById('resizer');

    // UX Feature: Toggle buttons
    const toggleChatBtn = document.getElementById('toggle-chat-btn');
    const toggleVideoBtn = document.getElementById('toggle-video-btn');

    let uploadedFileURL = null;
    let selectedFile = null;


    // --- Helper Functions ---
    function timeStringToSeconds(str) {
        str = String(str).trim();
        const msMatch = str.match(/^(\d+)m(\d+)s$/i);
        if (msMatch) return parseInt(msMatch[1]) * 60 + parseInt(msMatch[2]);
        const sMatch = str.match(/^(\d+)s$/i);
        if (sMatch) return parseInt(sMatch[1]);

        const parts = str.split(':').map(p => parseInt(p, 10) || 0);
        if (parts.length === 2) return (parts[0] * 60) + parts[1];
        if (parts.length === 3) return (parts[0] * 3600) + (parts[1] * 60) + parts[2];
        return parts[0] || 0;
    }
    
    function flashNotice(msg) {
        const n = document.createElement('div');
        n.style.cssText = 'position:fixed;right:20px;bottom:20px;padding:12px 16px;background:#111;color:#fff;border-radius:10px;opacity:0.95;z-index:9999;font-size: .9rem;';
        n.textContent = msg;
        document.body.appendChild(n);
        setTimeout(() => { n.remove(); }, 2800);
    }

    // --- UX Feature: Column Resizing Logic ---
    function initResizer() {
        let isResizing = false;

        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            document.body.style.cursor = 'col-resize';
            mainContainer.style.userSelect = 'none';

            // Remove any focus mode classes
            mainContainer.classList.remove('chat-focused', 'video-focused');
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const containerRect = mainContainer.getBoundingClientRect();
            const mouseX = e.clientX - containerRect.left;
            
            // Calculate percentage, with min/max constraints (e.g., 20% to 80%)
            let videoWidth = (mouseX / containerRect.width) * 100;
            videoWidth = Math.max(20, Math.min(80, videoWidth));
            
            const chatWidth = 100 - videoWidth;

            videoColumn.style.flexBasis = `${videoWidth}%`;
            chatColumn.style.flexBasis = `${chatWidth}%`;
        });

        document.addEventListener('mouseup', () => {
            isResizing = false;
            document.body.style.cursor = 'default';
            mainContainer.style.userSelect = 'auto';
        });
    }

    // --- UX Feature: Focus Mode Toggle Logic ---
    function initToggles() {
        toggleChatBtn.addEventListener('click', () => {
            mainContainer.classList.toggle('chat-focused');
            mainContainer.classList.remove('video-focused');
        });

        toggleVideoBtn.addEventListener('click', () => {
            mainContainer.classList.toggle('video-focused');
            mainContainer.classList.remove('chat-focused');
        });
    }


    // --- File Handling and Uploads ---
    function initFileUpload() {
        pickFile.addEventListener('click', () => fileInput.click());
        document.getElementById('replace-btn').addEventListener('click', () => fileInput.click());
        
        fileInput.addEventListener('change', e => {
            const f = e.target.files && e.target.files[0];
            if (!f) return;

            selectedFile = f;
            currentFilename.textContent = f.name;
            fileSizeEl.textContent = `(${(f.size / 1024 / 1024).toFixed(2)} MB)`;
            document.getElementById('replace-btn').style.display = 'inline-block';

            if (f.type.startsWith('video/')) {
                if (uploadedFileURL) URL.revokeObjectURL(uploadedFileURL);
                uploadedFileURL = URL.createObjectURL(f);
                videoPlayer.src = uploadedFileURL;
                videoWrap.setAttribute('aria-hidden', 'false');
                document.getElementById('play-context').style.display = 'inline-block';
            } else {
                videoPlayer.removeAttribute('src');
                videoWrap.setAttribute('aria-hidden', 'true');
                document.getElementById('play-context').style.display = 'none';
            }
        });

        uploadForm.addEventListener('submit', evt => {
            evt.preventDefault();
            if (!selectedFile) return alert('Choose a file first');

            const formData = new FormData();
            formData.append('file', selectedFile);

            statusText.textContent = 'Uploading...';
            statusDot.style.background = '#f9c74f';

            fetch('/upload', { method: 'POST', body: formData })
                .then(r => r.json())
                .then(data => {
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    statusText.textContent = data.message || 'Uploaded';
                    statusDot.style.background = '#4cc9f0';
                })
                .catch(err => {
                    statusText.textContent = 'Upload failed';
                    statusDot.style.background = '#f94144';
                    console.error(err);
                    alert('Upload error: ' + err.message);
                });
        });
    }

    // --- Chat & Messaging Logic ---
    function renderMessage(role, content) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message ' + (role === 'user' ? 'user' : 'assistant');
        
        // Remove empty chat message if it exists
        const empty = chatMessages.querySelector('.empty-chat');
        if(empty) empty.remove();

        if (role === 'assistant') {
            const timestampRegex = /(?<!\()\b(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})\b/g;
            const preProcessed = content.replace(timestampRegex, match => `[${match}](timestamp:${match})`);
            wrapper.innerHTML = marked.parse(preProcessed);

            wrapper.querySelectorAll('a[href^="timestamp:"]').forEach(a => {
                a.classList.add('timestamp');
                a.setAttribute('role', 'button');
                a.addEventListener('click', ev => {
                    ev.preventDefault();
                    const t = a.getAttribute('href').replace('timestamp:', '');
                    const seconds = timeStringToSeconds(t);
                    if (videoPlayer && videoWrap.getAttribute('aria-hidden') !== 'true') {
                        videoPlayer.currentTime = seconds;
                        videoPlayer.play();
                        videoPlayer.focus();
                    } else {
                        flashNotice('Upload a video to use timestamps.');
                    }
                });
            });
        } else {
            wrapper.textContent = content;
        }

        const timeDiv = document.createElement('div');
        timeDiv.className = 'time';
        timeDiv.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        wrapper.appendChild(timeDiv);
        chatMessages.appendChild(wrapper);
    }

    function initChat() {
        questionForm.addEventListener('submit', e => {
            e.preventDefault();
            const q = questionInput.value.trim();
            if (!q) return;

            renderMessage('user', q);
            questionInput.value = '';
            chatMessages.scrollTop = chatMessages.scrollHeight;
            typingIndicator.style.display = 'block';

            fetch('/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: q })
            })
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    renderMessage('assistant', 'Error: ' + data.error);
                }
                if (data.answer) {
                    renderMessage('assistant', data.answer);
                }
            })
            .catch(err => {
                renderMessage('assistant', 'Error: ' + err);
            })
            .finally(() => {
                typingIndicator.style.display = 'none';
                chatMessages.scrollTop = chatMessages.scrollHeight;
            });
        });
    }

    // --- Initializations ---
    initResizer();
    initToggles();
    initFileUpload();
    initChat();
});