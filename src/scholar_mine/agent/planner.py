"""Research planner — main Agent entry point."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path

from scholar_mine.agent.keyword_expander import KeywordExpander
from scholar_mine.agent.schema_inferrer import SchemaInferrer
from scholar_mine.agent.config_generator import ConfigGenerator
from scholar_mine.agent.prompts import INTENT_PARSE_PROMPT
from scholar_mine.utils.logger import Logger

log = Logger.get()

@dataclass
class PlanResult:
    research_direction: str
    domain: str = ""
    subdomain: str = ""
    paper_count: int = 1500
    keywords: List[str] = field(default_factory=list)
    schema: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    intent: Dict[str, Any] = field(default_factory=dict)
    config_path: Optional[Path] = None

class ResearchPlanner:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.keyword_expander = KeywordExpander(llm_client)
        self.schema_inferrer = SchemaInferrer(llm_client)

    def parse_intent(self, user_input: str) -> dict:
        prompt = INTENT_PARSE_PROMPT.format(user_input=user_input)
        response = self.llm.chat(
            system_prompt="You are a research planning assistant. Parse research queries into structured JSON.",
            user_prompt=prompt,
        )
        import json, re
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            m = re.search(r'\{[\s\S]*\}', response)
            if m:
                return json.loads(m.group())
        return {"domain": user_input, "paper_count": 1500}

    def plan(self, user_input: str, paper_count: int = 1500, schema_id: Optional[str] = None) -> PlanResult:
        log.info(f"Planning research: {user_input}")
        intent = self.parse_intent(user_input)
        intent.setdefault("paper_count", paper_count)

        direction = f"{intent.get('domain', '')} {intent.get('subdomain', '')}".strip() or user_input
        keywords = self.keyword_expander.expand(direction, count=25)

        if schema_id:
            schema = self.schema_inferrer.load_preset(schema_id)
            if schema is None:
                log.warning(f"Schema {schema_id} not found, inferring...")
                schema = self.schema_inferrer.infer(direction, field_count=15)
        else:
            schema = self.schema_inferrer.infer(direction, field_count=15)

        config = ConfigGenerator.build_config_dict(
            research_direction=direction,
            keywords=keywords,
            schema=schema,
            paper_count=intent.get("paper_count", paper_count),
            year_start=intent.get("year_start"),
            year_end=intent.get("year_end"),
        )

        return PlanResult(
            research_direction=direction,
            domain=intent.get("domain", ""),
            subdomain=intent.get("subdomain", ""),
            paper_count=intent.get("paper_count", paper_count),
            keywords=keywords,
            schema=schema,
            config=config,
            intent=intent,
        )
