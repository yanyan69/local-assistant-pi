import re

BAD_WORDS_RE = re.compile(
    r'\b(fuck|fucking|fucked|slave|bitch|shit|damn)\b',
    re.IGNORECASE
)


def process_robot_request(data, llm, search_database):
    if not data or "query" not in data:
        return {
            "error": "Missing 'query' field"
        }, 400

    raw_query = data["query"].strip()

    user_query = BAD_WORDS_RE.sub(
        "",
        raw_query
    ).replace(
        "  ",
        " "
    ).strip().lower()

    filler_words = [
        "okay ",
        "ok ",
        "cool ",
        "thanks ",
        "thank you ",
        "yes ",
        "bro ",
        "lol ",
        "hahaha "
    ]

    cleaned_router_query = user_query

    for word in filler_words:
        if cleaned_router_query.startswith(word):
            cleaned_router_query = cleaned_router_query[
                len(word):
            ].strip()

    client_history = data.get("history", [])

    print(f"\n[Incoming Request]: {user_query}")

    if any(cmd in user_query for cmd in ["clear memory", "reset chat", "clear chat"]):
        print("[SYSTEM INFO]: Short-term conversation history wiped.")
        return {
            "response": "Memory wiped. Ready for a new topic!",
            "hardware_cmd": "NONE",
            "history": []
        }, 200

    if any(on_cmd in user_query for on_cmd in ["turn on", "switch on"]) and any(w in user_query for w in ["light", "led"]) or user_query in ["lights on", "light on", "led on"]:
        print("[HARDWARE ACTION]: Triggering LED ON command.")
        return {
            "response": "Understood. Turning the light on right now.",
            "hardware_cmd": "LED_ON",
            "history": client_history
        }, 200

    if any(off_cmd in user_query for off_cmd in ["turn off", "switch off"]) and any(w in user_query for w in ["light", "led"]) or user_query in ["lights off", "light off", "led off"]:
        print("[HARDWARE ACTION]: Triggering LED OFF command.")
        return {
            "response": "Understood. Switching off the light.",
            "hardware_cmd": "LED_OFF",
            "history": client_history
        }, 200

    code_generation_triggers = [
        "code",
        "script",
        "program",
        "function",
        "write a python",
        "write code"
    ]

    is_follow_up_request = any(
        w in user_query
        for w in [
            "make it",
            "change it",
            "fix it",
            "more",
            "add",
            "continue",
            "next",
            "how about"
        ]
    )
    router_words = set(cleaned_router_query.split())
    casual_phrases = ["your name", "my name", "who are you", "who am i", "thank you"]
    if (
        any(
            w in cleaned_router_query
            for w in code_generation_triggers
        )
        or is_follow_up_request
    ):
        token_limit = 400

        print(
            "[CONTEXT ROUTER]: "
            "Heavy Generation or Follow-up Request Detected."
        )

        retrieved_data = search_database(user_query)

        system_instructions = (
            "You are a programming assistant. "
            "Write only the exact, functional code requested by the user. "
            "Wrap your code block in standard markdown formatting. "
            "Keep verbal explanations to a maximum of 2 sentences below "
            "the code block. "
            "If the user mentions a specific hardware target, "
            "use its standard framework. "
            "Say 'I don't know' if you can't search for info about it."
        )
    
    elif (
        any(w in router_words for w in ["hello", "hi", "hey", "thanks", "cool", "ok", "okay"])
        or any(phrase in cleaned_router_query for phrase in casual_phrases)
        or not cleaned_router_query
    ):
        token_limit = 80

        print(
            "[CONTEXT ROUTER]: "
            "Casual conversation detected."
        )

        retrieved_data = "No file search context needed."

        system_instructions = (
            "You are a friendly, concise offline robot assistant. "
            "Respond naturally. Keep it very short."
        )

    else:
        token_limit = 150
        print("[CONTEXT ROUTER]: Standard query detected.")

        retrieved_data = search_database(user_query)
        print(f"\n[RAW DATABASE RETRIEVAL]:\n{retrieved_data}\n")

        if "No highly relevant text matches found" in retrieved_data or "No local document records" in retrieved_data:
            return {
                "response": "I could not find that specific information in my local documents.",
                "hardware_cmd": "NONE",
                "history": client_history + [(user_query, "I could not find that specific information in my local documents.")]
            }, 200
        
        system_instructions = (
            "You are a precise offline search assistant. "
            "Answer the user's question clearly and directly using only the facts provided in the Context below. "
            "CRITICAL FORMAT RULE: Write your entire response as a single, continuous paragraph. "
            "Do not use bullet points, numbered lists, or newlines. "
            "Keep your total output short and concise (under 3 sentences). "
            "If the provided Context does not contain the direct answer to the user's question, respond exactly with: "
            "'I could not find that specific information in my local documents.' "
            "Do not make up facts or use outside knowledge."
        )

    formatted_prompt = (
        "<|start_header_id|>system<|end_header_id|>\n\n"
        f"{system_instructions}\n\n"
        f"Context:\n{retrieved_data[:2000]}"
        "<|eot_id|>"
    )

    for old_user, old_bot in client_history[-2:]:
        clean_old_user = (
            str(old_user)
            .strip()
            .replace("<|", "")
        )

        clean_old_bot = (
            str(old_bot)
            .strip()
            .replace("<|", "")
        )

        formatted_prompt += (
            "<|start_header_id|>user<|end_header_id|>\n\n"
            f"{clean_old_user}"
            "<|eot_id|>"
            "<|start_header_id|>assistant<|end_header_id|>\n\n"
            f"{clean_old_bot}"
            "<|eot_id|>"
        )

    formatted_prompt += f"<|start_header_id|>user<|end_header_id|>\n\n{user_query}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

    output = llm(
        formatted_prompt,
        max_tokens=token_limit,
        temperature=0.1,
        stop=[
            "<|eot_id|>",
            "<|start_header_id|>",
            "<|end_header_id|>",
            "User:",
            "user:"
        ],
        repeat_penalty=1.2
    )

    ai_response = output["choices"][0]["text"].strip()

    updated_history = (
        client_history
        + [(user_query, ai_response)]
    )[-3:]

    print(f"[AI Reply]: {ai_response}")

    return {
        "response": ai_response,
        "hardware_cmd": "NONE",
        "history": updated_history
    }, 200