"""Keyword expander — LLM-driven search keyword generation."""
import json
import re
from typing import Dict, List

from scholar_mine.agent.prompts import KEYWORD_EXPANSION_PROMPT
from scholar_mine.utils.logger import Logger

log = Logger.get()

class KeywordExpander:
    def __init__(self, llm_client):
        self.llm = llm_client

    def expand(self, research_direction: str, count: int = 25, mode: str = "broad") -> List[str]:
        prompt = KEYWORD_EXPANSION_PROMPT.format(
            research_direction=research_direction, count=count, mode=mode
        )
        response = self.llm.chat(
            system_prompt="You are a research librarian expert in keyword expansion.",
            user_prompt=prompt,
        )
        try:
            keywords = json.loads(response)
            if isinstance(keywords, list):
                return [k.strip() for k in keywords if isinstance(k, str) and k.strip()]
        except json.JSONDecodeError:
            pass
        lines = [line.strip("- *\u2022\t") for line in response.split("\n") if line.strip()]
        return lines[:count]

    def classify_strength(self, keywords: List[str]) -> Dict[str, List[str]]:
        mid = len(keywords) // 2
        return {"strong": keywords[:mid], "weak": keywords[mid:]}
