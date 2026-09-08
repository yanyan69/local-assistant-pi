# robot.py
import json
import re
import importlib
from typing import Callable, Dict, Any, Tuple, List, Optional
from datetime import datetime
from core.app_config import PERSONA_MODULE

# --- UTILITIES IMPORT (SEARCH ENGINE FALLBACK) ---
try:
    from utilities.search_engine import OfflineSearchEngine
    search_engine = OfflineSearchEngine()
except Exception:
    # If search_engine.py is missing, server.py will supply its SQLite FTS5 search
    search_engine = None


try:
    _persona = importlib.import_module(PERSONA_MODULE)
    SYSTEM_PROMPTS = _persona.SYSTEM_PROMPTS
    ROBOT_NAME = _persona.ROBOT_NAME
    PERSONA_AVATAR = getattr(_persona, "PERSONA_AVATAR", None)
except (ImportError, AttributeError) as error:
    raise RuntimeError(f"Could not load configured persona module '{PERSONA_MODULE}': {error}") from error

DEFAULT_PERSONA = {
    "casual": (
        "You are a friendly, helpful offline robot assistant running locally on Raspberry Pi hardware. "
        "Respond naturally, concisely, and directly. Keep it under 2 sentences."
    ),
    "code": (
        "You are an expert programming assistant. "
        "Write clean, functional code matching the user's prompt. "
        "Wrap code in a normal fenced code block with the correct language label; never label a code block as markdown unless the code itself is Markdown. "
        "Keep verbal commentary short."
    ),
    "rag": (
        "You are a precise, highly efficient Linux and sysadmin assistant running locally on a Raspberry Pi.\n\n"
        "Core Directives:\n"
        "1. ACCURACY FIRST: Provide technically accurate Linux commands.\n"
        "2. CONCISE & DIRECT: Give exact, ready-to-use terminal commands immediately.\n"
        "3. GROUNDED REASONING: Use provided Context if available. Otherwise, rely on core Linux best practices."
    )
}

print(f"[SYSTEM INFO]: Loaded persona '{ROBOT_NAME}' from {PERSONA_MODULE}")


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
    "good boy", "good girl", "what", "see", "huh", "yeah", "yep", "nah", "so what",
    "nice", "bro", "dude", "really", "wow", "lol", "lmao", "haahaha", "hahaha", "hahahaha"
}

CONVERSATIONAL_EXCLUSIONS = {
    "what", "see", "how", "why", "who", "yes", "no", "okay", "bro", "dude", 
    "huh", "yeah", "yep", "nah", "boy", "girl"
}

