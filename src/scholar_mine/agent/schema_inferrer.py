"""Schema inferrer — LLM-driven extraction schema generation."""
import json, re, yaml
from pathlib import Path
from typing import Any, Dict, Optional

from scholar_mine.agent.prompts import SCHEMA_INFERENCE_PROMPT
from scholar_mine.utils.logger import Logger

log = Logger.get()

class SchemaInferrer:
    def __init__(self, llm_client):
        self.llm = llm_client

    def infer(self, domain_description: str, field_count: int = 15) -> dict:
        prompt = SCHEMA_INFERENCE_PROMPT.format(
            domain_description=domain_description, field_count=field_count
        )
        response = self.llm.chat(
            system_prompt="You are a domain expert. Define structured extraction fields for a research area.",
            user_prompt=prompt,
        )
        try:
            fields = json.loads(response)
            if isinstance(fields, list):
                return {
                    "schema_id": "auto_inferred",
                    "domain": domain_description[:80],
                    "description": f"Auto-inferred schema for: {domain_description[:100]}",
                    "fields": fields,
                }
        except json.JSONDecodeError:
            m = re.search(r'\[[\s\S]*\]', response)
            if m:
                try:
                    fields = json.loads(m.group())
                    return {"schema_id": "auto_inferred", "domain": domain_description[:80], "fields": fields}
                except json.JSONDecodeError:
                    pass
        return self._fallback_schema(domain_description)

    def load_preset(self, schema_id: str) -> Optional[dict]:
        preset_dir = Path(__file__).parent.parent.parent.parent / "config" / "schemas"
        path = preset_dir / f"{schema_id}.yaml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return None

    def _fallback_schema(self, domain: str) -> dict:
        general = self.load_preset("general_5fields")
        if general:
            return general
        return {
            "schema_id": "fallback",
            "domain": domain,
            "fields": [
                {"name": "Title", "key": "title", "type": "string"},
                {"name": "Authors", "key": "authors", "type": "string"},
                {"name": "Year", "key": "year", "type": "integer"},
                {"name": "Key Findings", "key": "key_findings", "type": "string"},
                {"name": "Notes", "key": "notes", "type": "string", "placeholder": "-"},
            ],
        }
