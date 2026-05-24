"""Prompt templates for the ScholarMine Agent layer."""

KEYWORD_EXPANSION_PROMPT = """You are a research librarian expert. Given a research direction, generate {count} professional search keywords.

Research direction: {research_direction}
Mode: {mode}

Requirements:
- Generate EXACTLY {count} keywords.
- Include: broad terms, narrow technical terms, synonym variations, abbreviation + full-form pairs.
- For "broad" mode: cover multiple sub-topics and neighboring fields.
- For "focused" mode: deep, highly specific terminology.
- Output as a JSON array of strings. No markdown, no commentary."""

SCHEMA_INFERENCE_PROMPT = """You are a domain expert. For the research area described below, define {field_count} structured extraction fields.

Domain description: {domain_description}

Output a JSON array of field definitions. Each field has:
- "name": display name (short, human-readable)
- "key": machine key (snake_case, no spaces)
- "type": "string" | "numeric" | "categorical"
- "description": one-line explanation of what to extract
- "placeholder": "-" (what to use when field is missing)

The fields should capture the most important experimental parameters, performance metrics, material properties, and key findings for this domain.
Output ONLY a valid JSON array. No markdown fences, no commentary."""

INTENT_PARSE_PROMPT = """Parse the user's research query into structured parameters.

User input: {user_input}

Output a JSON object with these fields:
- "domain": high-level research area
- "subdomain": specific sub-topic
- "year_start": start year (null if not specified)
- "year_end": end year (null if not specified)
- "paper_count": target number of papers (default 1500)
- "extraction_focus": what kind of data to extract (e.g., "experimental performance metrics", "synthesis conditions", "material properties")
- "keywords_hint": any explicit keywords the user mentioned
- "notes": additional constraints or preferences

Output ONLY valid JSON. No markdown."""

PIPELINE_CONFIG_PROMPT = """Based on the following research plan, recommend pipeline settings.

Plan: {plan_summary}

Output a JSON object with:
- "keyword_mode": "broad" or "focused"
- "platform_priority": ordered list of recommended platforms from: arxiv, semantic_scholar, crossref, pubmed, scihub, core, chemrxiv
- "filter_strictness": "loose" (keep >50% relevance) | "moderate" (keep >70%) | "strict" (keep >90%)
- "batch_size": recommended batch size for LLM extraction (20-50)
- "estimated_runtime_minutes": rough estimate
- "notes": any warnings or suggestions

Output ONLY valid JSON."""
