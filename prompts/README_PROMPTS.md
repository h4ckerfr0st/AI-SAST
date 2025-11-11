PROMPTS DIRECTORY
=================

Each stack folder contains multiple prompt templates you can edit. Use the --prompt-file argument to pass a custom prompt to the analyzer script.

Usage examples:

# Use a stack default prompt (no change required)
python LLM/llm_analysis.py --stack php

# Use a specific prompt file
python LLM/llm_analysis.py --stack php --prompt-file prompts/php/triage.txt

Notes:
- The analyzer will replace the placeholders in the prompt with the actual finding content (rule_id, severity, message, path, start, end, code_snippet).
- Prompts expect the model to return STRICT JSON. If the model returns code fences, the analyzer will try to strip them before parsing.
- Edit prompts to tune the model's behavior for your projects.
