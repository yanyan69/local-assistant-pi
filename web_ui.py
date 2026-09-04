# web_ui.py - Self-contained HTML component module for your offline AI assistant

def get_chat_html():
    """Returns the complete HTML/JS string to render the dashboard interface."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Offline AI Core Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
            .chat-container { max-width: 700px; margin: 0 auto; display: flex; flex-direction: column; height: 92vh; }
            .header-panel { text-align: center; margin-bottom: 10px; border-bottom: 1px solid #2d2d2d; padding-bottom: 10px; }
            h2 { color: #1e88e5; margin: 0 0 5px 0; font-size: 24px; }
            .system-status { font-size: 12px; color: #4caf50; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
            .chat-box { flex: 1; border: 1px solid #2d2d2d; border-radius: 8px; background: #1e1e1e; padding: 20px; overflow-y: auto; margin-bottom: 15px; box-shadow: inset 0 2px 10px rgba(0,0,0,0.5); display: flex; flex-direction: column; }

            .msg { margin-bottom: 15px; padding: 12px 16px; border-radius: 8px; max-width: 85%; line-height: 1.5; font-size: 15px; word-wrap: break-word; }
            .user { background: #2a2a2a; color: #ffffff; align-self: flex-end; margin-left: auto; border-bottom-right-radius: 1px; white-space: pre-wrap; }
            .bot { background: #0d47a1; color: #ffffff; align-self: flex-start; margin-right: auto; border-bottom-left-radius: 1px; }
            .hardware-tag { display: inline-block; background: #ff9800; color: #000; font-weight: bold; font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-top: 8px; text-transform: uppercase; }
            .input-area { display: flex; gap: 10px; background: #1a1a1a; padding: 5px; border-radius: 8px; }
            input { flex: 1; padding: 14px; border: 1px solid #333; border-radius: 6px; background: #252525; color: #fff; font-size: 16px; outline: none; transition: border 0.2s; }
            input:focus { border-color: #1e88e5; }
            button { padding: 14px 28px; border: none; background: #1e88e5; color: white; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; transition: background 0.2s; }
            button:hover { background: #1565c0; }

            pre { background: #2d2d2d; padding: 14px; border-radius: 6px; overflow-x: auto; border: 1px solid #444; margin: 10px 0; }
            code { font-family: 'Courier New', Courier, monospace; color: #f8f8f2; font-size: 14px; white-space: pre; }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="header-panel">
                <h2>Offline Yanyan Bot</h2>
                <div class="system-status">● LAN Server Active</div>
            </div>
            <div class="chat-box" id="chatBox">
                <div class="msg bot">hi haha...</div>
            </div>
            <div class="input-area">
                <input type="text" id="userInput" placeholder="ask me anything..." onkeypress="if(event.key==='Enter') sendMsg()">
                <button onclick="sendMsg()">Send</button>
            </div>
        </div>

        <script>
            let chatHistory = [];

            async function sendMsg() {
                const inputEl = document.getElementById('userInput');
                const query = inputEl.value.trim();
                if (!query) return;

                appendMsg(query, 'user');
                inputEl.value = '';

                try {
                    const res = await fetch('/api/robot', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            query: query,
                            history: chatHistory // Handshake history state up to Flask
                        })
                    });
                    const data = await res.json();
                    
                    // Sync our local state with the memory array returned by the backend
                    chatHistory = data.history || [];
                    
                    let botReply = data.response;
                    let hwCmd = data.hardware_cmd;
                    
                    appendMsg(botReply, 'bot', hwCmd);
                } catch (e) {
                    appendMsg("Error communicating with the local AI background process.", 'bot', "NONE");
                }
            }

            function parseMarkdownCodeBlocks(text) {
                // Safely escape basic HTML tags to prevent execution injection
                let safeText = text
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;");

                // Regex pattern to catch standard triple backtick blocks (```lang ... ```)
                const codeBlockRegex = /```(?:[a-zA-Z0-9_-]+)?\\n([\s\S]*?)\\n```/g;
                
                // Replace text blocks with styled pre/code blocks
                safeText = safeText.replace(codeBlockRegex, function(match, codeContent) {
                    return `<pre><code>${codeContent.trim()}</code></pre>`;
                });

                // Inline code snippet fallback (single `backtick`)
                safeText = safeText.replace(/`([^`]+)`/g, '<code style="background:#2d2d2d; padding:2px 5px; border-radius:4px;">$1</code>');

                // Convert natural newlines to HTML breaks outside of pre blocks
                return safeText.replace(/\\n/g, "<br>");
            }

            function appendMsg(text, sender, hwCmd = "NONE") {
                const box = document.getElementById('chatBox');
                const div = document.createElement('div');
                div.className = `msg ${sender}`;
                
                if (sender === 'bot') {
                    // Process markdown and write directly to innerHTML for structural element rendering
                    div.innerHTML = parseMarkdownCodeBlocks(text);
                    
                    // If the server pushed a physical hardware flag, render a tag visualizer
                    if (hwCmd !== "NONE") {
                        const tag = document.createElement('div');
                        tag.className = 'hardware-tag';
                        tag.innerText = `Action: ${hwCmd}`;
                        div.appendChild(tag);
                    }
                } else {
                    div.innerText = text;
                }
                
                box.appendChild(div);
                box.scrollTop = box.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
