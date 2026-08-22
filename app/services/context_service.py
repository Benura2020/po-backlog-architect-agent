import os
import re
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import ContextSection

logger = logging.getLogger(__name__)


class ContextService:
    def __init__(self, db: Session, db_path: str = "./flowdesk.db"):
        self.db = db
        self.db_path = db_path
        self._init_fts5()

    def _init_fts5(self):
        """Initialize SQLite FTS5 virtual table for keyword & text search."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_context USING fts5(
                ref UNINDEXED,
                title,
                content,
                document_name
            );
        """)
        conn.commit()
        conn.close()

    def index_markdown(self, file_path: str, doc_name: str = "product_brief.md") -> int:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Markdown document not found at: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Regex to split document by Markdown headings containing section refs like PB-01, PB-04.1
        # Example pattern: ### Section PB-04.1: Supported Media Types
        pattern = r"(?=(?:^|\n)#{1,4}\s+(?:Section\s+)?(PB-\d+(?:\.\d+)?):?\s*(.*?)(?=\n|$))"
        matches = list(re.finditer(pattern, text, re.DOTALL))

        sections: List[Dict[str, Any]] = []

        if not matches:
            # Fallback block chunking if no explicit PB refs found
            blocks = text.split("\n\n")
            for idx, block in enumerate(blocks):
                ref = f"PB-{idx+1:02d}"
                sections.append({
                    "ref": ref,
                    "title": f"Section {ref}",
                    "content": block.strip(),
                    "document_name": doc_name
                })
        else:
            for i in range(len(matches)):
                match = matches[i]
                ref = match.group(1).strip()
                title = match.group(2).strip()

                start_pos = match.start()
                end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                section_text = text[start_pos:end_pos].strip()

                # Remove heading line from section text for clean content
                lines = section_text.split("\n")
                content = "\n".join(lines[1:]).strip() if len(lines) > 1 else section_text

                sections.append({
                    "ref": ref,
                    "title": title or f"Section {ref}",
                    "content": content,
                    "document_name": doc_name
                })

        # Clear existing DB sections for this document
        self.db.query(ContextSection).filter(ContextSection.document_name == doc_name).delete()
        self.db.commit()

        for s in sections:
            db_section = ContextSection(
                ref=s["ref"],
                title=s["title"],
                content=s["content"],
                document_name=s["document_name"]
            )
            self.db.add(db_section)
        self.db.commit()

        # Sync with FTS5 table separately
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fts_context WHERE document_name = ?", (doc_name,))
        for s in sections:
            cursor.execute(
                "INSERT INTO fts_context (ref, title, content, document_name) VALUES (?, ?, ?, ?)",
                (s["ref"], s["title"], s["content"], s["document_name"])
            )
        conn.commit()
        conn.close()

        logger.info(f"Indexed {len(sections)} context sections from {doc_name}")
        return len(sections)

    def get_section(self, ref: str) -> Optional[ContextSection]:
        return self.db.query(ContextSection).filter(ContextSection.ref == ref).first()

    def search_context(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Sanitize query for FTS5
        clean_query = re.sub(r"[^\w\s]", " ", query).strip()
        if not clean_query:
            return []

        try:
            cursor.execute(
                """
                SELECT ref, title, content, document_name
                FROM fts_context
                WHERE fts_context MATCH ?
                LIMIT ?
                """,
                (clean_query, limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.OperationalError:
            # Fallback simple LIKE query if FTS syntax fails
            cursor.execute(
                """
                SELECT ref, title, content, document_name
                FROM fts_context
                WHERE title LIKE ? OR content LIKE ?
                LIMIT ?
                """,
                (f"%{clean_query}%", f"%{clean_query}%", limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_all_sections(self) -> List[ContextSection]:
        return self.db.query(ContextSection).all()
