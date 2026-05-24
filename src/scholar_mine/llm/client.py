"""DeepSeek-compatible LLM client with batch support."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from openai import OpenAI

from scholar_mine.utils.logger import Logger
from scholar_mine.utils.retry import retry_sync

load_dotenv()
log = Logger.get()


class LLMClient:
    """Unified LLM client — currently DeepSeek, extensible to OpenAI/Anthropic.

    Supports:
    - Single-prompt completion
    - Batch completion (multiple prompts in one request for efficiency)
    - Schema-driven structured extraction
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        self.model = self.config.get("llm", {}).get("model", "deepseek-chat")
        self.max_tokens = self.config.get("llm", {}).get("max_tokens", 8192)
        self.temperature = self.config.get("llm", {}).get("temperature", 0.1)
        self.timeout = self.config.get("llm", {}).get("request_timeout_secs", 120)
        self.max_retries = self.config.get("llm", {}).get("max_retries", 3)

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        # Try default config
        default = Path(__file__).parent.parent.parent.parent / "config" / "default.yaml"
        if default.exists():
            with open(default, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    @retry_sync(max_retries=3)
    def chat(self, system_prompt: str, user_prompt: str,
             max_tokens: Optional[int] = None,
             temperature: Optional[float] = None) -> str:
        """Single-turn chat completion. Returns response text."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature if temperature is not None else self.temperature,
            timeout=self.timeout,
        )
        return response.choices[0].message.content or ""

    @retry_sync(max_retries=2)
    def extract_batch(self, papers: List[Dict[str, str]],
                      schema: Dict[str, Any],
                      max_tokens: int = 128000) -> Dict[str, Any]:
        """Batch extract structured data from multiple papers.

        Args:
            papers: [{"source": filename, "text": full_text}, ...]
            schema: Schema dict with field definitions
            max_tokens: Max output tokens (128K for deepseek-chat)

        Returns:
            {"results": [...], "errors": [...], "usage": {...}}
        """
        field_names = [f["name"] for f in schema.get("fields", [])]
        field_keys = [f["key"] for f in schema.get("fields", [])]

        # Build the system prompt
        sys_prompt = f"""You are a research data extraction expert. Your task is to read academic papers and extract structured data.

FIELDS TO EXTRACT (in order):
{chr(10).join(f'  {i+1}. {name} (key: {key})' for i, (name, key) in enumerate(zip(field_names, field_keys)))}

OUTPUT FORMAT:
Return a JSON object with a "results" array. Each element is one extracted record:
{{
  "source": "filename.pdf",
  "data": [
    {{
      "{field_keys[0]}": "value1",
      "{field_keys[1]}": "value2",
      ...
    }}
  ]
}}

RULES:
- If a field is not found in the paper, use "{self._placeholder(schema)}".
- One paper may produce MULTIPLE rows (e.g., different catalyst systems).
- Use precise values from the text. Do NOT invent or extrapolate.
- If the paper is completely irrelevant to the research topic, mark it:
  {{"source": "filename.pdf", "reject": true, "reason": "irrelevant — topic X, not Y"}}
- Output ONLY valid JSON. No markdown fences, no commentary."""

        # Build user prompt with paper texts
        paper_texts = []
        for i, paper in enumerate(papers):
            text = paper.get("text", "")
            # Truncate each paper to ~100K chars if needed
            if len(text) > 150000:
                text = text[:150000] + "\n\n[...truncated...]"
            paper_texts.append(
                f"=== PAPER {i+1}: {paper['source']} ===\n\n{text}"
            )

        user_prompt = "Extract structured data from the following papers:\n\n"
        user_prompt += "\n\n---\n\n".join(paper_texts)
        user_prompt += "\n\n---\n\nReturn the JSON object now."

        log.info(f"Sending batch of {len(papers)} papers to LLM "
                 f"(~{len(user_prompt)} chars input)")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.1,
            timeout=300,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown fences
            import re
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                parsed = json.loads(match.group())
            else:
                parsed = {"results": [], "errors": [{"raw": raw[:500]}]}

        return parsed

    def _placeholder(self, schema: Dict[str, Any]) -> str:
        return schema.get("output", {}).get("placeholder", "-") if isinstance(schema.get("output"), dict) else "-"

    def generate_keywords(self, research_direction: str, count: int = 25,
                          mode: str = "broad") -> List[str]:
        """Generate search keywords for a research direction."""
        from scholar_mine.agent.prompts import KEYWORD_EXPANSION_PROMPT

        prompt = KEYWORD_EXPANSION_PROMPT.format(
            research_direction=research_direction,
            count=count,
            mode=mode,
        )
        response = self.chat(
            system_prompt="You are a research librarian expert in keyword expansion.",
            user_prompt=prompt,
        )
        # Parse the response — expect a JSON array
        try:
            keywords = json.loads(response)
            if isinstance(keywords, list):
                return [k for k in keywords if isinstance(k, str) and k.strip()]
        except json.JSONDecodeError:
            pass

        # Fallback: split by newlines
        return [line.strip("-•* ") for line in response.split("\n")
                if line.strip() and not line.strip().startswith(("{", "["))]
