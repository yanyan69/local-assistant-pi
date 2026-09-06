# web_ui.py - Self-contained modern WebUI for your offline AI assistant

def get_chat_html():
    """Returns the complete HTML/JS string to render an Open WebUI-inspired interface."""
    return r"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Yanyan Bot - Local AI Interface</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            :root {
                --bg-main: #131316;
                --bg-sidebar: #1a1a1e;
                --bg-chat: #18181c;
                --bg-msg-user: #2b2b36;
                --bg-msg-bot: #212128;
                --bg-input: #23232a;
                --border-color: rgba(255, 255, 255, 0.08);
                --accent-color: #6366f1;
                --accent-hover: #4f46e5;
                --text-main: #ececef;
                --text-muted: #9e9ea7;
                --hw-badge: #f59e0b;
                --code-bg: #0d0d11;
                --code-header-bg: #16161d;
            }

            * { box-sizing: border-box; margin: 0; padding: 0; }
            
            body { 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background: var(--bg-main); 
                color: var(--text-main); 
                display: flex;
                height: 100vh;
                overflow: hidden;
            }

            /* Layout Architecture */
            .app-container { display: flex; width: 100%; height: 100vh; }
            
            /* Sidebar Navigation */
            .sidebar {
                width: 260px;
                background: var(--bg-sidebar);
                border-right: 1px solid var(--border-color);
                display: flex;
                flex-direction: column;
                padding: 16px;
                gap: 16px;
                flex-shrink: 0;
                transition: transform 0.3s ease;
            }

            .brand {
                display: flex;
                align-items: center;
                gap: 12px;
                padding-bottom: 12px;
                border-bottom: 1px solid var(--border-color);
            }

            .brand-avatar {
                width: 32px;
                height: 32px;
                background: var(--accent-color);
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 14px;
            }

            .brand-title h1 { font-size: 15px; font-weight: 600; }
            .brand-title .status { 
                font-size: 11px; 
                color: #10b981; 
                display: flex; 
                align-items: center; 
                gap: 4px; 
            }
            .status-dot { width: 6px; height: 6px; background: #10b981; border-radius: 50%; }

            .sidebar-btn {
                width: 100%;
                background: transparent;
                border: 1px solid var(--border-color);
                color: var(--text-main);
                padding: 10px 14px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 13px;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: background 0.2s;
            }

            .sidebar-btn:hover { background: rgba(255, 255, 255, 0.05); }

            .sidebar-spacer { flex: 1; }

            .system-info {
                font-size: 11px;
                color: var(--text-muted);
                line-height: 1.5;
                padding: 10px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 6px;
            }

            /* Main Workspace */
            .main-content {
                flex: 1;
                display: flex;
                flex-direction: column;
                background: var(--bg-chat);
                position: relative;
                min-width: 0;
            }

            /* Chat Stream Window */
            .chat-box {
                flex: 1;
                overflow-y: auto;
                padding: 24px 16px;
                display: flex;
                flex-direction: column;
                gap: 24px;
                scroll-behavior: smooth;
            }

            .chat-container {
                max-width: 800px;
                width: 100%;
                margin: 0 auto;
                display: flex;
                flex-direction: column;
                gap: 20px;
            }

            .msg-wrapper {
                display: flex;
                gap: 14px;
                width: 100%;
                max-width: 100%;
            }

            .msg-wrapper.user { flex-direction: row-reverse; }
            .msg-wrapper.bot { flex-direction: row; }

            .msg-avatar {
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: bold;
                flex-shrink: 0;
            }

            .user .msg-avatar { background: #3b82f6; }
            .bot .msg-avatar { background: var(--accent-color); }

            /* Text Adaptation & Wrappers */
            .msg-content {
                background: var(--bg-msg-bot);
                padding: 14px 18px;
                border-radius: 12px;
                border: 1px solid var(--border-color);
                line-height: 1.6;
                font-size: 14.5px;
                max-width: 85%;
                
                overflow-wrap: anywhere;
                word-break: break-word;
                hyphens: auto;
                min-width: 0;
            }

            .user .msg-content {
                background: var(--bg-msg-user);
                border-color: transparent;
                white-space: pre-wrap;
            }

            /* Markdown Content Styling */
            .msg-content p { margin-bottom: 0.8em; }
            .msg-content p:last-child { margin-bottom: 0; }
            .msg-content h1, .msg-content h2, .msg-content h3 { margin: 1em 0 0.4em 0; color: #fff; }
            .msg-content ul, .msg-content ol { margin: 0.5em 0 0.8em 1.5em; }
            .msg-content li { margin-bottom: 0.3em; }
            .msg-content blockquote {
                border-left: 3px solid var(--accent-color);
                padding-left: 10px;
                margin: 0.8em 0;
                color: var(--text-muted);
            }

            /* Hardware Command Action Badge */
            .hardware-tag {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: rgba(245, 158, 11, 0.15);
                border: 1px solid var(--hw-badge);
                color: var(--hw-badge);
                font-weight: 600;
                font-size: 11px;
                padding: 4px 8px;
                border-radius: 6px;
                margin-top: 10px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            /* Modern Code Blocks */
            .code-block-wrapper {
                background: var(--code-bg);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                margin: 12px 0;
                overflow: hidden;
            }

            .code-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: var(--code-header-bg);
                padding: 6px 12px;
                font-size: 11px;
                color: var(--text-muted);
                border-bottom: 1px solid var(--border-color);
                font-family: monospace;
            }

            pre {
                margin: 0;
                overflow-x: auto;
                padding: 12px 14px;
                white-space: pre;
            }

            code {
                font-family: "Fira Code", Consolas, Monaco, "Courier New", monospace;
                font-size: 13px;
                color: #e2e8f0;
            }

            p code, li code {
                display: inline;
                padding: 2px 6px;
                background: rgba(255, 255, 255, 0.08);
                border-radius: 4px;
                color: #f472b6;
                font-size: 0.9em;
                word-break: break-word;
            }

            .copy-btn {
                background: transparent;
                border: none;
                color: var(--text-muted);
                cursor: pointer;
                font-size: 11px;
                padding: 4px 8px;
                border-radius: 4px;
                display: flex;
                align-items: center;
                gap: 5px;
                transition: all 0.2s ease;
            }
            .copy-btn:hover { 
                color: #fff; 
                background: rgba(255, 255, 255, 0.08);
            }
            .copy-btn svg {
                width: 13px;
                height: 13px;
                fill: currentColor;
            }

            /* Input Workspace Controls */
            .input-container {
                padding: 16px;
                background: var(--bg-chat);
                border-top: 1px solid var(--border-color);
            }

            .input-box-wrapper {
                max-width: 800px;
                margin: 0 auto;
                width: 100%;
            }

            .input-box {
                display: flex;
                background: var(--bg-input);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 8px 12px;
                align-items: flex-end;
                gap: 8px;
                transition: border-color 0.2s;
            }

            .input-box:focus-within { border-color: var(--accent-color); }

            textarea {
                flex: 1;
                background: transparent;
                border: none;
                outline: none;
                color: #fff;
                font-size: 15px;
                font-family: inherit;
                padding: 6px 4px;
                resize: none;
                max-height: 180px;
                min-height: 24px;
                line-height: 1.4;
            }

            textarea::placeholder { color: var(--text-muted); }

            .send-btn {
                background: var(--accent-color);
                border: none;
                color: #fff;
                width: 34px;
                height: 34px;
                border-radius: 8px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s;
                flex-shrink: 0;
            }

            .send-btn:hover { background: var(--accent-hover); }
            .send-btn:disabled { background: var(--border-color); cursor: not-allowed; opacity: 0.5; }

            /* Typing Streaming Indicator */
            .cursor {
                display: inline-block;
                width: 7px;
                height: 14px;
                background: var(--accent-color);
                margin-left: 4px;
                vertical-align: middle;
                animation: blink 0.8s infinite;
            }
            @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

            @media (max-width: 768px) {
                .sidebar { display: none; }
                .msg-content { max-width: 90%; }
            }
        </style>
    </head>
    <body>
        <div class="app-container">
            <!-- Sidebar -->
            <div class="sidebar">
                <div class="brand">
                    <div class="brand-avatar">Y</div>
                    <div class="brand-title">
                        <h1>Yanyan Bot</h1>
                        <div class="status"><span class="status-dot"></span> Raspberry Pi 5</div>
                    </div>
                </div>

                <button class="sidebar-btn" onclick="resetChat()">
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                    New Chat
                </button>

                <div class="sidebar-spacer"></div>

                <div class="system-info">
                    <strong>Model Engine:</strong> Llama 3 (Local)<br>
                    <strong>Interface:</strong> Offline WebUI<br>
                    <strong>Execution Mode:</strong> Direct Hardware
                </div>
            </div>

            <!-- Main Chat Workspace -->
            <div class="main-content">
                <div class="chat-box" id="chatBox">
                    <div class="chat-container" id="chatContainer">
                        <div class="msg-wrapper bot">
                            <div class="msg-avatar">AI</div>
                            <div class="msg-content">
                                System initialized and running locally. How can I assist you with code, terminal commands, or hardware control?
                            </div>
                        </div>
                    </div>
                </div>

                <div class="input-container">
                    <div class="input-box-wrapper">
                        <div class="input-box">
                            <textarea id="userInput" rows="1" placeholder="Send a message or hardware command..." oninput="autoResize(this)" onkeydown="handleKeyDown(event)"></textarea>
                            <button class="send-btn" id="sendBtn" onclick="sendMsg()">
                                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M12 5l7 7-7 7"/></svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let chatHistory = [];
            let isGenerating = false;

            function autoResize(textarea) {
                textarea.style.height = 'auto';
                textarea.style.height = Math.min(textarea.scrollHeight, 180) + 'px';
            }

            function handleKeyDown(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMsg();
                }
            }

            async function sendMsg() {
                if (isGenerating) return;

                const inputEl = document.getElementById('userInput');
                const sendBtn = document.getElementById('sendBtn');
                const query = inputEl.value.trim();
                if (!query) return;

                appendMsg(query, 'user');
                inputEl.value = '';
                inputEl.style.height = 'auto';
                
                // Set UI state to busy
                isGenerating = true;
                inputEl.disabled = true;
                sendBtn.disabled = true;

                // Create empty bot placeholder element
                const { msgContentEl } = appendMsg('', 'bot');
                msgContentEl.innerHTML = '<span class="cursor"></span>';

                try {
                    const res = await fetch('/api/robot', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            query: query,
                            history: chatHistory
                        })
                    });

                    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

                    const reader = res.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';

                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n\n');
                        buffer = lines.pop(); 

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                const rawJson = line.replace('data: ', '').trim();
                                if (!rawJson) continue;

                                try {
                                    const parsed = JSON.parse(rawJson);
                                    
                                    if (parsed.history) {
                                        chatHistory = parsed.history;
                                    }

                                    updateBotMsg(msgContentEl, parsed.response, parsed.hardware_cmd || "NONE");
                                } catch (err) {
                                    console.error("JSON parse error:", err);
                                }
                            }
                        }
                    }

                } catch (e) {
                    console.error("Communication error:", e);
                    updateBotMsg(msgContentEl, "Error communicating with local AI backend.", "NONE");
                } finally {
                    isGenerating = false;
                    inputEl.disabled = false;
                    sendBtn.disabled = false;
                    inputEl.focus();
                }
            }

            function resetChat() {
                chatHistory = [];
                const box = document.getElementById('chatContainer');
                box.innerHTML = `
                    <div class="msg-wrapper bot">
                        <div class="msg-avatar">AI</div>
                        <div class="msg-content">Chat reset. Ready for new input!</div>
                    </div>`;
            }

            function parseMarkdown(text) {
                if (!text) return "";

                // 1. Escape basic HTML safely
                let safe = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

                // 2. Extract code blocks (handles unclosed streaming code blocks gracefully)
                const codeBlocks = [];
                safe = safe.replace(/```([a-zA-Z0-9_-]+)?\n([\s\S]*?)(?:\n```|$)/g, function(match, lang, codeContent) {
                    const id = 'code-' + Math.random().toString(36).substr(2, 9);
                    const language = lang || 'code';
                    
                    const blockHtml = `<div class="code-block-wrapper">
                        <div class="code-header">
                            <span>${language}</span>
                            <button class="copy-btn" onclick="copyCode('${id}', this)">
                                <svg viewBox="0 0 24 24"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                                <span>Copy code</span>
                            </button>
                        </div>
                        <pre><code id="${id}">${codeContent ? codeContent.trim() : ''}</code></pre>
                    </div>`;
                    
                    const placeholder = `__CODE_BLOCK_PLACEHOLDER_${codeBlocks.length}__`;
                    codeBlocks.push(blockHtml);
                    return placeholder;
                });

                // 3. Inline Code & Headers
                safe = safe.replace(/`([^`]+)`/g, '<code>$1</code>');
                safe = safe.replace(/^### (.*$)/gim, '<h3>$1</h3>');
                safe = safe.replace(/^## (.*$)/gim, '<h2>$1</h2>');
                safe = safe.replace(/^# (.*$)/gim, '<h1>$1</h1>');

                // 4. Bold, Italics & Blockquotes
                safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                safe = safe.replace(/\*(.*?)\*/g, '<em>$1</em>');
                safe = safe.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');

                // 5. Convert linebreaks outside code blocks
                safe = safe.replace(/\n/g, "<br>");

                // 6. Restore protected code blocks back into HTML
                codeBlocks.forEach((block, index) => {
                    safe = safe.replace(`__CODE_BLOCK_PLACEHOLDER_${index}__`, block);
                });

                return safe;
            }

            function copyCode(id, btn) {
                const codeEl = document.getElementById(id);
                if (!codeEl) return;
                
                const textToCopy = codeEl.textContent || codeEl.innerText;
                const label = btn.querySelector('span');

                const setSuccess = () => {
                    if (label) label.innerText = "Copied!";
                    setTimeout(() => {
                        if (label) label.innerText = "Copy code";
                    }, 2000);
                };

                if (navigator.clipboard && window.isSecureContext) {
                    navigator.clipboard.writeText(textToCopy)
                        .then(setSuccess)
                        .catch(() => fallbackCopy(textToCopy, setSuccess));
                } else {
                    fallbackCopy(textToCopy, setSuccess);
                }
            }

            function fallbackCopy(text, callback) {
                const textArea = document.createElement("textarea");
                textArea.value = text;
                textArea.style.position = "fixed";
                textArea.style.left = "-9999px";
                textArea.style.top = "-9999px";
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                
                try {
                    document.execCommand('copy');
                    callback();
                } catch (err) {
                    console.error('Fallback copy failed:', err);
                }
                document.body.removeChild(textArea);
            }

            function appendMsg(text, sender) {
                const container = document.getElementById('chatContainer');
                const chatBox = document.getElementById('chatBox');
                
                const wrapper = document.createElement('div');
                wrapper.className = `msg-wrapper ${sender}`;

                const avatar = document.createElement('div');
                avatar.className = 'msg-avatar';
                avatar.innerText = sender === 'user' ? 'YOU' : 'AI';

                const msgContent = document.createElement('div');
                msgContent.className = 'msg-content';
                
                if (sender === 'user') {
                    msgContent.innerText = text;
                } else {
                    msgContent.innerHTML = parseMarkdown(text);
                }

                wrapper.appendChild(avatar);
                wrapper.appendChild(msgContent);
                container.appendChild(wrapper);

                chatBox.scrollTop = chatBox.scrollHeight;
                return { wrapper, msgContentEl: msgContent };
            }

            function updateBotMsg(element, text, hwCmd = "NONE") {
                const chatBox = document.getElementById('chatBox');
                element.innerHTML = parseMarkdown(text);

                if (hwCmd !== "NONE") {
                    const tag = document.createElement('div');
                    tag.className = 'hardware-tag';
                    tag.innerHTML = `Action: <strong>${hwCmd}</strong>`;
                    element.appendChild(tag);
                }

                chatBox.scrollTop = chatBox.scrollHeight;
            }
        </script>
    </body>
    </html>
    """