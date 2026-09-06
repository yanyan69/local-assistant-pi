# robot.py
import re
from typing import Dict, Any, Tuple, List, Optional

# --- UTILITIES IMPORT (SEARCH ENGINE FALLBACK) ---
try:
    from utilities.search_engine import OfflineSearchEngine
    search_engine = OfflineSearchEngine()
except Exception:
    # If search_engine.py is missing, server.py will supply its SQLite FTS5 search
    search_engine = None


# --- DYNAMIC PERSONA IMPORT WITH FALLBACK ---
DEFAULT_PERSONA = {
    "casual": (
        "You are a friendly, helpful offline robot assistant running locally on Raspberry Pi hardware. "
        "Respond naturally, concisely, and directly. Keep it under 2 sentences."
    ),
    "code": (
        "You are an expert programming assistant. "
        "Write clean, functional code matching the user's prompt. "
        "Wrap code blocks in standard Markdown fences. Keep verbal commentary short."
    ),
    "rag": (
        "You are a precise, highly efficient Linux and sysadmin assistant running locally on a Raspberry Pi.\n\n"
        "Core Directives:\n"
        "1. ACCURACY FIRST: Provide technically accurate Linux commands.\n"
        "2. CONCISE & DIRECT: Give exact, ready-to-use terminal commands immediately.\n"
        "3. GROUNDED REASONING: Use provided Context if available. Otherwise, rely on core Linux best practices."
    )
}

try:
    import persona
    SYSTEM_PROMPTS = getattr(persona, "SYSTEM_PROMPTS", DEFAULT_PERSONA)
    robot_name = getattr(persona, "ROBOT_NAME", "Robot")
    print(f"[SYSTEM INFO]: Loaded custom persona '{robot_name}' from persona.py")
except Exception as e:
    SYSTEM_PROMPTS = DEFAULT_PERSONA
    print(f"[WARNING]: Could not load persona.py ({e}). Using default robot persona.")


# --- PRE-COMPILED REGEX PATTERNS ---
BAD_WORDS_RE = re.compile(
    r'\b(fuck|fucking|fucked|slave|bitch|shit|damn)\b', 
    re.IGNORECASE
)

CLEAN_TAGS_RE = re.compile(
    r'^(assistant|system|user)\s*', 
    re.IGNORECASE
)

CASUAL_REGEX = re.compile(
    r'^(h+i+|h+e+l+o+|h+e+y+|greetings|thanks|thank\s+you|cool|ok|okay|who\s+are\s+you|who\s+am\s+i|your\s+name|my\s+name|you\s+are|you\'re|nice|awesome|great)(\s+.*)?$',
    re.IGNORECASE
)

CASUAL_PHRASES = {
    "good boy", "good girl", "what", "see", "huh", "yeah", "yep", "nah", 
    "nice", "bro", "dude", "really", "wow", "lol", "lmao", "haahaha", "hahaha"
}

CONVERSATIONAL_EXCLUSIONS = {
    "what", "see", "how", "why", "who", "yes", "no", "okay", "bro", "dude", 
    "huh", "yeah", "yep", "nah", "boy", "girl"
}

# --- EXPANDED HARDWARE & MEDIA INTENT PATTERNS ---
HARDWARE_PATTERNS = {
    "LED_ON": re.compile(
        r'\b(turn|switch|power|put)\b.*\b(on)\b.*\b(light|lights|led)\b|\b(light|lights|led)\b.*\b(on)\b',
        re.IGNORECASE
    ),
    "LED_OFF": re.compile(
        r'\b(turn|switch|power|put)\b.*\b(off)\b.*\b(light|lights|led)\b|\b(light|lights|led)\b.*\b(off)\b',
        re.IGNORECASE
    ),
    "MUSIC_ON": re.compile(
        r'\b(music\s+on|play\s+music|start\b.*\bmusic|turn\s+on\b.*\bmusic)\b|\b(music)\b.*\b(on|play|start)\b',
        re.IGNORECASE
    ),
    "MUSIC_SHUFFLE": re.compile(
        r'\b(play|shuffle|start|resume)\b.*\b(music|song|songs|tracks|playlist)\b|\b(play|shuffle)\b$',
        re.IGNORECASE
    ),
    "MUSIC_NEXT": re.compile(
        r'\b(next|skip)\b.*\b(song|track|music)\b|\b(next|skip)\b$',
        re.IGNORECASE
    ),
    "MUSIC_STOP": re.compile(
        r'\b(stop|pause|halt|turn\s+off|switch\s+off|shut\s+off|turn\s+it\s+off|kill|off)\b.*\b(music|song|playing|audio|track)\b|\b(music|song|playing|audio)\b.*\b(stop|off)\b|^\s*(stop|pause|shut\s+up)\s*$',
        re.IGNORECASE
    ),
    "SYS_TEMP": re.compile(
        r'\b(cpu\s+temp|pi\s+temp|temperature|check\s+temp|system\s+temp)\b',
        re.IGNORECASE
    )
}

