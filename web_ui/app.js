let conversationId = null;
let chatHistory = [];
let isGenerating = false;
let mediaRecorder = null;
let voiceChunks = [];
let personaAvatar = '';
let conversationLoadSequence = 0;
let generationController = null;
let attachedText = '';
let speakResponsesEnabled = true;

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
  element.classList.toggle('streaming', streaming);
  element.innerHTML = renderMarkdown(text);
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

function appendStreamingCursor(element) {
  if (!element.classList.contains('streaming')) return;
  element.querySelector('.cursor')?.remove();
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  cursor.setAttribute('aria-hidden', 'true');
  element.appendChild(cursor);
}

function openToolPanel(panelId) {
  document.querySelectorAll('.tool-panel-window').forEach((panel) => { panel.hidden = panel.id !== panelId; });
  const backdrop = byId('toolPanelBackdrop');
  backdrop.hidden = false;
  requestAnimationFrame(() => backdrop.classList.add('visible'));
}

function closeToolPanels() {
  document.querySelectorAll('.tool-panel-window').forEach((panel) => { panel.hidden = true; });
  const backdrop = byId('toolPanelBackdrop');
  backdrop.classList.remove('visible');
  setTimeout(() => { backdrop.hidden = true; }, 180);
}

async function copyText(text, button) {
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = '✓';
    setTimeout(() => { button.textContent = '⧉'; }, 1200);
  } catch (error) {
    button.title = 'Copy failed';
  }
}

function removeWelcome() {
  byId('welcomeScreen')?.remove();
}

function renderWelcome() {
  let welcome = byId('welcomeScreen');
  if (!welcome) {
    welcome = document.createElement('div');
    welcome.id = 'welcomeScreen';
    welcome.className = 'welcome-screen';
    welcome.innerHTML = '<div class="welcome-orb avatar" id="welcomeAvatar">AI</div><h1>What can I help you with?</h1><p>Ask locally for code, Linux help, or hardware control.</p><div class="suggestion-grid"><button type="button" data-prompt="Show me useful Linux commands for today.">Linux commands</button><button type="button" data-prompt="Help me write a small Python script.">Write Python</button><button type="button" data-prompt="What hardware status can you check?">Hardware status</button></div>';
  }
  byId('chatContainer').replaceChildren(welcome);
  welcome.hidden = false;
  const name = byId('headerPersonaName').textContent || 'AI';
  setAvatarImage(byId('welcomeAvatar'), name);
  bindWelcomePrompts();
}

function bindWelcomePrompts() {
  const welcome = byId('welcomeScreen');
  if (!welcome) return;
  welcome.querySelectorAll('[data-prompt]').forEach((button) => {
    button.onclick = () => {
      byId('userInput').value = button.dataset.prompt || '';
      autoResize();
      byId('userInput').focus();
    };
  });
}

function findMessageText(wrapper) {
  return wrapper?.querySelector('.message-body')?.dataset.text || wrapper?.querySelector('.message-body')?.textContent || '';
}

function addMessageActions(wrapper, role) {
  const actions = document.createElement('div');
  actions.className = 'message-actions';
  const copy = document.createElement('button');
  copy.type = 'button'; copy.textContent = '⧉'; copy.title = 'Copy'; copy.setAttribute('aria-label', 'Copy message');
  copy.onclick = () => copyText(findMessageText(wrapper), copy);
  actions.appendChild(copy);
  if (role === 'bot') {
    const speak = document.createElement('button');
    speak.type = 'button'; speak.textContent = '◖'; speak.title = 'Speak aloud'; speak.setAttribute('aria-label', 'Speak message');
    speak.onclick = () => speakResponse(findMessageText(wrapper));
    actions.appendChild(speak);
  } else {
    const edit = document.createElement('button');
    edit.type = 'button'; edit.textContent = '✎'; edit.title = 'Edit'; edit.setAttribute('aria-label', 'Edit message');
    edit.onclick = () => { byId('userInput').value = findMessageText(wrapper); autoResize(); byId('userInput').focus(); };
    actions.appendChild(edit);
  }
  const menuButton = document.createElement('button');
  menuButton.type = 'button'; menuButton.textContent = '⋯'; menuButton.title = 'Message menu'; menuButton.setAttribute('aria-label', 'Message menu');
  const menu = document.createElement('div');
  menu.className = 'message-menu'; menu.hidden = true;
  const retry = document.createElement('button');
  retry.type = 'button'; retry.textContent = 'Retry';
  retry.onclick = () => {
    menu.hidden = true;
    const previous = wrapper.previousElementSibling;
    const query = role === 'bot' ? findMessageText(previous) : findMessageText(wrapper);
    if (query) streamMessage(query);
  };
  menu.appendChild(retry);
  menuButton.onclick = (event) => { event.stopPropagation(); menu.hidden = !menu.hidden; };
  actions.append(menuButton, menu);
  wrapper.appendChild(actions);
}

