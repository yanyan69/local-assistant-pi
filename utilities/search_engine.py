# utilities/search_engine.py
import os
import re
import sqlite3
from typing import List, Dict, Any
from core.app_config import KNOWLEDGE_DB_PATH

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = str(KNOWLEDGE_DB_PATH)

class OfflineSearchEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def query(self, query_str: str, top_k: int = 2, category: str = None) -> str:
        """Queries SQLite FTS5 index directly for BM25 match scores."""
        if not os.path.exists(self.db_path):
            return "No local document records available."

        # Extract search terms and strip stop words
        sanitized_terms = re.findall(r'\w+', query_str.lower())
        stop_words = {
            "about", "what", "whatis", "explain", "describe", "intro", 
            "tell", "your", "with", "this", "that", "from", "and", "how", 
            "why", "does", "is", "command", "usage", "explanation"
        }
        core_terms = [t for t in sanitized_terms if len(t) > 2 and t not in stop_words]

        if not core_terms:
            core_terms = [t for t in sanitized_terms if len(t) > 2]

        if not core_terms:
            return "No clear search query detected."

        fts_query = " OR ".join(core_terms)

        try:
            with sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True) as conn:
                cursor = conn.cursor()
                
                # Check if FTS table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='paragraphs_fts'")
                if not cursor.fetchone():
                    return "Search index not initialized."

                category_filter = " AND category = ?" if category else ""
                sql = f"""
                    SELECT 
                        filename,
                        category,
                        content,
                        bm25(paragraphs_fts) AS score
                    FROM paragraphs_fts
                    WHERE paragraphs_fts MATCH ?{category_filter}
                    ORDER BY score ASC
                    LIMIT ?
                """
                params = (fts_query, category, top_k) if category else (fts_query, top_k)
                cursor.execute(sql, params)

                rows = cursor.fetchall()
                if not rows:
                    return "No highly relevant text matches found in local documents."

                results = []
                for filename, category, content, score in rows:
                    results.append(f"[Source: {filename}]\n[Category: {category}]\n{content}")

                return "\n\n---\n\n".join(results)

        except Exception as e:
            return f"Knowledge search error occurred: {e}"