CONVERSATIONAL_STOP_WORDS = {
    "nice", "cool", "great", "awesome", "please", "teach", "me", "about", 
    "tell", "explain", "what", "is", "can", "you", "show", "give", "info", "do",
    "good", "boy", "girl", "now", "hey", "bro", "thanks", "thank"
}

CODE_TRIGGERS = {"code", "script", "program", "function", "write", "python", "cpp", "c++", "bug", "fix"}


def default_search_database(query_str: str) -> str:
    """Fallback search query function if server.py doesn't pass SQLite search."""
    if search_engine:
        return search_engine.query(query_str, top_k=2)
    return ""


def sanitize_input(text: str) -> str:
    text = BAD_WORDS_RE.sub("", text)
    text = re.sub(r'<\|.*?\|>', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def clean_search_query(user_query: str) -> str:
    tokens = re.findall(r'\w+', user_query.lower())
    meaningful_tokens = [t for t in tokens if t not in CONVERSATIONAL_STOP_WORDS and len(t) > 2]
    
    if not meaningful_tokens:
        meaningful_tokens = [t for t in tokens if len(t) > 2]

    base_query = " ".join(meaningful_tokens)

    if len(meaningful_tokens) == 1 and base_query and base_query not in CONVERSATIONAL_EXCLUSIONS:
        return f"{base_query} command usage explanation"
        
    return base_query or user_query


def detect_hardware_intent(query: str) -> Optional[Tuple[str, str]]:
    """Detects hardware/media commands and returns (hardware_cmd_key, spoken_response_text)."""
    for cmd, pattern in HARDWARE_PATTERNS.items():
        if pattern.search(query):
            responses = {
                "LED_ON": "Turning the lights on.",
                "LED_OFF": "Switching the lights off.",
                "MUSIC_ON": "Starting music playback.",
                "MUSIC_SHUFFLE": "Shuffling and playing your music.",
                "MUSIC_NEXT": "Skipping to the next track.",
                "MUSIC_STOP": "Stopping music playback.",
                "SYS_TEMP": "Checking system temperature."
            }
            return cmd, responses.get(cmd, "Command recognized.")
    return None


def build_llama3_prompt(system_prompt: str, context: str, history: List[Tuple[str, str]], query: str) -> str:
    prompt = f"<|start_header_id|>system<|end_header_id|>\n\n{system_prompt}"
    
    if context:
        prompt += f"\n\nContext Information:\n{context[:1800]}"
    
    prompt += "<|eot_id|>"

    for old_user, old_bot in history[-2:]:
        prompt += (
            f"<|start_header_id|>user<|end_header_id|>\n\n{old_user}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n\n{old_bot}<|eot_id|>"
        )

    prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{query}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
    return prompt


def process_robot_request(data: Dict[str, Any], llm: Any, search_database: Any = None) -> Tuple[Dict[str, Any], int]:
    if not data or "query" not in data:
        return {"error": "Missing 'query' field"}, 400

    if search_database is None:
        search_database = default_search_database

    raw_query = data["query"]
    user_query = sanitize_input(raw_query)
    client_history = data.get("history", [])

    print(f"\n[Incoming Request]: {user_query}")

    # ROUTE 1: Memory Reset
    if any(cmd in user_query.lower() for cmd in ["clear memory", "reset chat", "clear chat"]):
        print("[SYSTEM INFO]: Memory reset triggered.")
        return {
            "response": "Memory reset! What would you like to talk about next?",
            "hardware_cmd": "NONE",
            "history": []
        }, 200

    # ROUTE 2: Hardware & Media Control
    hw_match = detect_hardware_intent(user_query)
    if hw_match:
        cmd_key, action_text = hw_match
        print(f"[HARDWARE ACTION DETECTED]: Triggering intent -> {cmd_key}")
        return {
            "response": action_text,
            "hardware_cmd": cmd_key,
            "history": client_history
        }, 200
    if any(p in user_query.lower() for p in ["what can you do", "list commands", "help me", "your commands", "available commands"]):
        return {
            "response": (
                "I'm your offline Pi assistant! Here's what you can ask me:\n"
                "- Hardware: 'Turn on the lights', 'Stop music', 'Next song'\n"
                "- Programming: Ask me to write or debug Python/C++ code\n"
                "- Linux/Sysadmin: Ask about terminal commands (e.g., 'How do I use rsync?')\n"
                "- System: 'Clear memory' to reset chat history"
            ),
            "hardware_cmd": "NONE",
            "history": client_history
        }, 200

    # ROUTE 3: Context & Intent Routing
    query_lower = user_query.lower()
    words = query_lower.split()
    
    TECHNICAL_KEYWORDS = {
        "how", "what", "why", "where", "when", "which", "who", "explain", "describe",
        "linux", "python", "code", "script", "command", "terminal", "install", "config",
        "error", "bug", "run", "sudo", "apt", "pip", "git", "docker", "ls", "grep",
        "cat", "chmod", "chown", "systemctl", "journalctl", "service", "rsync", "ssh"
    }

    has_technical_intent = any(w in query_lower for w in TECHNICAL_KEYWORDS) or any(trig in query_lower for trig in CODE_TRIGGERS)
    
    is_casual = (
        not has_technical_intent
        or bool(CASUAL_REGEX.match(query_lower))
        or query_lower in CASUAL_PHRASES
    )

    retrieved_data = ""
    
    if is_casual or not user_query:
        print("[CONTEXT ROUTER]: Casual conversation detected.")
        token_limit = 100
        system_instructions = SYSTEM_PROMPTS.get("casual", DEFAULT_PERSONA["casual"])

    elif any(trig in query_lower for trig in CODE_TRIGGERS):
        print("[CONTEXT ROUTER]: Technical/Code generation detected.")
        token_limit = 450
        search_target = clean_search_query(user_query)
        retrieved_data = search_database(search_target)
        system_instructions = SYSTEM_PROMPTS.get("code", DEFAULT_PERSONA["code"])

    else:
        print("[CONTEXT ROUTER]: Standard RAG query detected.")
        token_limit = 250
        search_target = clean_search_query(user_query)
        print(f"[SEARCH TARGET]: Extracted '{search_target}' from raw query '{user_query}'")
        
        retrieved_data = search_database(search_target)
        
        # Filter out empty or non-match search responses
        no_match_phrases = [
            "No highly relevant text matches", 
            "No local document records", 
            "No clear search query detected",
            "Knowledge search error"
        ]
        if any(msg in retrieved_data for msg in no_match_phrases):
            retrieved_data = ""

        system_instructions = SYSTEM_PROMPTS.get("rag", DEFAULT_PERSONA["rag"])

    # PROMPT EXECUTION
    formatted_prompt = build_llama3_prompt(
        system_instructions, 
        retrieved_data, 
        client_history, 
        user_query
    )

    output = llm(
        formatted_prompt,
        max_tokens=token_limit,
        temperature=0.2,
        top_p=0.9,
        stop=[
            "<|eot_id|>",
            "<|start_header_id|>",
            "<|end_header_id|>",
            "User:",
            "user:"
        ],
        repeat_penalty=1.15
    )

    ai_response = output["choices"][0]["text"].strip()
    ai_response = CLEAN_TAGS_RE.sub('', ai_response).strip()

    updated_history = (client_history + [(user_query, ai_response)])[-3:]

    print(f"[AI Reply]: {ai_response}")

    return {
        "response": ai_response,
        "hardware_cmd": "NONE",
        "history": updated_history
    }, 200