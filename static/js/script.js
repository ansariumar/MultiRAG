function timeStringToSeconds(str) {
    // allow patterns like 1:23, 01:02:03, 00:05:12, 5m12s, 75s
    str = String(str).trim();
    // handle formats like 1m23s or 75s
    const msMatch = str.match(/^(\d+)m(\d+)s$/i);
    if (msMatch) return parseInt(msMatch[1]) * 60 + parseInt(msMatch[2]);
    const sMatch = str.match(/^(\d+)s$/i);
    if (sMatch) return parseInt(sMatch[1]);


    const parts = str.split(':').map(p => p.replace(/^0+/, '') || '0');
    if (parts.length === 1) return parseInt(parts[0]) || 0;
    if (parts.length === 2) return (parseInt(parts[0] || 0) * 60) + (parseInt(parts[1] || 0));
    if (parts.length === 3) return (parseInt(parts[0] || 0) * 3600) + (parseInt(parts[1] || 0) * 60) + (parseInt(parts[2] || 0));
    return 0;
}

function secondsToHms(sec) {
    sec = Math.max(0, Math.floor(sec));
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    if (h > 0) return [h, m, s].map(x => String(x).padStart(2, '0')).join(':');
    return [m, s].map(x => String(x).padStart(2, '0')).join(':');
}

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    const pickFile = document.getElementById('pick-file');
    const uploadForm = document.getElementById('upload-form');
    const uploadBtn = document.getElementById('upload-btn');
    const replaceBtn = document.getElementById('replace-btn');
    const currentFilename = document.getElementById('current-filename');
    const fileSizeEl = document.getElementById('file-size');
    const videoWrap = document.getElementById('video-wrap');
    const videoPlayer = document.getElementById('video-player');
    const chatMessages = document.getElementById('chat-messages');
    const questionForm = document.getElementById('question-form');
    const questionInput = document.getElementById('question-input');
    const playContextBtn = document.getElementById('play-context');
    const statusText = document.getElementById('status-text');
    const statusDot = document.getElementById('status-dot');

    let uploadedFileURL = null; // object URL for preview

    // When user clicks choose file
    pickFile.addEventListener('click', () => fileInput.click());
    replaceBtn.addEventListener('click', () => fileInput.click());

    // Show preview of local video if file chosen
    fileInput.addEventListener('change', e => {
        const f = e.target.files && e.target.files[0];
        if (!f) return;

        // show filename and size
        currentFilename.textContent = f.name;
        fileSizeEl.textContent = (f.size / 1024 / 1024).toFixed(2) + ' MB';

        // Show mini replace button
        replaceBtn.style.display = 'inline-block';

        // If it's a video, preview it immediately
        if (f.type.startsWith('video/')) {
            if (uploadedFileURL) URL.revokeObjectURL(uploadedFileURL);
            uploadedFileURL = URL.createObjectURL(f);
            videoPlayer.src = uploadedFileURL;
            videoWrap.setAttribute('aria-hidden', 'false');
            playContextBtn.style.display = 'inline-block';
            videoPlayer.style.display = 'block';
        } else {
            // Not a video — hide video player
            videoPlayer.removeAttribute('src');
            videoPlayer.load && videoPlayer.load();
            videoWrap.setAttribute('aria-hidden', 'true');
            playContextBtn.style.display = 'none';
        }

    });

    // Submit upload to server
    uploadForm.addEventListener('submit', evt => {
        evt.preventDefault();
        if (!fileInput.files.length) return alert('Choose a file first');

        const fd = new FormData();
        fd.append('file', fileInput.files[0]);

        statusText.textContent = 'Uploading...'; statusDot.style.background = '#f9c74f';
        fetch('/upload', { method: 'POST', body: fd })
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    statusText.textContent = 'Upload failed'; statusDot.style.background = '#f94144';
                    alert(data.error);
                    return;
                }
                statusText.textContent = data.message || 'Uploaded'; statusDot.style.background = '#4cc9f0';

                // minimize upload-bar to a small badge
                document.getElementById('upload-bar').innerHTML = `<small>Uploaded: ${fileInput.files[0].name}</small><button id=\"replace-btn-mini\" class=\"btn-mini\">Replace</button>`;
                document.getElementById('replace-btn-mini').addEventListener('click', () => fileInput.click());

                // Start polling messages, etc. (reuse existing fetchMessages if server supports)
                fetchMessages();
            })
            .catch(err => { statusText.textContent = 'Upload error'; statusDot.style.background = '#f94144'; console.error(err); alert('Upload error: ' + err) });
    });

    // Fetch messages and render (polling style from your original)
    let previousMessageCount = 0;
    let userScrolledUp = false;

    chatMessages.addEventListener('scroll', () => {
        const isAtBottom = chatMessages.scrollHeight - chatMessages.scrollTop === chatMessages.clientHeight;
        userScrolledUp = !isAtBottom;
    });

    function fetchMessages() {
        fetch('/messages')
            .then(r => r.json())
            .then(data => {
                if (data.error) return console.error(data.error);
                const msgs = data.messages || [];
                if (msgs.length === 0) { chatMessages.innerHTML = '<div class="empty">No messages yet. Ask questions after upload.</div>'; previousMessageCount = 0; return; }

                if (msgs.length !== previousMessageCount) {
                    const oldScrollHeight = chatMessages.scrollHeight; const oldScrollTop = chatMessages.scrollTop;
                    chatMessages.innerHTML = '';
                    msgs.forEach(m => renderMessage(m.role, m.content));
                    if (!userScrolledUp) chatMessages.scrollTop = chatMessages.scrollHeight; else chatMessages.scrollTop = oldScrollTop + (chatMessages.scrollHeight - oldScrollHeight);
                    previousMessageCount = msgs.length;
                }
            })
            .catch(err => console.error('fetchMessages', err));
    }

    // Render a single message — assistant messages are treated as markdown with timestamp linking
    function renderMessage(role, content) {
        // Create container
        const wrapper = document.createElement('div'); wrapper.className = 'message ' + (role === 'user' ? 'user' : 'assistant');

        if (role === 'assistant') {
            // 1) Convert timestamp-like tokens into markdown-style timestamp links: [00:05:12](timestamp:00:05:12)
            // Regex captures HH:MM:SS or MM:SS or M:SS
            const timestampRegex = /(?<!\()\b(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})\b/g;
            const preProcessed = content.replace(timestampRegex, function (match) { return `[${match}](timestamp:${match})`; });

            // 2) Use marked to parse the (possibly) markdown response
            const html = marked.parse(preProcessed);
            wrapper.innerHTML = html;

            // 3) Find any anchor with href starting with "timestamp:" and convert to actionable links
            wrapper.querySelectorAll('a').forEach(a => {
                const href = a.getAttribute('href') || '';
                if (href.startsWith('timestamp:')) {
                    a.classList.add('timestamp');
                    a.setAttribute('role', 'button');
                    a.addEventListener('click', function (ev) {
                        ev.preventDefault(); const t = href.replace('timestamp:', ''); const seconds = timeStringToSeconds(t); if (videoPlayer.src && !videoWrap.getAttribute('aria-hidden')) { videoPlayer.currentTime = seconds; videoPlayer.play(); videoPlayer.focus(); } else { // no video: show a small hint
                            flashNotice('No video loaded. Upload a video to use timestamps.');
                        }
                    });
                }
            });

        } else {
            // user message — just text
            wrapper.textContent = content;
        }

        // time
        const timeDiv = document.createElement('div'); timeDiv.className = 'time'; timeDiv.textContent = new Date().toLocaleTimeString();
        wrapper.appendChild(timeDiv);
        chatMessages.appendChild(wrapper);
    }

    // Small toast-like notice in the chat area
    let noticeTimeout = null;
    function flashNotice(msg) {
        const n = document.createElement('div'); n.style.cssText = 'position:fixed;right:20px;bottom:20px;padding:10px 14px;background:#111;color:#fff;border-radius:10px;opacity:0.95;z-index:9999'; n.textContent = msg; document.body.appendChild(n);
        clearTimeout(noticeTimeout); noticeTimeout = setTimeout(() => { n.remove(); }, 2600);
    }

    // handle ask question
    questionForm.addEventListener('submit', e => {
        e.preventDefault(); const q = questionInput.value && questionInput.value.trim(); if (!q) return;
        renderMessage('user', q); questionInput.value = ''; chatMessages.scrollTop = chatMessages.scrollHeight;
        // show typing indicator
        const typing = document.createElement('div'); typing.className = 'message'; typing.textContent = 'Assistant is typing...'; chatMessages.appendChild(typing); chatMessages.scrollTop = chatMessages.scrollHeight;

        fetch('/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q }) })
            .then(r => r.json())
            .then(data => {
                typing.remove(); if (data.error) { renderMessage('assistant', 'Error: ' + data.error); return; }
                // backend will likely start processing; we will start polling for messages
                fetchMessages();
            })
            .catch(err => { typing.remove(); renderMessage('assistant', 'Error: ' + err); });
    });

    // Periodically poll status (like your original script)
    setInterval(() => { fetch('/status').then(r => r.json()).then(s => { if (s && s.status) { statusText.textContent = s.status; statusDot.style.background = s.is_processing ? '#f9c74f' : '#4cc9f0' } }).catch(() => { }); }, 8000);

    // initial fetch
    fetchMessages();

    // Play from first timestamp button: find first timestamp in messages and seek
    playContextBtn.addEventListener('click', () => {
        // find first anchor.timestamp in chat
        const first = document.querySelector('#chat-messages a.timestamp');
        if (first) { const href = first.getAttribute('href'); const t = href.replace('timestamp:', ''); const sec = timeStringToSeconds(t); videoPlayer.currentTime = sec; videoPlayer.play(); } else flashNotice('No timestamp found in chat.');
    });

});