let conversationId = null;
let chatHistory = [];
let isGenerating = false;
let mediaRecorder = null;
let voiceChunks = [];
let personaAvatar = '';
let conversationLoadSequence = 0;

const byId = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderMarkdown(text) {
  let safe = escapeHtml(text);
  const codeBlocks = [];

  safe = safe.replace(/```([\w+-]*)\n?([\s\S]*?)(?:```|$)/g, (_match, language, code) => {
    const index = codeBlocks.length;
    codeBlocks.push('<div class="code-block-wrap"><button class="copy-code-button" type="button" aria-label="Copy code" title="Copy code">⧉</button><pre class="code-block"><code>' + code.trim() + '</code></pre></div>');
    return `@@CODE_BLOCK_${index}@@`;
  });

  safe = safe
    .replace(/^### (.*)$/gim, '<h3>$1</h3>')
    .replace(/^## (.*)$/gim, '<h2>$1</h2>')
    .replace(/^# (.*)$/gim, '<h1>$1</h1>')
    .replace(/`([^`\n]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>');

  safe = safe.replace(/(?:^|\n)((?:[-*] .+(?:\n|$))+)/g, (_match, list) => {
    const items = list.trim().split('\n').map((line) => `<li>${line.slice(2)}</li>`).join('');
    return `\n<ul>${items}</ul>\n`;
  });

  safe = safe.replace(/(?:^|\n)((?:\d+\. .+(?:\n|$))+)/g, (_match, list) => {
    const items = list.trim().split('\n').map((line) => `<li>${line.replace(/^\d+\. /, '')}</li>`).join('');
    return `\n<ol>${items}</ol>\n`;
  });

  safe = safe.replace(/\n/g, '<br>');
  codeBlocks.forEach((block, index) => {
    safe = safe.replace(`@@CODE_BLOCK_${index}@@`, block);
  });
  return safe;
}

function setMessageContent(element, text, streaming = false) {
  element.dataset.text = text || '';
  element.innerHTML = renderMarkdown(text) + (streaming ? '<span class="cursor"></span>' : '');
  element.querySelectorAll('.copy-code-button').forEach((button) => {
    button.onclick = async () => {
      const code = button.parentElement.querySelector('code')?.textContent || '';
      try {
        await navigator.clipboard.writeText(code);
        button.textContent = '✓';
        button.title = 'Copied';
        setTimeout(() => {
          button.textContent = '⧉';
          button.title = 'Copy code';
        }, 1200);
      } catch (error) {
        button.title = 'Copy failed';
      }
    };
  });
}

function autoResize() {
  const input = byId('userInput');
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
}

function appendMessage(text, role) {
  const wrapper = document.createElement('div');
  wrapper.className = `message ${role}`;
  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  if (role === 'user' || !personaAvatar) {
    avatar.textContent = role === 'user' ? 'U' : (byId('headerPersonaName').textContent || 'AI').slice(0, 2).toUpperCase();
  } else {
    const image = document.createElement('img');
    image.src = personaAvatar;
    image.alt = '';
    avatar.appendChild(image);
  }
  const body = document.createElement('div');
  body.className = 'message-body';
  if (role === 'user') body.textContent = text;
  else setMessageContent(body, text);
  if (role === 'user') wrapper.append(body, avatar);
  else wrapper.append(avatar, body);
  byId('chatContainer').appendChild(wrapper);
  byId('chatBox').scrollTop = byId('chatBox').scrollHeight;
  return body;
}

function renderConversation(conversation) {
  conversationId = conversation.id;
  chatHistory = [];
  byId('chatContainer').replaceChildren();
  let pendingPair = null;
  (conversation.messages || []).forEach((message) => {
    appendMessage(message.content, message.role === 'user' ? 'user' : 'bot');
    if (message.role === 'user') {
      pendingPair = [message.content, ''];
      chatHistory.push(pendingPair);
    } else if (pendingPair) {
      pendingPair[1] = message.content;
    }
  });
  if (!conversation.messages?.length) {
    appendMessage('System initialized and running locally. Ask for code, Linux help, or hardware control.', 'bot');
  }
  chatHistory = chatHistory.filter((pair) => pair[0] && pair[1]).slice(-3);
}

function renderConversationList(conversations) {
  const list = byId('conversationList');
  list.replaceChildren();
  conversations.forEach((conversation) => {
    const item = document.createElement('div');
    item.className = `conversation-item${conversation.id === conversationId ? ' active' : ''}`;
    const button = document.createElement('button');
    button.className = 'conversation-title';
    button.textContent = conversation.title || 'New chat';
    button.type = 'button';
    button.onclick = () => openConversation(conversation.id);
    const options = document.createElement('button');
    options.className = 'conversation-options';
    options.type = 'button';
    options.textContent = '⋯';
    options.title = 'Chat options';
    options.setAttribute('aria-label', `Options for ${conversation.title || 'New chat'}`);
    const menu = document.createElement('div');
    menu.className = 'conversation-options-menu';
    menu.hidden = true;
    const rename = document.createElement('button');
    rename.type = 'button';
    rename.textContent = 'Rename';
    rename.onclick = () => {
      menu.hidden = true;
      renameConversation(conversation);
    };
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'delete';
    remove.textContent = 'Delete';
    remove.onclick = () => {
      menu.hidden = true;
      deleteConversation(conversation);
    };
    menu.append(rename, remove);
    options.onclick = (event) => {
      event.stopPropagation();
      menu.hidden = !menu.hidden;
    };
    item.append(button, options, menu);
    list.appendChild(item);
  });
}

async function refreshConversationList() {
  const response = await fetch('/api/conversations');
  if (!response.ok) throw new Error('Could not load chat history.');
  const data = await response.json();
  const conversations = data.conversations || [];
  renderConversationList(conversations);
  return conversations;
}

async function renameConversation(conversation) {
  const title = window.prompt('Chat name (maximum 40 characters)', conversation.title || 'New chat')?.trim().slice(0, 40);
  if (!title || title === conversation.title) return;
  const response = await fetch(`/api/conversations/${encodeURIComponent(conversation.id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title })
  });
  if (!response.ok) return alert('Could not rename this chat.');
  await refreshConversationList();
}

async function deleteConversation(conversation) {
  if (!window.confirm(`Delete "${conversation.title || 'New chat'}"?`)) return;
  const response = await fetch(`/api/conversations/${encodeURIComponent(conversation.id)}`, { method: 'DELETE' });
  if (!response.ok) return alert('Could not delete this chat.');
  if (conversation.id === conversationId) {
    conversationId = null;
    const conversations = await refreshConversationList();
    if (conversations.length) await openConversation(conversations[0].id);
    else await newChat();
  } else {
    await refreshConversationList();
  }
}

async function openConversation(id) {
  if (isGenerating) return;
  const loadSequence = ++conversationLoadSequence;
  const response = await fetch(`/api/conversations/${encodeURIComponent(id)}`);
  if (!response.ok || loadSequence !== conversationLoadSequence) return;
  renderConversation(await response.json());
  if (loadSequence === conversationLoadSequence) await refreshConversationList();
}

async function newChat() {
  const response = await fetch('/api/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: 'New chat' })
  });
  if (response.ok) {
    renderConversation(await response.json());
    await refreshConversationList();
  }
}

async function speakResponse(text) {
  try {
    const response = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    if (!response.ok || !(response.headers.get('content-type') || '').includes('audio/')) return;
    const audio = new Audio(URL.createObjectURL(await response.blob()));
    audio.onended = () => URL.revokeObjectURL(audio.src);
    await audio.play();
  } catch (error) {
    console.debug('TTS unavailable', error);
  }
}

async function streamMessage(query) {
  if (isGenerating) return;
  isGenerating = true;
  byId('userInput').disabled = true;
  byId('sendButton').disabled = true;
  byId('voiceButton').disabled = true;
  appendMessage(query, 'user');
  const botMessage = appendMessage('', 'bot');
  setMessageContent(botMessage, '', true);

  try {
    const response = await fetch('/api/robot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, history: chatHistory, conversation_id: conversationId })
    });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      for (const line of parts) {
        if (!line.startsWith('data: ')) continue;
        const payload = JSON.parse(line.slice(6));
        if (payload.delta) setMessageContent(botMessage, `${botMessage.dataset.text || ''}${payload.delta}`, true);
        if (payload.history) chatHistory = payload.history;
        if (payload.conversation_id) conversationId = payload.conversation_id;
        if (payload.response !== undefined) {
          setMessageContent(botMessage, payload.response);
          speakResponse(payload.response);
        }
      }
    }
  } catch (error) {
    setMessageContent(botMessage, 'Error communicating with local AI backend.');
    console.error(error);
  } finally {
    isGenerating = false;
    byId('userInput').disabled = false;
    byId('sendButton').disabled = false;
    byId('voiceButton').disabled = false;
    byId('userInput').focus();
    await refreshConversationList();
  }
}

async function toggleVoice() {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    alert('Microphone recording is unavailable.');
    return;
  }
  if (mediaRecorder?.state === 'recording') {
    mediaRecorder.stop();
    byId('voiceButton').classList.remove('recording');
    return;
  }
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true }
  });
  voiceChunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (event) => { if (event.data.size) voiceChunks.push(event.data); };
  mediaRecorder.onstop = async () => {
    stream.getTracks().forEach((track) => track.stop());
    byId('voiceButton').disabled = true;
    try {
      const response = await fetch('/api/voice/transcribe', {
        method: 'POST',
        headers: { 'Content-Type': mediaRecorder.mimeType || 'audio/webm' },
        body: new Blob(voiceChunks, { type: mediaRecorder.mimeType || 'audio/webm' })
      });
      const data = await response.json();
      if (data.status === 'ok' && data.text) await streamMessage(data.text);
    } finally {
      byId('voiceButton').disabled = false;
    }
  };
  mediaRecorder.start();
  byId('voiceButton').classList.add('recording');
}

document.addEventListener('DOMContentLoaded', async () => {
  byId('sidebarToggle').onclick = () => {
    if (innerWidth <= 760) byId('sidebar').classList.remove('mobile-open');
    else byId('sidebar').classList.toggle('collapsed');
  };
  byId('mobileMenu').onclick = () => byId('sidebar').classList.toggle('mobile-open');
  byId('newChatButton').onclick = newChat;
  byId('messageForm').onsubmit = (event) => {
    event.preventDefault();
    const input = byId('userInput');
    const query = input.value.trim();
    if (query) {
      input.value = '';
      autoResize();
      streamMessage(query);
    }
  };
  byId('userInput').oninput = autoResize;
  byId('userInput').onkeydown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      byId('messageForm').requestSubmit();
    }
  };
  byId('voiceButton').onclick = toggleVoice;
  document.addEventListener('click', () => {
    document.querySelectorAll('.conversation-options-menu').forEach((menu) => { menu.hidden = true; });
  });

  try {
    const response = await fetch('/api/status');
    const data = await response.json();
    const name = data.persona_name || 'Local Assistant';
    personaAvatar = data.persona_avatar || '';
    byId('brandName').textContent = name;
    byId('headerPersonaName').textContent = name;
    [byId('brandAvatar'), byId('panelAvatar')].forEach((avatar) => {
      if (!personaAvatar) return;
      avatar.textContent = '';
      const image = document.createElement('img');
      image.src = personaAvatar;
      image.alt = `${name} avatar`;
      avatar.appendChild(image);
    });
    byId('statusLabel').textContent = data.status;
    byId('headerPersonaStatus').textContent = data.status;
    byId('runtimeMode').textContent = `Mode: ${data.mode}`;
    byId('runtimeHardware').textContent = data.raspberry_pi ? 'Raspberry Pi' : 'Local host';
    byId('runtimeLatency').textContent = data.metrics?.average_latency_ms ? `${Math.round(data.metrics.average_latency_ms)} ms avg` : 'No requests';
    if (!data.voice_enabled || !data.voice_configured) byId('voiceButton').disabled = true;
  } catch (error) {
    console.error(error);
  }

  try {
    const conversations = await refreshConversationList();
    if (conversations.length) await openConversation(conversations[0].id);
    else await newChat();
  } catch (error) {
    console.error(error);
    byId('conversationList').textContent = 'Chat history unavailable.';
  }
});