async function loadCanonicalConfig() {
  const editor = byId('configEditor');
  try {
    const response = await fetch('/local-ai.config');
    if (!response.ok) throw new Error('Config not available');
    editor.value = await response.text();
    byId('configStatus').textContent = 'Loaded local-ai.config';
  } catch (error) {
    editor.value = '# local-ai.config\nMODE=balanced\nVOICE_ENABLED=true\nPERSONA_MODULE=persona.ryo_persona\nSERVER_PORT=5000\n';
    byId('configStatus').textContent = 'Loaded fallback configuration.';
  }
}

function autoResize() {
  const input = byId('userInput');
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 180)}px`;
}

function setAvatarImage(element, name) {
  if (!element || !personaAvatar) return;
  element.replaceChildren();
  const image = document.createElement('img');
  image.src = personaAvatar;
  image.alt = `${name} avatar`;
  image.onerror = () => {
    element.textContent = name.slice(0, 2).toUpperCase();
  };
  element.appendChild(image);
}

function syncPersonaAvatars(name) {
  setAvatarImage(byId('brandAvatar'), name);
  setAvatarImage(byId('panelAvatar'), name);
  setAvatarImage(byId('welcomeAvatar'), name);
  document.querySelectorAll('.message.bot .message-avatar').forEach((avatar) => setAvatarImage(avatar, name));
}

function appendMessage(text, role) {
  removeWelcome();
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
  addMessageActions(wrapper, role);
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
    renderWelcome();
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
  if (!speakResponsesEnabled || !text) return;
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
  generationController = new AbortController();
  byId('userInput').disabled = true;
  byId('sendButton').disabled = false;
  byId('sendButton').textContent = '■';
  byId('sendButton').setAttribute('aria-label', 'Stop generating');
  byId('sendButton').classList.add('streaming');
  byId('voiceButton').disabled = true;
  removeWelcome();
  const fullQuery = attachedText ? `${query}\n\nAttached file context:\n${attachedText}` : query;
  attachedText = '';
  byId('attachmentChip').hidden = true;
  appendMessage(fullQuery, 'user');
  const botMessage = appendMessage('', 'bot');
  setMessageContent(botMessage, '', true);
  appendStreamingCursor(botMessage);

  try {
    const response = await fetch('/api/robot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: fullQuery, history: chatHistory, conversation_id: conversationId, mode: byId('modeSelect').value }),
      signal: generationController.signal
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
        if (payload.delta) {
          setMessageContent(botMessage, `${botMessage.dataset.text || ''}${payload.delta}`, true);
          appendStreamingCursor(botMessage);
        }
        if (payload.history) chatHistory = payload.history;
        if (payload.conversation_id) conversationId = payload.conversation_id;
        if (payload.response !== undefined) {
          setMessageContent(botMessage, payload.response);
          speakResponse(payload.response);
        }
      }
    }
  } catch (error) {
    if (error.name !== 'AbortError') {
      setMessageContent(botMessage, 'Error communicating with local AI backend.');
      console.error(error);
    } else {
      botMessage.closest('.message')?.remove();
    }
  } finally {
    isGenerating = false;
    generationController = null;
    byId('userInput').disabled = false;
    byId('sendButton').textContent = '➜';
    byId('sendButton').setAttribute('aria-label', 'Send');
    byId('sendButton').classList.remove('streaming');
    byId('voiceButton').disabled = false;
    byId('userInput').focus();
    await refreshConversationList();
  }
}

function stopGeneration() {
  generationController?.abort();
}

async function attachTextFile(file) {
  if (!file) return;
  if (file.size > 65536) return alert('Text attachments must be 64 KB or smaller.');
  attachedText = await file.text();
  const chip = byId('attachmentChip');
  chip.textContent = `${file.name} ×`;
  chip.hidden = false;
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
    if (innerWidth <= 760) {
      byId('sidebar').classList.remove('mobile-open');
      byId('sidebarBackdrop').classList.remove('visible');
    } else {
      byId('sidebar').classList.toggle('collapsed');
    }
  };
  byId('mobileMenu').onclick = () => {
    byId('sidebar').classList.add('mobile-open');
    byId('sidebarBackdrop').classList.add('visible');
  };
  byId('sidebarBackdrop').onclick = () => {
    byId('sidebar').classList.remove('mobile-open');
    byId('sidebarBackdrop').classList.remove('visible');
  };
  byId('newChatButton').onclick = newChat;
  byId('railNewChat').onclick = newChat;
  const railToolDropdown = byId('railToolDropdown');
  byId('railTools').onclick = () => {
    if (!byId('sidebar').classList.contains('collapsed')) {
      openToolPanel('memoryPanel');
      return;
    }
    railToolDropdown.hidden = !railToolDropdown.hidden;
  };
  byId('railToolDropdown').querySelectorAll('[data-panel]').forEach((button) => {
    button.onclick = () => {
      railToolDropdown.hidden = true;
      openToolPanel(button.dataset.panel);
    };
  });
  byId('messageForm').onsubmit = (event) => {
    event.preventDefault();
    if (isGenerating) return stopGeneration();
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
  bindWelcomePrompts();
  byId('sendButton').onclick = (event) => { if (isGenerating) { event.preventDefault(); stopGeneration(); } };
  byId('attachButton').onclick = () => byId('attachmentInput').click();
  byId('attachmentInput').onchange = (event) => attachTextFile(event.target.files?.[0]);
  byId('attachmentChip').onclick = () => { attachedText = ''; byId('attachmentChip').hidden = true; };
  byId('toolsButton').onclick = () => {
    const panel = byId('toolsPanel');
    panel.hidden = !panel.hidden;
    byId('toolsButton').setAttribute('aria-expanded', String(!panel.hidden));
  };
  byId('settingsButton').onclick = () => {
    openToolPanel('settingsPanel');
    byId('settingsAccountSection').hidden = false;
    byId('settingsConfigSection').hidden = true;
    document.querySelectorAll('[data-settings-tab]').forEach((tab) => tab.classList.toggle('active', tab.dataset.settingsTab === 'account'));
  };
  const memoryTabs = Array.from(document.querySelectorAll('[data-memory-tab]'));
  const memoryPanels = {
    history: byId('memoryHistoryPanel'),
    memory: byId('memoryMemoryPanel'),
    knowledge: byId('memoryKnowledgePanel'),
  };
  memoryTabs.forEach((tab) => {
    tab.onclick = () => {
      const target = tab.dataset.memoryTab;
      memoryTabs.forEach((item) => item.classList.toggle('active', item === tab));
      Object.entries(memoryPanels).forEach(([key, panel]) => {
        panel.hidden = key !== target;
      });
    };
  });

  document.querySelectorAll('.tool-entry').forEach((button) => { button.onclick = () => openToolPanel(button.dataset.panel); });
  document.querySelectorAll('.panel-close').forEach((button) => { button.onclick = closeToolPanels; });
  byId('toolPanelBackdrop').onclick = closeToolPanels;
  byId('saveMemoryButton').onclick = () => {
    const note = byId('memoryNote').value.trim();
    if (!note) return;
    const notes = JSON.parse(localStorage.getItem('local-assistant-memory') || '[]');
    notes.push({ note, createdAt: new Date().toISOString() });
    localStorage.setItem('local-assistant-memory', JSON.stringify(notes.slice(-50)));
    byId('memoryNote').value = '';
    byId('memoryNoteStatus').textContent = 'Memory note saved locally.';
  };

  byId('memoryKnowledgeImportButton').onclick = () => {
    byId('memoryKnowledgeFileInput')?.click();
  };

  byId('memoryKnowledgeFileInput').onchange = async (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    const body = new FormData();
    files.forEach((file) => body.append('files', file));
    byId('memoryKnowledgeStatus').textContent = 'Importing files into configured knowledge directory...';
    try {
      const response = await fetch('/api/knowledge/import', { method: 'POST', body });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || data.message || 'Knowledge import failed');
      byId('memoryKnowledgeStatus').textContent = `Imported ${data.imported.length} file(s) into ${data.knowledge_dir || 'knowledge dir'}.`;
    } catch (error) {
      byId('memoryKnowledgeStatus').textContent = error.message || 'Knowledge import failed.';
    }
  };

  byId('memoryKnowledgeDigestButton').onclick = async () => {
    byId('memoryKnowledgeStatus').textContent = 'Digesting configured knowledge directory...';
    try {
      const response = await fetch('/api/knowledge/digest', { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Knowledge digest failed');
      byId('memoryKnowledgeStatus').textContent = `Knowledge digest complete: ${data.db_path || 'updated database'}.`;
    } catch (error) {
      byId('memoryKnowledgeStatus').textContent = error.message || 'Knowledge digest failed.';
    }
  };

  byId('memoryKnowledgeRebuildButton').onclick = async () => {
    byId('memoryKnowledgeStatus').textContent = 'Reindexing configured knowledge directory...';
    try {
      const response = await fetch('/api/knowledge/reindex', { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Knowledge reindex failed');
      byId('memoryKnowledgeStatus').textContent = `Knowledge reindex complete: ${data.db_path || 'updated database'}.`;
    } catch (error) {
      byId('memoryKnowledgeStatus').textContent = error.message || 'Knowledge reindex failed.';
    }
  };
  document.querySelectorAll('[data-hardware-action]').forEach((button) => {
    button.onclick = () => { byId('hardwareStatus').textContent = `${button.textContent} queued for ESP32 integration.`; };
  });
  byId('speakToggle').onchange = (event) => { speakResponsesEnabled = event.target.checked; };
  byId('clearChatButton').onclick = () => { byId('toolsPanel').hidden = true; newChat(); };
  byId('settingsConfigSection').hidden = true;
  document.querySelectorAll('[data-settings-tab]').forEach((tab) => {
    tab.onclick = () => {
      const target = tab.dataset.settingsTab;
      document.querySelectorAll('[data-settings-tab]').forEach((item) => item.classList.toggle('active', item === tab));
      byId('settingsAccountSection').hidden = target !== 'account';
      byId('settingsConfigSection').hidden = target !== 'configuration';
      if (target === 'configuration' && !byId('configEditor').value.trim()) {
        loadCanonicalConfig();
      }
    };
  });

  byId('assetImportButton').onclick = () => {
    byId('assetImportInput').click();
  };

  byId('assetImportInput').onchange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append('file', file);
    try {
      byId('assetImportStatus').textContent = `Importing ${file.name}...`;
      const response = await fetch('/api/assets/upload', {
        method: 'POST',
        body
      });
      if (!response.ok) throw new Error('Asset upload failed');
      const data = await response.json();
      byId('assetImportStatus').textContent = `Imported ${file.name} to ${data.path || 'assets'}`;
    } catch (error) {
      byId('assetImportStatus').textContent = 'Import failed';
    }
  };

  byId('saveConfigButton').onclick = async () => {
    const text = byId('configEditor').value || '';
    byId('configStatus').textContent = 'Saving local-ai.config...';
    try {
      const response = await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain;charset=utf-8' },
        body: text,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.message || 'Configuration save failed');
      byId('configStatus').textContent = `local-ai.config saved to ${data.path || 'project config'}.`;
    } catch (error) {
      byId('configStatus').textContent = error.message || 'Configuration editor updated locally.';
    }
  };
  await loadCanonicalConfig();
  document.addEventListener('click', () => {
    document.querySelectorAll('.conversation-options-menu').forEach((menu) => { menu.hidden = true; });
    document.querySelectorAll('.message-menu').forEach((menu) => { menu.hidden = true; });
  });

  try {
    const response = await fetch('/api/status');
    const data = await response.json();
    const name = data.persona_name || 'Local Assistant';
    personaAvatar = data.persona_avatar || '';
    byId('brandName').textContent = name;
    byId('headerPersonaName').textContent = name;
    syncPersonaAvatars(name);
    byId('statusLabel').textContent = data.status;
    if (byId('memoryKnowledgePath')) {
      byId('memoryKnowledgePath').textContent = data.knowledge_dir || 'configured knowledge dir';
    }
    byId('headerPersonaStatus').textContent = data.status;
    if ([...byId('modeSelect').options].some((option) => option.value === data.mode)) byId('modeSelect').value = data.mode;
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
