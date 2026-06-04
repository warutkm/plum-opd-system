import json
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DocumentChunker:
    def __init__(self):
        self._local_chunks_cache: List[Dict[str, Any]] = []

    def get_chunks(self) -> List[Dict[str, Any]]:
        if self._local_chunks_cache:
            return self._local_chunks_cache

        chunks: List[Dict[str, Any]] = []
        base_dir = Path(__file__).parent.parent.parent
        rules_path = base_dir / "reference" / "adjudication_rules.md"
        terms_path = base_dir / "reference" / "policy_terms.json"

        if not rules_path.exists():
            rules_path = base_dir.parent / "adjudication_rules.md"
        if not terms_path.exists():
            terms_path = base_dir.parent / "policy_terms.json"

        if rules_path.exists():
            content = rules_path.read_text(encoding="utf-8")
            blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
            for idx, block in enumerate(blocks):
                chunks.append({
                    "text": block,
                    "source": "adjudication_rules.md",
                    "index": idx,
                    "embedding": None,
                })

        if terms_path.exists():
            try:
                terms_data = json.loads(terms_path.read_text(encoding="utf-8"))
                for key, val in terms_data.items():
                    if isinstance(val, dict):
                        text = f"Policy Section: {key.replace('_', ' ').title()}\n{json.dumps(val, indent=2)}"
                    else:
                        text = f"Policy Parameter: {key.title()} = {val}"
                    chunks.append({
                        "text": text,
                        "source": "policy_terms.json",
                        "index": len(chunks),
                        "embedding": None,
                    })
            except Exception as exc:
                logger.error(f"Error parsing local policy terms JSON: {exc}")

        self._local_chunks_cache = chunks
        return chunks
