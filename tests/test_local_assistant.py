import unittest

from app_config import build_runtime_config
from local_commands import detect_local_command_query
from local_memory import LocalMemoryStore
from robot import process_robot_request


class LocalAssistantConfigurationTests(unittest.TestCase):
    def test_build_runtime_config_defaults_to_pi_safe_settings(self):
        config = build_runtime_config()
        self.assertEqual(config["mode"], "balanced")
        self.assertLessEqual(config["n_ctx"], 4096)
        self.assertGreater(config["n_threads"], 0)
        self.assertIn("flash_attn", config)

    def test_memory_store_can_persist_and_load_history(self):
        store = LocalMemoryStore(":memory:")
        try:
            store.add_memory("user", "hello there")
            store.add_memory("assistant", "hello back")
            store.add_fact("User likes science fiction", "anime_scifi")
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
