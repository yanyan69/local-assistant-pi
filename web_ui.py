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
                --bg-main: #0f1117;
                --bg-panel: #171b24;
                --bg-soft: #1d2430;
                --bg-chat: #111722;
                --bg-msg-user: linear-gradient(135deg, #2d5bff, #4f8cff);
                --bg-msg-bot: #1b2230;
                --bg-input: #1a2330;
                --border-color: rgba(255, 255, 255, 0.08);
                --accent-color: #7c9cff;
                --accent-hover: #5d82ff;
                --text-main: #edf3ff;
                --text-muted: #9aa8c3;
                --text-soft: #c3cee7;
                --hw-badge: #f5b94a;
                --code-bg: #0d1117;
                --code-header-bg: #141b26;
                --shadow-soft: 0 12px 28px rgba(0, 0, 0, 0.26);
                --radius-lg: 22px;
                --radius-md: 16px;
                --radius-sm: 12px;
            }

            * { box-sizing: border-box; margin: 0; padding: 0; }

            html, body {
                height: 100%;
                background: var(--bg-main);
                color: var(--text-main);
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }

            body {
                overflow: hidden;
                height: 100dvh;
            }

            .app-container {
                display: flex;
                width: 100%;
                height: 100vh;
                background: radial-gradient(circle at top, rgba(124, 156, 255, 0.18), transparent 36%), var(--bg-main);
            }

            .sidebar {
                width: 270px;
                background: rgba(19, 24, 33, 0.96);
                border-right: 1px solid var(--border-color);
                display: flex;
                flex-direction: column;
                padding: 18px 16px;
                flex-shrink: 0;
                gap: 18px;
                transition: width 0.26s cubic-bezier(0.22, 1, 0.36, 1), padding 0.26s cubic-bezier(0.22, 1, 0.36, 1);
                will-change: width;
            }

            .sidebar.collapsed {
                width: 52px;
                padding-left: 6px;
                padding-right: 6px;
                gap: 0;
            }

            .sidebar.collapsed > :not(.brand) {
                display: none;
            }

            .sidebar.collapsed .brand {
                justify-content: center;
                gap: 0;
                padding: 0;
                border-bottom: 0;
            }

            .sidebar.collapsed .brand > :not(.sidebar-toggle) {
                display: none;
            }

            .sidebar.collapsed .brand-title,
            .sidebar.collapsed .brand-avatar,
            .sidebar.collapsed .sidebar-card,
            .sidebar.collapsed .quick-actions,
            .sidebar.collapsed .sidebar-btn,
            .sidebar.collapsed .music-card,
            .sidebar.collapsed .system-info,
            .sidebar.collapsed .settings-label-bar,
            .sidebar.collapsed .profile-mini .mini-meta,
            .sidebar.is-animating .brand-avatar,
            .sidebar.is-animating .brand-title,
            .sidebar.is-animating .sidebar-card,
            .sidebar.is-animating .quick-actions,
            .sidebar.is-animating .sidebar-btn,
            .sidebar.is-animating .music-card,
            .sidebar.is-animating .system-info,
            .sidebar.is-animating .settings-label-bar,
            .sidebar.is-animating .quick-actions-toggle .label,
            .sidebar.is-animating .profile-mini .mini-meta {
                opacity: 0;
                pointer-events: none;
                max-height: 0;
                overflow: hidden;
                margin: 0;
                padding: 0;
                border: 0;
            }

            .sidebar.collapsed .brand-avatar,
            .sidebar.is-animating .brand-avatar {
                display: none;
            }

            .sidebar.collapsed .sidebar-card {
                padding: 10px;
            }

            .sidebar.collapsed .profile-mini {
                justify-content: center;
                padding: 0;
            }

            .sidebar.collapsed .profile-mini .avatar-slot {
                flex: 0 0 36px;
            }

            .sidebar.collapsed .sidebar-btn {
                justify-content: center;
                padding-left: 10px;
                padding-right: 10px;
            }

            .sidebar.collapsed .brand {
                justify-content: center;
                gap: 0;
                padding-left: 0;
                padding-right: 0;
                padding-bottom: 12px;
            }

            .sidebar.collapsed .sidebar-toggle {
                margin-left: 0;
            }

            .sidebar.collapsed .music-card {
                justify-content: center;
                width: 100%;
                padding-left: 0;
                padding-right: 0;
            }

            .sidebar-toggle {
                width: 40px;
                height: 40px;
                flex: 0 0 40px;
                border-radius: 10px;
                border: 1px solid var(--border-color);
                background: rgba(255,255,255,0.02);
                color: var(--text-main);
                cursor: pointer;
                display: grid;
                place-items: center;
                margin-left: auto;
                padding: 0;
            }

            .brand {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 8px 4px 14px;
                border-bottom: 1px solid var(--border-color);
            }

            .brand-avatar {
                width: 38px;
                height: 38px;
                flex: 0 0 38px;
                border-radius: 12px;
                display: grid;
                place-items: center;
                font-weight: 700;
                background: linear-gradient(135deg, #7c9cff, #adc2ff);
                color: #0b1020;
                box-shadow: var(--shadow-soft);
                overflow: hidden;
            }

            .brand-avatar img,
            .panel-avatar img,
            .msg-avatar img,
            .avatar-slot img {
                width: 100%;
                height: 100%;
                max-width: 100%;
                max-height: 100%;
                min-width: 0;
                min-height: 0;
                display: block;
                box-sizing: border-box;
                object-fit: contain;
                object-position: center;
            }

            .brand-title h1 {
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.02em;
            }

            .status {
                display: flex;
                align-items: center;
                gap: 6px;
                font-size: 11px;
                color: #7be4ac;
                margin-top: 2px;
            }

                width: 100%;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                border: 0;
                border-radius: 8px;
                background: transparent;
                color: var(--text-soft);
                cursor: pointer;
                padding: 8px;
                text-align: left;
                font-size: 12px;
            }

            .conversation-item:hover,
            .conversation-item.active {
                background: rgba(124, 156, 255, 0.14);
                color: var(--text-main);
            }

            .profile-mini {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 4px 2px 12px;
            }

            .mini-avatar,
            .avatar-slot {
                width: 36px;
                height: 36px;
                border-radius: 50%;
                display: grid;
                place-items: center;
                background: linear-gradient(135deg, #ffb989, #ff7fa8);
                overflow: hidden;
                border: 1px solid rgba(255,255,255,0.12);
                box-shadow: var(--shadow-soft);
            }

            .avatar-slot img {
                width: 100%;
                height: 100%;
                object-fit: cover;
                display: block;
            }

            .mini-meta {
                display: flex;
                flex-direction: column;
                gap: 2px;
            }

            .mini-meta strong {
                font-size: 13px;
            }

            .mini-meta span {
                font-size: 11px;
                color: var(--text-muted);
            }

            .sidebar-btn {
                width: 100%;
                min-height: 40px;
                background: rgba(124, 156, 255, 0.08);
                border: 1px solid var(--border-color);
                color: var(--text-main);
                padding: 10px 12px;
                border-radius: 10px;
                cursor: pointer;
                font-size: 13px;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
            }

            .sidebar-btn > svg {
                width: 16px;
                height: 16px;
                flex: 0 0 16px;
            }

            .sidebar-btn .label {
                min-width: 0;
                white-space: nowrap;
                overflow: hidden;
                opacity: 1;
                transition: opacity 0.12s ease;
            }

            .sidebar-btn:hover {
                background: rgba(124, 156, 255, 0.14);
                transform: translateY(-1px);
            }

            .quick-actions {
                position: relative;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }

            .quick-actions-toggle {
                width: 100%;
                min-height: 40px;
                display: flex;
                align-items: center;
                justify-content: flex-start;
                gap: 8px;
                padding: 10px 12px;
                border: 1px solid var(--border-color);
                border-radius: 10px;
                background: rgba(124, 156, 255, 0.08);
                color: var(--text-main);
                cursor: pointer;
                transition: background 0.2s ease, border-color 0.2s ease;
            }

            .quick-actions-toggle svg {
                width: 16px;
                height: 16px;
                flex: 0 0 16px;
            }

            .quick-actions-toggle .label {
                white-space: nowrap;
                overflow: hidden;
            }

            .quick-actions-toggle:hover {
                background: rgba(124, 156, 255, 0.14);
                border-color: rgba(124, 156, 255, 0.45);
            }

            .quick-menu {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                max-height: 0;
                overflow: hidden;
                opacity: 0;
                pointer-events: none;
                transform: translateY(-6px);
                transition: max-height 0.24s ease, opacity 0.18s ease, transform 0.24s ease;
            }

            .quick-actions.open .quick-menu {
                max-height: 180px;
                opacity: 1;
                pointer-events: auto;
                transform: translateY(0);
            }

            .sidebar.collapsed .quick-actions {
                align-items: center;
            }

            .sidebar.collapsed .quick-actions-toggle {
                width: 40px;
                height: 40px;
                min-height: 40px;
                justify-content: center;
                padding: 0;
            }

            .sidebar.collapsed .quick-actions-toggle .label {
                display: none;
            }

            .sidebar.collapsed .quick-actions.open .quick-menu {
                position: absolute;
                z-index: 10;
                top: 0;
                left: 52px;
                width: 184px;
                padding: 10px;
                max-height: 180px;
                border: 1px solid var(--border-color);
                border-radius: 12px;
                background: rgba(23, 27, 36, 0.98);
                box-shadow: var(--shadow-soft);
            }

            .chip {
                background: rgba(255,255,255,0.03);
                border: 1px solid var(--border-color);
                color: var(--text-soft);
                border-radius: 999px;
                padding: 6px 10px;
                font-size: 11px;
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .chip:hover {
                border-color: rgba(124, 156, 255, 0.6);
                background: rgba(124, 156, 255, 0.08);
            }

            .music-card {
                display: flex;
                align-items: center;
                gap: 10px;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 10px 10px;
                opacity: 1;
                transform: translateY(0);
                transition: opacity 0.2s ease, transform 0.2s ease, max-height 0.2s ease;
                max-height: 120px;
                overflow: hidden;
            }

            .music-card.hidden {
                opacity: 0;
                transform: translateY(-4px);
                max-height: 0;
                padding-top: 0;
                padding-bottom: 0;
                border-width: 0;
                margin: 0;
                pointer-events: none;
            }

            .music-art {
                width: 42px;
                height: 42px;
                flex: 0 0 42px;
                border-radius: 10px;
                background: linear-gradient(135deg, #7c9cff, #5ec5ff);
                display: grid;
                place-items: center;
                color: #091421;
                font-size: 18px;
                font-weight: 700;
            }

            .music-label {
                display: block;
                font-size: 10px;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--text-muted);
            }

            .music-track {
                display: block;
                font-size: 12px;
                font-weight: 600;
                margin-top: 3px;
                color: var(--text-main);
                line-height: 1.4;
            }

            .music-folder {
                display: block;
                font-size: 10px;
                color: var(--text-muted);
                margin-top: 2px;
            }

            .system-info {
                font-size: 11px;
                color: var(--text-muted);
                line-height: 1.7;
                padding: 10px 12px;
                background: rgba(255, 255, 255, 0.02);
                border-radius: var(--radius-sm);
                border: 1px solid var(--border-color);
            }

            .main-content {
                flex: 1;
                display: flex;
                flex-direction: column;
                min-width: 0;
                min-height: 0;
                height: 100dvh;
                background: var(--bg-chat);
                position: relative;
            }

            .chat-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                padding: 18px 24px 14px;
                border-bottom: 1px solid var(--border-color);
                background: rgba(17, 23, 34, 0.9);
                backdrop-filter: blur(10px);
                flex: 0 0 auto;
                min-height: 70px;
            }

            .chat-header .left {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .chat-header .left .panel-avatar {
                width: 36px;
                height: 36px;
                border-radius: 50%;
                display: grid;
                place-items: center;
                background: linear-gradient(135deg, #7c9cff, #6ce3ff);
                color: #0d1424;
                font-weight: 700;
                overflow: hidden;
            }

            .chat-header .info strong {
                display: block;
                font-size: 14px;
            }

            .chat-header .info span {
                font-size: 11px;
                color: var(--text-muted);
            }

            .chat-actions {
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .chat-pill {
                background: rgba(124, 156, 255, 0.12);
                color: var(--text-soft);
                border: 1px solid var(--border-color);
                padding: 7px 10px;
                border-radius: 999px;
                font-size: 11px;
            }

            .chat-box {
                flex: 1;
                min-height: 0;
                overflow-y: auto;
                padding: 20px 18px 10px;
                scroll-behavior: smooth;
            }

            .chat-container {
                max-width: 860px;
                width: 100%;
                margin: 0 auto;
                display: flex;
                flex-direction: column;
                gap: 16px;
            }

            .msg-wrapper {
                display: flex;
                gap: 12px;
                align-items: flex-end;
                width: 100%;
            }

            .msg-wrapper.user {
                justify-content: flex-end;
            }

            .msg-wrapper.bot {
                justify-content: flex-start;
            }

            .msg-avatar {
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: grid;
                place-items: center;
                font-size: 10px;
                font-weight: 700;
                flex-shrink: 0;
                color: white;
                box-shadow: var(--shadow-soft);
                overflow: hidden;
            }

            .msg-wrapper.bot .msg-avatar {
                background: linear-gradient(135deg, #7c9cff, #5ec5ff);
                color: #08111f;
            }

            .msg-wrapper.user .msg-avatar {
                background: linear-gradient(135deg, #ff8f70, #ffb285);
            }

            .msg-content {
                max-width: min(72%, 680px);
                border-radius: 18px;
                padding: 13px 15px;
                line-height: 1.6;
                font-size: 14.5px;
                border: 1px solid var(--border-color);
                color: var(--text-main);
                overflow-wrap: anywhere;
                word-break: break-word;
                hyphens: auto;
                box-shadow: var(--shadow-soft);
            }

            .msg-wrapper.bot .msg-content {
                background: var(--bg-msg-bot);
                border-bottom-left-radius: 8px;
            }

            .msg-wrapper.user .msg-content {
                background: var(--bg-msg-user);
                border-bottom-right-radius: 8px;
                border-color: rgba(255, 255, 255, 0.08);
            }

            .msg-content p { margin-bottom: 0.7em; }
            .msg-content p:last-child { margin-bottom: 0; }
            .msg-content h1, .msg-content h2, .msg-content h3 { margin: 0.9em 0 0.45em; color: #fff; }
            .msg-content ul, .msg-content ol { margin: 0.6em 0 0.8em 1.4em; }
            .msg-content li { margin-bottom: 0.25em; }
            .msg-content blockquote {
                border-left: 3px solid var(--accent-color);
                padding-left: 10px;
                margin: 0.8em 0;
                color: var(--text-muted);
            }

            .hardware-tag {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                background: rgba(245, 185, 74, 0.12);
                border: 1px solid rgba(245, 185, 74, 0.35);
                color: var(--hw-badge);
                padding: 4px 8px;
                border-radius: 999px;
                margin-top: 10px;
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }

            .code-block-wrapper {
                background: var(--code-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                margin: 12px 0;
                overflow: hidden;
            }

            .code-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: var(--code-header-bg);
                padding: 7px 12px;
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
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
                font-size: 12.7px;
                color: #e5edf8;
            }

            p code, li code {
                display: inline;
                padding: 2px 6px;
                background: rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                color: #f7c4da;
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
                border-radius: 6px;
                display: flex;
                align-items: center;
                gap: 5px;
                transition: all 0.2s ease;
            }

            .copy-btn:hover {
                color: white;
                background: rgba(255, 255, 255, 0.06);
            }

            .copy-btn svg {
                width: 13px;
                height: 13px;
                fill: currentColor;
            }

            .input-container {
                padding: 14px 18px 18px;
                background: rgba(17, 23, 34, 0.9);
                border-top: 1px solid var(--border-color);
                flex: 0 0 auto;
            }

            .mobile-menu-btn {
                display: none;
                width: 36px;
                height: 36px;
                border: 1px solid var(--border-color);
                border-radius: 10px;
                background: rgba(255,255,255,0.04);
                color: var(--text-main);
                font-size: 18px;
            }

            .input-box-wrapper {
                max-width: 860px;
                width: 100%;
                margin: 0 auto;
            }

            .input-box {
                display: flex;
                align-items: flex-end;
                gap: 10px;
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid var(--border-color);
                border-radius: 18px;
                padding: 10px 12px 10px 14px;
                box-shadow: var(--shadow-soft);
            }

            .input-box:focus-within {
                border-color: rgba(124, 156, 255, 0.7);
                box-shadow: 0 0 0 1px rgba(124, 156, 255, 0.18), var(--shadow-soft);
            }

            textarea {
                flex: 1;
                background: transparent;
                border: none;
                outline: none;
                color: #fff;
                font-size: 15px;
                line-height: 1.45;
                padding: 8px 0;
                resize: none;
                max-height: 180px;
                min-height: 24px;
                font-family: inherit;
            }

            textarea::placeholder {
                color: var(--text-muted);
            }

            .send-btn {
                width: 42px;
                height: 42px;
                border: none;
                border-radius: 12px;
                background: linear-gradient(135deg, var(--accent-color), var(--accent-hover));
                color: white;
                display: grid;
                place-items: center;
                cursor: pointer;
                transition: transform 0.15s ease, opacity 0.15s ease;
                flex-shrink: 0;
            }

            .send-btn:hover {
                transform: translateY(-1px);
            }

            .send-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
            }

            .voice-btn {
                width: 42px;
                height: 42px;
                border: 1px solid var(--border-color);
                border-radius: 12px;
                background: rgba(255,255,255,0.04);
                color: var(--text-soft);
                display: grid;
                place-items: center;
                cursor: pointer;
                flex-shrink: 0;
            }

            .voice-btn.recording {
                color: #ff9a9a;
                border-color: rgba(255, 110, 110, 0.75);
                background: rgba(255, 90, 90, 0.14);
            }

            .voice-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .cursor {
                display: inline-block;
                width: 7px;
                height: 14px;
                background: var(--accent-color);
                margin-left: 4px;
                vertical-align: middle;
                animation: blink 0.8s infinite;
                border-radius: 2px;
            }

            @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

            @media (max-width: 900px) {
                .sidebar {
                    width: 210px;
                }
                .msg-content {
                    max-width: 78%;
                }
            }

            @media (max-width: 760px) {
                body {
                    overflow: hidden;
                }

                .app-container {
                    display: block;
                    height: 100dvh;
                    min-height: 0;
                    position: relative;
                }

                .sidebar {
                    display: none;
                    position: absolute;
                    z-index: 20;
                    top: 0;
                    left: 0;
                    width: min(88vw, 320px);
                    height: 100dvh;
                    box-shadow: 16px 0 36px rgba(0, 0, 0, 0.35);
                }

                .sidebar.mobile-open { display: flex; }

                .main-content {
                    width: 100%;
                    height: 100dvh;
                    min-height: 0;
                }

                .chat-header {
                    padding: 14px 14px 12px;
                    min-height: 64px;
                }

                .mobile-menu-btn { display: grid; place-items: center; }

                .chat-header .left { min-width: 0; }
                .chat-header .info { min-width: 0; }
                .chat-header .info strong,
                .chat-header .info span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

                .chat-actions .chat-pill { display: none; }

                .chat-box {
                    padding: 12px 12px 8px;
                }

                .msg-content {
                    max-width: 82%;
                    border-radius: 16px;
                    padding: 11px 12px;
                    font-size: 14px;
                }

                .input-container {
                    padding: 10px 12px 14px;
                }

                .input-box { min-height: 62px; }
                textarea { min-width: 0; }
            }
        </style>
    </head>
    <body>
        <div class="app-container">
            <aside class="sidebar" id="sidebar">
                <div class="brand">
                    <div class="brand-avatar" id="brandAvatar">AI</div>
                    <div class="brand-title">
                        <h1 id="brandName">Local Assistant</h1>
                        <div class="status"><span class="status-dot" id="statusDot"></span> <span id="statusLabel">Local AI</span></div>
                    </div>
                    <button class="sidebar-toggle" id="sidebarToggle" aria-label="Toggle sidebar">☰</button>
                </div>

                <div class="sidebar-card">
                    <div class="profile-mini">
                        <div class="avatar-slot" aria-label="User avatar">U</div>
                        <div class="mini-meta">
                            <strong>You</strong>
                            <span>Pi owner</span>
                        </div>
                    </div>
                </div>

                <div class="quick-actions">
                    <button class="quick-actions-toggle" id="quickActionsToggle" aria-label="Open quick commands" aria-expanded="false">
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z"/></svg>
                        <span class="label">Quick commands</span>
                    </button>
                    <div class="quick-menu" id="quickMenu">
                        <button class="chip" data-action="MUSIC_ON">Music on</button>
                        <button class="chip" data-action="MUSIC_STOP">Music off</button>
                        <button class="chip" data-action="LED_ON">Lights on</button>
                        <button class="chip" data-action="LED_OFF">Lights off</button>
                    </div>
                </div>

                <button class="sidebar-btn" onclick="startNewChat()">
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                    <span class="label">New chat</span>
                </button>

                <div class="sidebar-card conversation-card">
                    <div class="mini-meta"><strong>Chat history</strong></div>
                    <div class="conversation-list" id="conversationList"></div>
                </div>

                <div class="music-card">
                    <div class="music-art">♫</div>
                    <div class="music-info">
                        <span class="music-label">Now playing</span>
                        <strong class="music-track" id="currentTrackLabel">No track playing</strong>
                        <span class="music-folder" id="musicFolderLabel">Configured media directory</span>
                    </div>
                </div>

                <div class="sidebar-spacer" style="flex:1;"></div>

                <div class="system-info">
                    <strong>Engine:</strong> Llama 3 (Local)<br>
                    <strong>Mode:</strong> <span id="runtimeMode">Loading...</span><br>
                    <strong>Hardware:</strong> <span id="runtimeHardware">Local host</span><br>
                    <strong>Execution:</strong> <span id="runtimeSafety">Checking...</span><br>
                    <strong>Latency:</strong> <span id="runtimeLatency">Checking...</span>
                </div>

            </aside>

            <main class="main-content">
                <div class="chat-header">
                    <div class="left">
                        <button class="mobile-menu-btn" onclick="toggleMobileSidebar()" aria-label="Open menu">☰</button>
                        <div class="panel-avatar" id="panelAvatar">AI</div>
                        <div class="info">
                            <strong id="headerPersonaName">Local Assistant</strong>
                            <span id="headerPersonaStatus">Ready</span>
                        </div>
                    </div>
                    <div class="chat-actions">
                        <div class="chat-pill">Pi 5</div>
                    </div>
                </div>

                <div class="chat-box" id="chatBox">
                    <div class="chat-container" id="chatContainer">
                        <div class="msg-wrapper bot">
                            <div class="msg-avatar">AI</div>
                            <div class="msg-content">
                                System initialized and running locally. Ask for code, Linux help, or hardware control.
                            </div>
                        </div>
                    </div>
                </div>

                <div class="input-container">
                    <div class="input-box-wrapper">
                        <div class="input-box">
                            <textarea id="userInput" rows="1" placeholder="Message the assistant..." oninput="autoResize(this)" onkeydown="handleKeyDown(event)"></textarea>
                            <button class="voice-btn" id="voiceBtn" onclick="toggleVoiceInput()" aria-label="Speak to assistant" title="Speak to assistant">
                                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 10v2a7 7 0 0 1-14 0v-2m7 9v3m-4 0h8"/></svg>
                            </button>
                            <button class="send-btn" id="sendBtn" onclick="sendMsg()" aria-label="Send message">
                                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M12 5l7 7-7 7"/></svg>
                            </button>
                        </div>
                    </div>
                </div>
            </main>
        </div>

        <script>
            let chatHistory = [];
            let mediaDirectory = 'Configured media directory';
            let conversationId = null;
            let isGenerating = false;
            let voiceRecorder = null;
            let voiceChunks = [];

            function toggleMobileSidebar() {
                const sidebar = document.getElementById('sidebar');
                if (sidebar) sidebar.classList.toggle('mobile-open');
            }

            function applyPersona(data) {
                const name = data.persona_name || 'Local Assistant';
                const avatarUrl = data.persona_avatar;
                ['brandName', 'headerPersonaName'].forEach((id) => {
                    const element = document.getElementById(id);
                    if (element) element.textContent = name;
                });
                ['brandAvatar', 'panelAvatar'].forEach((id) => {
                    const element = document.getElementById(id);
                    if (!element) return;
                    if (avatarUrl) {
                        element.innerHTML = `<img src="${avatarUrl}" alt="${name} avatar">`;
                    } else {
                        element.textContent = name.slice(0, 2).toUpperCase();
                    }
                });
                document.querySelectorAll('.msg-avatar').forEach((element) => {
                    if (element.closest('.msg-wrapper.user')) return;
                    if (avatarUrl) element.innerHTML = `<img src="${avatarUrl}" alt="${name} avatar">`;
                    else element.textContent = name.slice(0, 2).toUpperCase();
                });
                const voiceBtn = document.getElementById('voiceBtn');
                if (voiceBtn && (!data.voice_enabled || !data.voice_configured)) {
                    voiceBtn.disabled = true;
                    voiceBtn.title = 'Enable and configure local voice in local-ai.config';
                }
            }

            async function pollProactiveMessage() {
                try {
                    const response = await fetch('/api/proactive');
                    if (!response.ok) return;
                    const data = await response.json();
                    if (data.message) appendMsg(data.message, 'bot');
                } catch (error) {
                    console.error('Proactive status error:', error);
                }
            }

            function renderConversationList(conversations) {
                const list = document.getElementById('conversationList');
                if (!list) return;
                list.innerHTML = '';
                conversations.forEach((conversation) => {
                    const button = document.createElement('button');
                    button.className = `conversation-item${conversation.id === conversationId ? ' active' : ''}`;
                    button.textContent = conversation.title || 'New chat';
                    button.title = conversation.title || 'New chat';
                    button.onclick = () => openConversation(conversation.id);
                    list.appendChild(button);
                });
            }

            async function loadConversations() {
                try {
                    const response = await fetch('/api/conversations');
                    const data = await response.json();
                    renderConversationList(data.conversations || []);
                    if (!conversationId && data.conversations?.length) {
                        await openConversation(data.conversations[0].id);
                    } else if (!conversationId) {
                        await startNewChat();
                    }
                } catch (error) {
                    console.error('Conversation list error:', error);
                }
            }

            function renderConversation(conversation) {
                conversationId = conversation.id;
                chatHistory = [];
                const box = document.getElementById('chatContainer');
                box.innerHTML = '';
                (conversation.messages || []).forEach((message) => {
                    appendMsg(message.content, message.role === 'user' ? 'user' : 'bot');
                    if (message.role === 'user') chatHistory.push([message.content, '']);
                    else if (chatHistory.length) chatHistory[chatHistory.length - 1][1] = message.content;
                });
                if (!conversation.messages?.length) {
                    appendMsg('System initialized and running locally. Ask for code, Linux help, or hardware control.', 'bot');
                }
                chatHistory = chatHistory.filter((pair) => pair[0] && pair[1]).slice(-3);
            }

            async function openConversation(id) {
                if (isGenerating) return;
                const response = await fetch(`/api/conversations/${encodeURIComponent(id)}`);
                if (!response.ok) return;
                const conversation = await response.json();
                if (conversation.status === 'error') return;
                renderConversation(conversation);
                const listResponse = await fetch('/api/conversations');
                renderConversationList((await listResponse.json()).conversations || []);
            }

            async function startNewChat() {
                if (isGenerating) return;
                const response = await fetch('/api/conversations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: 'New chat' })
                });
                if (!response.ok) return;
                const conversation = await response.json();
                renderConversation(conversation);
                const listResponse = await fetch('/api/conversations');
                renderConversationList((await listResponse.json()).conversations || []);
            }

            function setCurrentTrack(title, folder = mediaDirectory) {
                const trackLabel = document.getElementById('currentTrackLabel');
                const folderLabel = document.getElementById('musicFolderLabel');
                const musicCard = document.querySelector('.music-card');
                const isPlaying = !!(title && title !== 'No track playing');

                if (trackLabel) trackLabel.textContent = title || 'No track playing';
                if (folderLabel) folderLabel.textContent = folder || mediaDirectory;

                if (musicCard) {
                    musicCard.classList.toggle('hidden', !isPlaying);
                }
            }

            function toggleSidebar() {
                const sidebar = document.getElementById('sidebar');
                if (!sidebar) return;

                if (window.matchMedia('(max-width: 760px)').matches) {
                    sidebar.classList.remove('collapsed', 'mobile-open', 'is-animating');
                    return;
                }

                const shouldCollapse = !sidebar.classList.contains('collapsed');
                sidebar.classList.add('is-animating');

                const finishAnimation = (event) => {
                    if (event.propertyName !== 'width') return;
                    sidebar.classList.remove('is-animating');
                    sidebar.removeEventListener('transitionend', finishAnimation);
                };

                sidebar.addEventListener('transitionend', finishAnimation);

                if (shouldCollapse) {
                    // Hide labels first, then begin the rail-width transition.
                    requestAnimationFrame(() => {
                        sidebar.classList.add('collapsed');
                    });
                } else {
                    // Start expanding immediately; labels return after width settles.
                    sidebar.classList.remove('collapsed');
                }
            }

            function toggleQuickActions() {
                const actions = document.querySelector('.quick-actions');
                const toggle = document.getElementById('quickActionsToggle');
                if (!actions || !toggle) return;

                const isOpen = actions.classList.toggle('open');
                toggle.setAttribute('aria-expanded', String(isOpen));
            }

            document.addEventListener('DOMContentLoaded', function () {
                const toggleBtn = document.getElementById('sidebarToggle');
                if (toggleBtn) {
                    toggleBtn.addEventListener('click', toggleSidebar);
                }

                const quickActionsToggle = document.getElementById('quickActionsToggle');
                if (quickActionsToggle) {
                    quickActionsToggle.addEventListener('click', toggleQuickActions);
                }

                document.querySelectorAll('.chip').forEach((chip) => {
                    chip.addEventListener('click', function () {
                        const action = this.dataset.action;
                        if (!action) return;
                        toggleQuickActions();
                        sendQuickAction(action);
                    });
                });

                setCurrentTrack('No track playing');
                loadRuntimeStatus();
                loadConversations();
                window.setInterval(pollProactiveMessage, 60000);
            });

            async function loadRuntimeStatus() {
                const statusLabel = document.getElementById('statusLabel');
                const statusDot = document.getElementById('statusDot');
                const mode = document.getElementById('runtimeMode');
                const hardware = document.getElementById('runtimeHardware');
                const safety = document.getElementById('runtimeSafety');
                const latency = document.getElementById('runtimeLatency');

                try {
                    const response = await fetch('/api/status');
                    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                    const data = await response.json();
                    applyPersona(data);
                    mediaDirectory = data.media_directory || mediaDirectory;
                    const ready = data.status === 'ready';
                    if (statusLabel) statusLabel.textContent = ready ? `${data.persona_name || 'Local AI'} ready` : 'Starting local AI';
                    if (statusDot) statusDot.style.background = ready ? '#37d67a' : '#f5b94a';
                    if (mode) mode.textContent = data.mode || 'unknown';
                    if (hardware) hardware.textContent = data.raspberry_pi ? 'Raspberry Pi' : 'Local host';
                    if (safety) safety.textContent = data.safe_execution ? 'Safe local mode' : 'Disabled';
                    if (latency) latency.textContent = data.metrics?.average_latency_ms ? `${Math.round(data.metrics.average_latency_ms)} ms avg` : 'No requests';
                } catch (error) {
                    if (statusLabel) statusLabel.textContent = 'Status unavailable';
                    if (statusDot) statusDot.style.background = '#e06b75';
                    if (mode) mode.textContent = 'unknown';
                    if (safety) safety.textContent = 'Unknown';
                    console.error('Runtime status error:', error);
                }
            }

            async function sendQuickAction(action) {
                if (isGenerating) return;

                const inputEl = document.getElementById('userInput');
                const sendBtn = document.getElementById('sendBtn');
                const actionMap = {
                    MUSIC_ON: 'play music',
                    MUSIC_STOP: 'stop music',
                    LED_ON: 'turn on the lights',
                    LED_OFF: 'turn off the lights'
                };

                const query = actionMap[action] || action;
                appendMsg(query, 'user');
                inputEl.value = '';
                inputEl.style.height = 'auto';

                isGenerating = true;
                inputEl.disabled = true;
                sendBtn.disabled = true;

                const { msgContentEl } = appendMsg('', 'bot');
                msgContentEl.innerHTML = '<span class="cursor"></span>';

                try {
                    const res = await fetch('/api/robot', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ query, history: chatHistory, conversation_id: conversationId })
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
                            if (!line.startsWith('data: ')) continue;
                            const rawJson = line.replace('data: ', '').trim();
                            if (!rawJson) continue;

                            try {
                                const parsed = JSON.parse(rawJson);
                                if (parsed.delta) appendBotDelta(msgContentEl, parsed.delta);
                                if (parsed.history) chatHistory = parsed.history;
                                if (parsed.conversation_id) conversationId = parsed.conversation_id;
                                if (parsed.response !== undefined) updateBotMsg(msgContentEl, parsed.response, parsed.hardware_cmd || 'NONE');

                                if (parsed.hardware_cmd === 'MUSIC_ON' || parsed.hardware_cmd === 'MUSIC_SHUFFLE' || parsed.hardware_cmd === 'MUSIC_NEXT') {
                                    setCurrentTrack('Playing local music');
                                } else if (parsed.hardware_cmd === 'MUSIC_STOP') {
                                    setCurrentTrack('No track playing');
                                }
                            } catch (err) {
                                console.error('JSON parse error:', err);
                            }
                        }
                    }
                } catch (e) {
                    console.error('Quick action error:', e);
                    updateBotMsg(msgContentEl, 'Command failed locally. Please try again.', 'NONE');
                } finally {
                    isGenerating = false;
                    inputEl.disabled = false;
                    sendBtn.disabled = false;
                    inputEl.focus();
                }
            }

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

            async function toggleVoiceInput() {
                const voiceBtn = document.getElementById('voiceBtn');
                if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
                    alert('This browser does not support local microphone recording.');
                    return;
                }
                if (voiceRecorder && voiceRecorder.state === 'recording') {
                    voiceRecorder.stop();
                    voiceBtn.classList.remove('recording');
                    voiceBtn.title = 'Speak to assistant';
                    return;
                }

                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    voiceChunks = [];
                    voiceRecorder = new MediaRecorder(stream);
                    voiceRecorder.ondataavailable = (event) => {
                        if (event.data.size) voiceChunks.push(event.data);
                    };
                    voiceRecorder.onstop = async () => {
                        stream.getTracks().forEach((track) => track.stop());
                        voiceBtn.disabled = true;
                        voiceBtn.title = 'Transcribing locally...';
                        try {
                            const response = await fetch('/api/voice/transcribe', {
                                method: 'POST',
                                headers: { 'Content-Type': voiceRecorder.mimeType || 'audio/webm' },
                                body: new Blob(voiceChunks, { type: voiceRecorder.mimeType || 'audio/webm' })
                            });
                            const data = await response.json();
                            if (data.status !== 'ok') throw new Error(data.message || 'Voice transcription failed');
                            const input = document.getElementById('userInput');
                            input.value = data.text || '';
                            autoResize(input);
                            if (input.value.trim()) sendMsg();
                        } catch (error) {
                            console.error('Voice input error:', error);
                            alert(error.message || 'Local voice transcription failed.');
                        } finally {
                            voiceBtn.disabled = false;
                            voiceBtn.title = 'Speak to assistant';
                        }
                    };
                    voiceRecorder.start();
                    voiceBtn.classList.add('recording');
                    voiceBtn.title = 'Stop recording';
                } catch (error) {
                    console.error('Microphone access error:', error);
                    alert('Microphone access was not granted.');
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
                            history: chatHistory,
                            conversation_id: conversationId
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
                                    
                                    if (parsed.delta) appendBotDelta(msgContentEl, parsed.delta);
                                    if (parsed.history) {
                                        chatHistory = parsed.history;
                                    }
                                    if (parsed.conversation_id) conversationId = parsed.conversation_id;

                                    if (parsed.response !== undefined) updateBotMsg(msgContentEl, parsed.response, parsed.hardware_cmd || "NONE");
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
                startNewChat();
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
                if (sender === 'user') {
                    avatar.textContent = 'U';
                } else {
                    const personaName = document.getElementById('headerPersonaName')?.textContent || 'AI';
                    avatar.textContent = personaName.slice(0, 2).toUpperCase();
                }

                const msgContent = document.createElement('div');
                msgContent.className = 'msg-content';

                if (sender === 'user') {
                    msgContent.innerText = text;
                } else {
                    msgContent.innerHTML = parseMarkdown(text);
                }

                if (sender === 'user') {
                    wrapper.appendChild(msgContent);
                    wrapper.appendChild(avatar);
                } else {
                    wrapper.appendChild(avatar);
                    wrapper.appendChild(msgContent);
                }

                container.appendChild(wrapper);

                chatBox.scrollTop = chatBox.scrollHeight;
                return { wrapper, msgContentEl: msgContent };
            }

            function updateBotMsg(element, text, hwCmd = "NONE") {
                const chatBox = document.getElementById('chatBox');
                element.dataset.streamText = '';
                element.innerHTML = parseMarkdown(text);

                if (hwCmd !== "NONE") {
                    const tag = document.createElement('div');
                    tag.className = 'hardware-tag';
                    tag.innerHTML = `Action: <strong>${hwCmd}</strong>`;
                    element.appendChild(tag);
                }

                chatBox.scrollTop = chatBox.scrollHeight;
            }

            function appendBotDelta(element, delta) {
                const chatBox = document.getElementById('chatBox');
                element.dataset.streamText = (element.dataset.streamText || '') + delta;
                element.innerHTML = parseMarkdown(element.dataset.streamText) + '<span class="cursor"></span>';
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        </script>
    </body>
    </html>
    """