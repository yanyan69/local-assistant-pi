import unittest
import tempfile
from pathlib import Path

import core.app_config as app_config
from core.app_config import build_runtime_config
from core.local_commands import detect_local_command_query
from core.local_memory import LocalMemoryStore
from core.tools import execute_tool
from core.conversations import ConversationStore
from robot import process_robot_request
from core.system_context import read_system_context
from robot import build_llama3_prompt, clean_model_response, clean_search_query
from utilities.offline_catalogs import close_catalog_connections, connect, query_catalog, upsert_document


class LocalAssistantConfigurationTests(unittest.TestCase):
    def test_conversation_can_be_renamed_and_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ConversationStore(directory)
            conversation = store.create("Original title")
            renamed = store.rename(conversation["id"], "Renamed title")
            self.assertEqual(renamed["title"], "Renamed title")
            self.assertEqual(store.get(conversation["id"])["title"], "Renamed title")
            self.assertTrue(store.delete(conversation["id"]))
            self.assertIsNone(store.get(conversation["id"]))
            self.assertFalse(store.delete(conversation["id"]))

    def test_catalog_query_quotes_fts_terms_with_punctuation(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "catalog.db"
            connection = connect(db_path)
            try:
                upsert_document(
                    connection,
                    "raspberry_pi",
                    "USB storage",
                    "Safely eject a mounted USB drive with umount before unplugging it.",
                    "local://raspberry-pi/usb",
                )
                connection.commit()
                result = query_catalog(
                    "how to eject safely a usb in a raspberry pi? what command should i use?",
                    db_path=db_path,
                )
                self.assertIn("Safely eject", result)
            finally:
                connection.close()
                close_catalog_connections()

    def test_settings_persist_and_force_proactive_interval_to_sixty_seconds(self):
        with tempfile.TemporaryDirectory() as directory:
            original_path = app_config.SETTINGS_PATH
            app_config.SETTINGS_PATH = Path(directory) / "settings.json"
            try:
                saved = app_config.save_settings({"proactive_mode": True, "proactive_interval_seconds": 5})
                loaded = app_config.load_settings()
                self.assertTrue(saved["proactive_mode"])
                self.assertEqual(loaded["proactive_interval_seconds"], 60)
            finally:
                app_config.SETTINGS_PATH = original_path

    def test_awareness_off_does_not_read_system_context(self):
        context = read_system_context({"system_awareness": "off", "power_saving_mode": True})
        self.assertEqual(context, {"power_saving_mode": True})

    def test_prompt_includes_approved_system_context(self):
        prompt = build_llama3_prompt(
            "You are local.",
            "[Source: notes.md]\n[Category: test]\nRetrieved fact.",
            [],
            "What time is it?",
            system_context={"local_time": "03:04", "power_saving_mode": True},
        )
        self.assertIn("Approved Local System Context", prompt)
        self.assertIn("03:04", prompt)
        self.assertIn("Retrieved Local Context", prompt)
        self.assertIn("Treat Retrieved Local Context as reference material", prompt)

    def test_empty_retrieval_prompt_does_not_assume_platform(self):
        prompt = build_llama3_prompt("You are local.", "", [], "How do I transfer files?")
        self.assertIn("Retrieved Local Context: NONE", prompt)
        self.assertIn("Do not assume the user's operating system", prompt)

    def test_short_command_names_are_preserved_in_search_query(self):
        query = clean_search_query("more commands using cp in linux")
        self.assertIn("cp", query.split())
        self.assertIn("linux", query.split())

    def test_debug_retrieval_trace_exposes_search_context_and_sources(self):
        def retrieval_llm(*args, **kwargs):
            return {"choices": [{"text": "Here is the grounded answer."}]}

        def search_database(query, category=None):
            return "[Source: local_notes.md]\n[Category: philosophy]\nA grounded local fact."

        response, status = process_robot_request(
            {"query": "explain stoicism", "history": [], "debug_retrieval": True},
            retrieval_llm,
            search_database=search_database,
        )
        self.assertEqual(status, 200)
        self.assertEqual(response["retrieval_trace"]["query"], "stoicism command usage explanation")
        self.assertEqual(response["retrieval_trace"]["sources"], [{"filename": "local_notes.md", "category": "philosophy"}])
        self.assertIn("A grounded local fact.", response["retrieval_trace"]["context"])

    def test_time_question_uses_approved_local_clock(self):
        def unexpected_llm(*args, **kwargs):
            raise AssertionError("time lookup should not call the LLM")

        response, status = process_robot_request(
            {"query": "what is the time?", "history": [], "system_context": {"local_time": "03:04"}},
            unexpected_llm,
        )
        self.assertEqual(status, 200)
        self.assertEqual(response["response"], "It is 03:04 locally.")

    def test_check_time_uses_local_clock_before_command_routing(self):
        response, status = process_robot_request(
            {"query": "check the time", "history": [], "system_context": {"local_time": "12:49"}},
            None,
        )
        self.assertEqual(status, 200)
        self.assertEqual(response["response"], "It is 12:49 locally.")

    def test_personal_feelings_question_is_not_sent_to_rag(self):
        def unexpected_llm(*args, **kwargs):
            raise AssertionError("personal feelings question should not call the LLM")

        response, status = process_robot_request(
            {"query": "what do you feel about me?", "history": []},
            unexpected_llm,
        )
        self.assertEqual(status, 200)
        self.assertIn("do not have human feelings", response["response"])

    def test_personal_thoughts_question_is_not_sent_to_rag(self):
        response, status = process_robot_request(
            {"query": "explain your thoughts about me", "history": []},
            None,
        )
        self.assertEqual(status, 200)
        self.assertIn("do not have human feelings", response["response"])

    def test_vague_code_request_asks_for_requirements(self):
        response, status = process_robot_request({"query": "sample me a code", "history": []}, None)
        self.assertEqual(status, 200)
        self.assertIn("which language", response["response"])

    def test_insult_gets_a_grounded_repair_response(self):
        response, status = process_robot_request({"query": "you sound stupid", "history": []}, None)
        self.assertEqual(status, 200)
        self.assertIn("missed the mark", response["response"])

    def test_markdown_language_fence_is_normalized(self):
        cleaned = clean_model_response("```markdown\nconst answer = 1;\n```")
        self.assertTrue(cleaned.startswith("```\n"))

    def test_miss_me_question_is_grounded(self):
        response, status = process_robot_request({"query": "you miss me?", "history": []}, None)
        self.assertEqual(status, 200)
        self.assertIn("do not miss people", response["response"])

    def test_correction_is_acknowledged_without_llm(self):
        response, status = process_robot_request({"query": "i didnt say that", "history": []}, None)
        self.assertEqual(status, 200)
        self.assertIn("misunderstood", response["response"])

    def test_bare_linux_query_does_not_invent_a_command(self):
        response, status = process_robot_request({"query": "linux", "history": []}, None)
        self.assertEqual(status, 200)
        self.assertIn("Linux is broad", response["response"])
        self.assertNotIn("sudo apt", response["response"])

    def test_vague_run_request_requires_an_exact_command(self):
        response, status = process_robot_request({"query": "run it for me", "history": []}, None)
        self.assertEqual(status, 200)
        self.assertIn("exact command", response["response"])

    def test_temperature_typo_is_normalized_to_local_status(self):
        response, status = process_robot_request(
            {"query": "cpu termp", "history": [], "system_context": {"cpu_temperature_c": 51.2}},
            None,
        )
        self.assertEqual(status, 200)
        self.assertEqual(response["response"], "The CPU temperature is 51.2 C.")

    def test_time_question_respects_awareness_off(self):
        response, status = process_robot_request(
            {"query": "what is the time?", "history": [], "system_awareness": "off"},
            None,
        )
        self.assertEqual(status, 200)
        self.assertIn("system awareness is turned off", response["response"])

    def test_light_death_is_grounded_as_death_note(self):
        def unexpected_llm(*args, **kwargs):
            raise AssertionError("Death Note fact should not call the LLM")

        response, status = process_robot_request(
            {"query": "what are your thoughts about Light's Death?", "history": []},
            unexpected_llm,
        )
        self.assertEqual(status, 200)
        self.assertIn("Death Note", response["response"])
        self.assertIn("Ryuk", response["response"])

    def test_model_response_does_not_leak_internal_prompt_sections(self):
        cleaned = clean_model_response(
            "Local Memory Summary:\nDurable user facts:\n- User likes tea\nRecent conversation:"
        )
        self.assertNotIn("Local Memory Summary", cleaned)
        self.assertNotIn("Durable user facts", cleaned)
        self.assertIn("direct answer", cleaned)

    def test_build_runtime_config_defaults_to_pi_safe_settings(self):
        config = build_runtime_config()
        self.assertEqual(config["mode"], "balanced")
        self.assertLessEqual(config["n_ctx"], 4096)
        self.assertGreater(config["n_threads"], 0)
        self.assertIn("flash_attn", config)

    def test_power_saving_profile_reduces_model_runtime_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            original_path = app_config.SETTINGS_PATH
            app_config.SETTINGS_PATH = Path(directory) / "settings.json"
            try:
                app_config.save_settings({"power_saving_mode": True})
                config = build_runtime_config()
                self.assertEqual(config["effective_mode"], "power_saving")
                self.assertEqual(config["n_batch"], 64)
                self.assertEqual(config["n_ctx"], 1024)
            finally:
                app_config.SETTINGS_PATH = original_path

    def test_typed_temperature_tool_returns_structured_result(self):
        result = execute_tool("get_temperature")
        self.assertIn(result["status"], {"ok", "error"})
        self.assertIn("output", result)

    def test_model_stream_callback_receives_generated_tokens(self):
        received = []

        class FakeStreamingLlm:
            def __call__(self, prompt, stream=False, **kwargs):
                self.assertTrue(stream)
                yield {"choices": [{"text": "streamed "}]}
                yield {"choices": [{"text": "answer"}]}

            def assertTrue(self, value):
                if not value:
                    raise AssertionError("stream mode was not enabled")

        response, status = process_robot_request(
            {"query": "tell me something", "history": []},
            FakeStreamingLlm(),
            search_database=lambda query: "",
            stream_callback=received.append,
        )
        self.assertEqual(status, 200)
        self.assertEqual("".join(received), "streamed answer")
        self.assertIn("streamed answer", response["response"])

    def test_memory_store_can_persist_and_load_history(self):
        store = LocalMemoryStore(":memory:")
        try:
            store.add_memory("user", "hello there")
            store.add_memory("assistant", "hello back")
            store.add_fact("User likes science fiction", "anime")
            self.assertGreater(len(store.get_recent_history(limit=10)), 0)
            self.assertIn("hello there", store.get_recent_history(limit=10)[0]["content"])
            self.assertIn("science fiction", store.get_memory_summary())
            self.assertEqual(store.remove_facts("science fiction"), 1)
        finally:
            store.close()

    def test_command_detection_handles_top_processes_and_grep_queries(self):
        self.assertIn("top_processes", detect_local_command_query("show top 5 running processes"))
        self.assertIn("grep", detect_local_command_query("grep hello in app.py"))
        self.assertIn("app.py", detect_local_command_query("grep hello in app.py"))
        self.assertEqual(detect_local_command_query("check top 5 running processes?"), "top_processes:5")
        self.assertEqual(detect_local_command_query('check for a file with words "reze"'), "search_files:reze")
        self.assertEqual(
            detect_local_command_query('check for a file within our dir, with a word "reze"'),
            "search_files:reze",
        )

    def test_command_history_question_does_not_call_llm(self):
        def unexpected_llm(*args, **kwargs):
            raise AssertionError("LLM should not be called for this deterministic route")

        response, status = process_robot_request(
            {"query": "what command were u looking for?", "history": []},
            unexpected_llm,
        )
        self.assertEqual(status, 200)
        self.assertIn("not looking for a specific command", response["response"])

    def test_sample_git_commands_is_not_executed(self):
        def command_list_llm(prompt, **kwargs):
            return {"choices": [{"text": "- `git status`\n- `git log`"}]}

        response, status = process_robot_request(
            {"query": "sample me git commands", "history": []},
            command_list_llm,
        )
        self.assertEqual(status, 200)
        self.assertIn("git", response["response"])

    def test_security_topic_uses_technical_routing(self):
        searches = []

        def search_database(query):
            searches.append(query)
            return "Cybersecurity includes authentication, authorization, and secure updates."

        def knowledge_llm(prompt, **kwargs):
            return {"choices": [{"text": "Cybersecurity protects systems, data, and users from unauthorized access."}]}

        response, status = process_robot_request(
            {"query": "teach me about cybersecurity", "history": []},
            knowledge_llm,
            search_database=search_database,
        )
        self.assertEqual(status, 200)
        self.assertTrue(searches)
        self.assertIn("Cybersecurity", response["response"])

    def test_repeated_casual_reply_is_replaced(self):
        def repeated_llm(*args, **kwargs):
            return {"choices": [{"text": "You're a sly one, always seeing right through my attempts at sass."}]}

        response, status = process_robot_request(
            {
                "query": "i see",
                "history": [("previous", "You're a sly one, always seeing right through my attempts at sass.")],
            },
            repeated_llm,
        )
        self.assertEqual(status, 200)
        self.assertEqual(response["response"], "I see you. What should we inspect next?")

    def test_sass_follow_up_uses_conversational_meaning(self):
        def unexpected_llm(*args, **kwargs):
            raise AssertionError("LLM should not be called for this contextual definition")

        response, status = process_robot_request(
            {"query": "what does sass even mean?", "history": []},
            unexpected_llm,
        )
        self.assertEqual(status, 200)
        self.assertIn("playful attitude", response["response"])

    def test_unverified_personal_fact_is_not_presented_as_memory(self):
        def unexpected_llm(*args, **kwargs):
            raise AssertionError("LLM should not be called for this clarification")

        response, status = process_robot_request(
            {"query": "how did you know i love coffee?", "history": []},
            unexpected_llm,
        )
        self.assertEqual(status, 200)
        self.assertIn("playful guess", response["response"])

    def test_knowledge_topic_is_not_misclassified_as_casual(self):
        searches = []

        def search_database(query):
            searches.append(query)
            return "Stoicism is a philosophy focused on distinguishing what is within your control."

        def knowledge_llm(*args, **kwargs):
            return {"choices": [{"text": "Stoicism is a philosophy about deliberate responses and control."}]}

        response, status = process_robot_request(
            {"query": "YOU KNOW ABOUT STOICISM?", "history": []},
            knowledge_llm,
            search_database=search_database,
        )
        self.assertEqual(status, 200)
        self.assertTrue(searches)
        self.assertIn("Stoicism", response["response"])

    def test_casual_action_only_reply_becomes_spoken_text(self):
        def theatrical_llm(*args, **kwargs):
            return {"choices": [{"text": "*smirks mischievously, eyes glinting with amusement*"}]}

        response, status = process_robot_request(
            {"query": "good girl", "history": []},
            theatrical_llm,
        )
        self.assertEqual(status, 200)
        self.assertEqual(response["response"], "You are enjoying the theatrics. What should we do next?")

    def test_fried_egg_request_returns_actual_fried_egg_method(self):
        response, status = process_robot_request(
            {"query": "sample me a fried egg recipe", "history": []},
            None,
        )
        self.assertEqual(status, 200)
        self.assertIn("Crack the egg directly into the pan", response["response"])
        self.assertIn("Do not whisk it", response["response"])

    def test_dark_humor_request_is_not_replaced_with_an_egg_pun(self):
        response, status = process_robot_request(
            {"query": "sample a dark humor", "history": []},
            None,
        )
        self.assertEqual(status, 200)
        self.assertIn("dark sense of humor", response["response"])

    def test_lain_origin_is_grounded(self):
        response, status = process_robot_request(
            {"query": "what anime did Lain come from again? the computer girl", "history": []},
            None,
        )
        self.assertEqual(status, 200)
        self.assertIn("Serial Experiments Lain", response["response"])
        self.assertNotIn("Neon Genesis Evangelion", response["response"])

    def test_greeting_does_not_trigger_random_recommendation(self):
        response, status = process_robot_request(
            {"query": "hi", "history": []},
            None,
        )
        self.assertEqual(status, 200)
        self.assertEqual(response["response"], "Hey. What are we getting into?")

    def test_steins_gate_is_recognized_as_anime_knowledge(self):
        response, status = process_robot_request(
            {"query": "you know steins gate bro the anime", "history": []},
            None,
        )
        self.assertEqual(status, 200)
        self.assertIn("Steins;Gate", response["response"])

    def test_watched_feedback_does_not_trigger_another_random_title(self):
        response, status = process_robot_request(
            {"query": "i already watched that", "history": []},
            None,
        )
        self.assertEqual(status, 200)
        self.assertIn("stop repeating", response["response"])

    def test_anime_facts_are_grounded(self):
        cases = [
            ("do you know lelouch?", "Code Geass"),
            ("have you watched mob psycho?", "three completed anime seasons"),
            ("how about Saitama", "One-Punch Man"),
            ("okay nvm, anyway you know Lain? and Saiki K?", "The Disastrous Life of Saiki K."),
        ]
        for query, expected in cases:
            response, status = process_robot_request({"query": query, "history": []}, None)
            self.assertEqual(status, 200)
            self.assertIn(expected, response["response"])

    def test_awareness_and_orientation_questions_are_grounded(self):
        response, status = process_robot_request(
            {"query": "are you aware you exist?", "history": []}, None
        )
        self.assertEqual(status, 200)
        self.assertIn("not conscious", response["response"])

        response, status = process_robot_request(
            {"query": "you gay?", "history": []}, None
        )
        self.assertEqual(status, 200)
        self.assertIn("sexual orientation", response["response"])

    def test_remember_forget_and_preference_commands_persist(self):
        store = LocalMemoryStore(":memory:")
        try:
            response, status = process_robot_request(
                {"query": "remember that I like psychological anime", "history": []},
                None,
                memory_store=store,
            )
            self.assertEqual(status, 200)
            self.assertIn("remember", response["response"].lower())
            self.assertIn("psychological anime", store.get_memory_summary())

            response, status = process_robot_request(
                {"query": "forget psychological anime", "history": []},
                None,
                memory_store=store,
            )
            self.assertEqual(status, 200)
            self.assertNotIn("psychological anime", store.get_memory_summary())
        finally:
            store.close()

    def test_anime_facts_are_grounded(self):
        cases = [
            ("do you know lelouch?", "Code Geass"),
            ("have you watched mob psycho?", "three completed anime seasons"),
            ("how about Saitama", "One-Punch Man"),
            ("okay nvm, anyway you know Lain? and Saiki K?", "The Disastrous Life of Saiki K."),
        ]
        for query, expected in cases:
            response, status = process_robot_request({"query": query, "history": []}, None)
            self.assertEqual(status, 200)
            self.assertIn(expected, response["response"])

    def test_awareness_and_orientation_questions_are_grounded(self):
        response, status = process_robot_request(
            {"query": "are you aware you exist?", "history": []}, None
        )
        self.assertEqual(status, 200)
        self.assertIn("not conscious", response["response"])

        response, status = process_robot_request(
            {"query": "you gay?", "history": []}, None
        )
        self.assertEqual(status, 200)
        self.assertIn("sexual orientation", response["response"])


if __name__ == "__main__":
    unittest.main()