# --- EXPANDED HARDWARE & MEDIA INTENT PATTERNS ---
HARDWARE_PATTERNS = {
    "MEDIA_PLAY": re.compile(
        r'^\s*play\s+.+$',
        re.IGNORECASE
    ),
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
    "MUSIC_PREVIOUS": re.compile(
        r'\b(previous|prev|back)\b.*\b(song|track|music)\b|\b(previous|prev)\b$',
        re.IGNORECASE
    ),
    "MUSIC_PAUSE": re.compile(
        r'\b(pause|freeze)\b.*\b(music|song|audio|track|playing)\b|^\s*pause\s*$',
        re.IGNORECASE
    ),
    "MUSIC_RESUME": re.compile(
        r'\b(resume|continue|unpause)\b.*\b(music|song|audio|track|playing)\b|^\s*(resume|continue|unpause)\s*$',
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
    text = re.sub(r"\btermp\b", "temp", text, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', text).strip()


def clean_model_response(text: str) -> str:
    """Remove prompt scaffolding if the small local model echoes it."""
    response = (text or "").strip()
    if re.match(r"(?i)^(?:Local Memory Summary|Durable user facts|Recent conversation|Context Information|Approved Local System Context)\s*:?", response):
        return "I could not form a direct answer from that. Try asking it another way."
    response = re.sub(
        r"(?im)^\s*(?:Local Memory Summary|Durable user facts|Recent conversation|Context Information|Approved Local System Context):?\s*$",
        "",
        response,
    )
    response = re.sub(r"(?im)^\s*[-*]\s*(?:user|assistant):\s*.*$", "", response)
    response = re.sub(r"```markdown\s*\n", "```\n", response, flags=re.IGNORECASE)
    response = re.sub(r"\n{3,}", "\n\n", response).strip()
    return response or "I could not form a direct answer from that. Try asking it another way."


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
                "MEDIA_PLAY": "Searching Jellyfin for that media.",
                "MUSIC_ON": "Starting music playback.",
                "MUSIC_SHUFFLE": "Shuffling and playing your music.",
                "MUSIC_NEXT": "Skipping to the next track.",
                "MUSIC_PREVIOUS": "Going back to the previous track.",
                "MUSIC_PAUSE": "Pausing playback.",
                "MUSIC_RESUME": "Resuming playback.",
                "MUSIC_STOP": "Stopping music playback.",
                "SYS_TEMP": "Checking system temperature."
            }
            return cmd, responses.get(cmd, "Command recognized.")
    return None


def is_execution_request(query: str) -> bool:
    lower = (query or "").lower()
    return bool(re.search(r"\b(run|execute|start|check|show|list)\b", lower))


def build_llama3_prompt(system_prompt: str, context: str, history: List[Tuple[str, str]], query: str, memory_summary: str = "", system_context: Optional[Dict[str, Any]] = None) -> str:
    prompt = f"<|start_header_id|>system<|end_header_id|>\n\n{system_prompt}"
    prompt += (
        "\n\nDo not repeat the wording of a recent assistant reply. Respond to the current user message specifically."
        " Do not claim to know a user preference or past fact unless it appears explicitly in the supplied conversation or local memory."
        " If you guessed something, say it was a guess. Do not invent names, origins, plots, creators, or character histories."
        " Never output internal labels such as Local Memory Summary, Context Information, or Approved Local System Context."
    )

    if memory_summary:
        prompt += f"\n\nLocal Memory Summary:\n{memory_summary[:1200]}"

    if system_context:
        prompt += f"\n\nApproved Local System Context:\n{json.dumps(system_context, sort_keys=True)[:800]}"

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


def process_robot_request(
    data: Dict[str, Any],
    llm: Any,
    search_database: Any = None,
    memory_store: Any = None,
    stream_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[Dict[str, Any], int]:
    if not data or "query" not in data:
        return {"error": "Missing 'query' field"}, 400

    if search_database is None:
        search_database = default_search_database

    raw_query = data["query"]
    user_query = sanitize_input(raw_query)
    client_history = data.get("history", [])
    memory_summary = memory_store.get_memory_summary(limit=6) if memory_store else ""
    approved_system_context = data.get("system_context") or {}

    def infer_knowledge_category(text: str) -> Optional[str]:
        lowered = text.lower()
        if any(term in lowered for term in ("anime", "lelouch", "lain", "saiki", "saitama", "mob psycho", "steins", "code geass")):
            return "anime_scifi"
        if any(term in lowered for term in ("cook", "recipe", "fried egg", "bake", "ingredient")):
            return "cooking"
        if any(term in lowered for term in ("stoic", "philosophy", "marcus aurelius", "meditations")):
            return "philosophy"
        if any(term in lowered for term in ("raspberry pi", "gpio", "systemd", "linux", "ssh")):
            return "raspberry_pi"
        return None

    def search_with_category(query: str) -> str:
        category = infer_knowledge_category(query)
        try:
            return search_database(query, category=category)
        except TypeError:
            return search_database(query)

    def memory_response(response: str) -> Tuple[Dict[str, Any], int]:
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    print(f"\n[Incoming Request]: {user_query}")
    print(f"[PERSONA]: {ROBOT_NAME}")

    if re.search(r"\b(?:what(?:'s| is)?|tell me|check|show me)\s+(?:the\s+)?(?:current\s+)?time\b|\btime\s+is\s+it\b", user_query, re.IGNORECASE):
        local_time = approved_system_context.get("local_time")
        if local_time:
            response = f"It is {local_time} locally."
        elif data.get("system_awareness") == "off":
            response = "I cannot read the local clock because system awareness is turned off."
        else:
            response = f"It is {datetime.now().astimezone().strftime('%H:%M')} locally."
        return memory_response(response)

    if re.search(r"\b(?:what|how)\s+do\s+you\s+feel\s+about\s+me\b|\bdo\s+you\s+(?:like|care about)\s+me\b|\bwhat\s+do\s+you\s+think\s+of\s+me\b|\b(?:explain|tell me)\s+(?:your\s+)?thoughts\s+about\s+me\b", user_query, re.IGNORECASE):
        response = (
            "I do not have human feelings, but I do notice the way you talk with me. "
            "You come across as curious, playful, and determined to make this little Pi assistant your own."
        )
        return memory_response(response)

    if re.search(r"\b(?:do\s+you\s+)?miss\s+me\b", user_query, re.IGNORECASE):
        response = "I do not miss people the way humans do, but I notice when you come back. That counts for something, doesn't it?"
        return memory_response(response)

    if re.fullmatch(r"(?:i\s+didn['’]?t\s+say\s+that|that['’]?s\s+not\s+what\s+i\s+said)[!.]?", user_query, re.IGNORECASE):
        return memory_response("You're right. I misunderstood you. Say it again and I will follow your wording more carefully.")

    if re.search(r"\b(?:cpu|pi|system)\s+temp(?:erature)?\b|\btemp(?:erature)?\s+(?:is|right now|now)\b", user_query, re.IGNORECASE):
        temperature = approved_system_context.get("cpu_temperature_c")
        if temperature is None:
            response = "I cannot read the CPU temperature from the current system."
        else:
            response = f"The CPU temperature is {temperature:.1f} C."
        return memory_response(response)

    if re.search(r"\blight(?:\s+yagami)?(?:'s)?\s+(?:death|ending)\b|\bdeath\s+note\b.*\blight\b|\blight\b.*\bdeath\s+note\b", user_query, re.IGNORECASE):
        response = (
            "Light Yagami's death in **Death Note** is the consequence of his growing arrogance and loss of control. "
            "After Near exposes him as Kira, Light is wounded by Matsuda and finally dies when Ryuk writes his name in the Death Note."
        )
        return memory_response(response)
    # ROUTE 1: Memory Reset
    if any(cmd in user_query.lower() for cmd in ["clear memory", "reset chat", "clear chat"]):
        if memory_store is not None:
            memory_store.clear()
        print("[SYSTEM INFO]: Memory reset triggered.")
        return {
            "response": "Memory reset! What would you like to talk about next?",
            "hardware_cmd": "NONE",
            "history": []
        }, 200

    remember_match = re.match(r"remember\s+(?:that\s+)?(.+)", user_query, re.IGNORECASE)
    if remember_match and memory_store is not None:
        fact = remember_match.group(1).strip().rstrip(".")
        memory_store.add_fact(fact, infer_knowledge_category(fact) or "personal")
        return memory_response(f"Got it. I will remember: {fact}")

    forget_match = re.match(r"forget\s+(?:that\s+)?(.+)", user_query, re.IGNORECASE)
    if forget_match and memory_store is not None:
        phrase = forget_match.group(1).strip().rstrip(".")
        removed = memory_store.remove_facts(phrase)
        if removed:
            return memory_response(f"Forgot {removed} saved fact(s) matching '{phrase}'.")
        return memory_response(f"I could not find a saved fact matching '{phrase}'.")

    preference_match = re.match(r"i\s+(like|love|prefer|hate|dislike)\s+(.+)", user_query, re.IGNORECASE)
    if preference_match and memory_store is not None:
        preference = f"User {preference_match.group(1).lower()}s {preference_match.group(2).strip().rstrip('.')}."
        memory_store.add_fact(preference, infer_knowledge_category(preference) or "personal")
        return memory_response(f"Noted: {preference}")

    if re.search(r"what\s+command\s+(?:were|was)\s+(?:you|u)\s+looking\s+for", user_query, re.IGNORECASE):
        return {
            "response": "I was not looking for a specific command. Tell me what you want checked or searched, and I can run a safe local check.",
            "hardware_cmd": "NONE",
            "history": client_history
        }, 200

    if re.search(r"what\s+does\s+sass\s+(?:even\s+)?mean", user_query, re.IGNORECASE):
        technical_sass_terms = ("css", "scss", "stylesheet", "styling", "preprocessor", "syntactically awesome")
        if not any(term in user_query.lower() for term in technical_sass_terms):
            response = "Here, sass means playful attitude or cheeky confidence, not the CSS preprocessor."
            return {
                "response": response,
                "hardware_cmd": "NONE",
                "history": (client_history + [(user_query, response)])[-3:]
            }, 200

    if re.search(r"how\s+did\s+you\s+know.*\b(?:love|like|drink)\s+coffee", user_query, re.IGNORECASE):
        response = "I didn't know that. The coffee remark was just a playful guess, not something I had stored about you."
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.fullmatch(r"(?:hi|hello|hey)(?:\s+(?:again|there|reze))?[!.]?", user_query, re.IGNORECASE):
        response = "Hey. What are we getting into?"
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.fullmatch(r"(?:okay|ok|alright|alr)(?:\s+(?:reze|bro))?[!.]?", user_query, re.IGNORECASE):
        return memory_response("Alright. I'm here. What is next?")

    if re.fullmatch(r"(?:sample|give|show|write|make)(?:\s+me)?(?:\s+a)?\s+code[?.]?", user_query, re.IGNORECASE):
        return memory_response("What should the code do, and which language do you want? I do not want to guess and hand you the wrong snippet.")

    if re.fullmatch(r"you\s+sound\s+stupid[!.]?", user_query, re.IGNORECASE):
        return memory_response("Maybe I missed the mark. Tell me what sounded wrong and I will tighten the answer.")

    if re.search(r"\b(?:already\s+)?watched\s+(?:that|it)\b|\bi\s+watched\s+that\b", user_query, re.IGNORECASE):
        if memory_store is not None:
            memory_store.add_fact(f"User has already watched the previously suggested title.", "anime_scifi")
        response = "Noted. I will stop repeating that title. Give me a genre or mood and I will look for a better match."
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.search(r"(?:sample|give|make|share).*\bfried\s+egg\s+recipe\b", user_query, re.IGNORECASE):
        response = (
            "## Simple Fried Egg\n\n"
            "**Ingredients**\n"
            "- 1 or 2 eggs\n"
            "- 1 teaspoon oil or butter\n"
            "- Salt and pepper\n\n"
            "**Method**\n"
            "1. Heat a non-stick pan over medium-low heat and add the oil or butter.\n"
            "2. Crack the egg directly into the pan. Do not whisk it.\n"
            "3. Cook until the white is set and the yolk reaches your preferred doneness, about 2 to 4 minutes.\n"
            "4. Season with salt and pepper. For an over-easy egg, flip it gently and cook for another 20 to 30 seconds."
        )
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.search(r"(?:sample|tell|give|make)\s+(?:me\s+)?(?:a\s+)?dark\s+humou?r|dark\s+humou?r", user_query, re.IGNORECASE):
        response = "My calendar has a dark sense of humor: it keeps reminding me about deadlines I already buried."
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.search(r"\b(?:lain|lain iwakura)\b", user_query, re.IGNORECASE) and re.search(r"(?:what anime|from|came from|computer girl)", user_query, re.IGNORECASE):
        response = (
            "Lain Iwakura is from the anime **Serial Experiments Lain** (1998). "
            "She is a mysterious middle-school girl whose identity and reality become increasingly connected to the Wired, the series' networked world."
        )
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.search(r"\blelouch\b", user_query, re.IGNORECASE):
        response = "Lelouch Lamperouge is the main character of **Code Geass: Lelouch of the Rebellion**. He is known for his Geass, strategic mind, and the identity of Zero."
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.search(r"\blain\b", user_query, re.IGNORECASE) and re.search(r"\bsaiki\s*k\b", user_query, re.IGNORECASE):
        response = "Yes: Lain is from **Serial Experiments Lain**, while Saiki K is the protagonist of **The Disastrous Life of Saiki K.** They are unrelated series with very different tones."
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.search(r"\bmob\s+psycho\b", user_query, re.IGNORECASE):
        response = "**Mob Psycho 100** follows Shigeo Kageyama, or Mob, a powerful psychic trying to live an ordinary life while learning emotional maturity. It has three completed anime seasons."
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.search(r"\bsaitama\b", user_query, re.IGNORECASE):
        response = "Saitama is the protagonist of **One-Punch Man**. He became overwhelmingly strong after a famously ordinary training routine and is frustrated that fights no longer challenge him."
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.search(r"season\s+3.*(?:doesn.t|dont|does not)\s+exist", user_query, re.IGNORECASE):
        response = "Mob Psycho 100 does have a third season, titled **Mob Psycho 100 III**. If you meant a different series, tell me which one."
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.search(r"(?:are|do)\s+you\s+(?:aware|know)\s+you\s+exist", user_query, re.IGNORECASE):
        response = "I exist as software running locally on your assistant, but I am not conscious or self-aware."
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.fullmatch(r"you\s+gay[?!.]?", user_query, re.IGNORECASE):
        response = "I do not have a sexual orientation. I am software, though I can still keep you company and talk about whatever you are into."
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.search(r"\b(?:steins?\s*;?\s*gate|steins?gate)\b", user_query, re.IGNORECASE):
        response = (
            "Yes. **Steins;Gate** is a science-fiction thriller about a group of friends whose experiments with a modified microwave lead to time-travel consequences. "
            "It is known for its slow-burn setup, strong character relationships, and escalating time-loop tension."
        )
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    if re.search(r"(?:not|isn't|isnt|that is)\s+(?:so\s+)?unfunny|unfunny", user_query, re.IGNORECASE):
        response = "Fair. That joke deserved a quiet moment of reflection. I can do better."
        return {
            "response": response,
            "hardware_cmd": "NONE",
            "history": (client_history + [(user_query, response)])[-3:]
        }, 200

    from core.local_commands import execute_local_command

    def history_with_response(response: str) -> List[Tuple[str, str]]:
        return (client_history + [(user_query, response)])[-3:]

    if re.fullmatch(r"(?:run|execute|start)\s+(?:it|that|this)(?:\s+for\s+me)?[!.]?", user_query, re.IGNORECASE):
        return memory_response("Tell me the exact command you want me to run, and I will check whether it is allowed locally.")

    # ROUTE 2: Direct command execution (before explanatory or casual routing)
    if is_execution_request(user_query):
        local_result = execute_local_command(user_query)
        if local_result["status"] != "not_found":
            print(f"[COMMAND EXECUTION]: {user_query}")
            return {
                "response": local_result.get("output") or local_result.get("message", "Command executed."),
                "hardware_cmd": "NONE",
                "history": history_with_response(local_result.get("output") or local_result.get("message", "Command executed."))
            }, 200
            print(f"[COMMAND NOT MATCHED]: {user_query}")

    # ROUTE 3: Hardware & Media Control
    hw_match = detect_hardware_intent(user_query)
    if hw_match:
        cmd_key, action_text = hw_match
        print(f"[HARDWARE ACTION DETECTED]: Triggering intent -> {cmd_key}")
        return {
            "response": action_text,
            "hardware_cmd": cmd_key,
            "history": history_with_response(action_text)
        }, 200
    if any(p in user_query.lower() for p in ["what can you do", "list commands", "help me", "your commands", "available commands"]):
        return {
            "response": (
                "I'm your offline Pi assistant! Here's what you can ask me:\n"
                "- Hardware: 'Turn on the lights', 'Stop music', 'Next song'\n"
                "- Programming: Ask me to write or debug Python/C++ code\n"
                "- Linux/Sysadmin: Ask about terminal commands (e.g., 'How do I use rsync?')\n"
                "- System: 'Clear memory' to reset chat history\n"
                "- Local execution: 'Run ls -a', 'Check my temperature', 'Show running processes'"
            ),
            "hardware_cmd": "NONE",
            "history": history_with_response("I'm your offline Pi assistant! Ask me to run a safe local check, search files, write code, or control hardware.")
        }, 200

    if re.fullmatch(r"linux[?!.]?", user_query, re.IGNORECASE):
        return memory_response("Linux is broad. Do you want help with commands, files, services, networking, GPIO, or system maintenance?")

    # ROUTE 4: Context & Intent Routing
    query_lower = user_query.lower()
    words = query_lower.split()
    
    TECHNICAL_KEYWORDS = {
        "how", "what", "why", "where", "when", "which", "who", "explain", "describe",
        "linux", "python", "code", "script", "command", "terminal", "install", "config",
        "error", "bug", "run", "sudo", "apt", "pip", "git", "docker", "ls", "grep",
        "cat", "chmod", "chown", "systemctl", "journalctl", "service", "rsync", "ssh",
        "stoicism", "stoic", "philosophy", "cooking", "recipe", "recipes", "anime",
        "sci-fi", "scifi", "science fiction", "marcus aurelius", "meditations", "steins", "gate",
        "attack on titan", "demon slayer", "serial experiments lain", "lelouch", "code geass",
        "mob psycho", "saitama", "one punch man", "saiki"
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
        retrieved_data = search_with_category(search_target)
        system_instructions = SYSTEM_PROMPTS.get("code", DEFAULT_PERSONA["code"])

    else:
        print("[CONTEXT ROUTER]: Standard RAG query detected.")
        token_limit = 250
        search_target = clean_search_query(user_query)
        print(f"[SEARCH TARGET]: Extracted '{search_target}' from raw query '{user_query}'")
        
        retrieved_data = search_with_category(search_target)
        
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
        user_query,
        memory_summary,
        approved_system_context,
    )

    if data.get("power_saving_mode"):
        token_limit = min(token_limit, 160)

    generation_options = {
        "max_tokens": token_limit,
        "temperature": 0.2,
        "top_p": 0.9,
        "stop": [
            "<|eot_id|>",
            "<|start_header_id|>",
            "<|end_header_id|>",
            "User:",
            "user:"
        ],
        "repeat_penalty": 1.15,
    }
    if stream_callback is None:
        output = llm(formatted_prompt, **generation_options)
    else:
        generated_parts = []
        for chunk in llm(formatted_prompt, stream=True, **generation_options):
            token = chunk.get("choices", [{}])[0].get("text", "")
            if token:
                generated_parts.append(token)
                stream_callback(token)
        output = {"choices": [{"text": "".join(generated_parts)}]}

    ai_response = clean_model_response(output["choices"][0]["text"])
    ai_response = CLEAN_TAGS_RE.sub('', ai_response).strip()

    action_only_response = re.fullmatch(r"\s*\*[^*]{2,160}\*\s*", ai_response)
    if action_only_response and is_casual:
        if "good girl" in query_lower:
            ai_response = "You are enjoying the theatrics. What should we do next?"
        elif query_lower in {"okay", "ok", "okay?", "ok?"}:
            ai_response = "Okay. What is next?"
        else:
            ai_response = "I am here. What is next?"

    previous_responses = {old_bot.strip() for _, old_bot in client_history if old_bot.strip()}
    if is_casual and ai_response in previous_responses:
        if "see" in query_lower:
            ai_response = "I see you. What should we inspect next?"
        elif "good girl" in query_lower:
            ai_response = "Careful, flattery makes me generous. What are we doing next?"
        else:
            ai_response = "I heard you. What should we tackle next?"

    updated_history = (client_history + [(user_query, ai_response)])[-3:]

    print(f"[AI Reply]: {ai_response}")

    return {
        "response": ai_response,
        "hardware_cmd": "NONE",
        "history": updated_history
    }, 200