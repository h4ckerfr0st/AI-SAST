import json
import os
import argparse
from textwrap import dedent
import requests

#BY FROSTY
#Luis Giordano
#Free as it should be

SEMGREP_JSON_PATH = "semgrep_results.json"

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.1"

MAX_FINDINGS = 20


def load_semgrep_results(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Semgrep JSON not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_code_snippet(finding: dict, repo_root: str = ".") -> str:
    """
    Read the file and extract a snippet around the finding lines.
    """
    path = finding.get("path")
    if not path:
        return "Code snippet not available."

    file_path = os.path.join(repo_root, path)
    if not os.path.exists(file_path):
        return f"File not found: {file_path}"

    start_line = finding.get("start", {}).get("line", 1)
    end_line = finding.get("end", {}).get("line", start_line)

    context_before = 5
    context_after = 5

    start_index = max(1, start_line - context_before)
    end_index = end_line + context_after

    lines = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, start=1):
            if start_index <= i <= end_index:
                lines.append(f"{i:4}: {line.rstrip()}")

    return "\n".join(lines) if lines else "Code snippet not available."


def stack_context_text(stack: str) -> str:
    """
    Returns a short description of the tech stack to inject into the prompt.
    """
    if stack == "php":
        return (
            "The project is a PHP web application (often Laravel-style), "
            "using typical PHP patterns such as controllers, views/blades, and raw PHP scripts."
        )
    elif stack == "java":
        return (
            "The project is a Java backend application, typically Spring or Spring Boot, "
            "using annotations, controllers, services, repositories, and build tooling like Maven/Gradle."
        )
    elif stack == "node":
        return (
            "The project is a Node.js backend or full-stack application, typically using Express.js "
            "or similar frameworks, npm/yarn for dependencies, and JavaScript/TypeScript on the server side."
        )
    elif stack == "python":
        return (
            "The project is a Python 3 application or API, often using frameworks like Django, "
            "Flask, or FastAPI, and pip/pip-tools/poetry for dependency management."
        )
    else:
        return "The project is a generic web/application codebase."


def remediation_style_hint(stack: str) -> str:

    if stack == "php":
        return (
            "For remediation, prefer secure PHP/Laravel patterns: parameterized queries (PDO/Eloquent), "
            "proper escaping in Blade templates, CSRF tokens, validation rules, and configuration best practices."
        )
    elif stack == "java":
        return (
            "For remediation, prefer secure Java/Spring patterns: use Spring Security, Bean Validation, "
            "prepared statements, proper @RequestParam/@PathVariable validation, and safe configuration."
        )
    elif stack == "node":
        return (
            "For remediation, prefer secure Node.js patterns: parameterized queries, input validation "
            "with libraries like Joi/Zod, proper use of helmet/csrf middlewares, and safe handling of "
            "environment variables and secrets."
        )
    elif stack == "python":
        return (
            "For remediation, prefer secure Python patterns: parameterized queries via ORM (Django ORM, SQLAlchemy), "
            "input validation, CSRF protection, proper use of framework security settings, and safe configuration."
        )
    else:
        return "For remediation, follow secure coding best practices for the relevant language and framework."


def build_prompt(finding: dict, code_snippet: str, stack: str) -> str:
    rule_id = finding.get("check_id", "unknown_rule")
    message = finding.get("extra", {}).get("message", "")
    severity = finding.get("extra", {}).get("severity", "UNKNOWN")
    path = finding.get("path", "unknown_file")
    start = finding.get("start", {})
    end = finding.get("end", {})
    start_line = start.get("line")
    end_line = end.get("line")

    stack_context = stack_context_text(stack)
    remediation_hint = remediation_style_hint(stack)

    prompt = dedent(
        f"""
        You are an Application Security engineer helping to triage Semgrep findings
        in a codebase.

        Technology context:
        - {stack_context}

        I will give you:
        - The Semgrep rule id
        - The Semgrep message and severity
        - The file and line range
        - The code snippet

        Your tasks:
        1. Decide if this is likely a TRUE POSITIVE or FALSE POSITIVE from a real-world
           AppSec perspective (even if the project might be a lab or intentionally vulnerable).
        2. Explain why in 1–3 short paragraphs, referencing the given tech stack when relevant.
        3. If it is a TRUE POSITIVE, propose a secure remediation in idiomatic {stack.upper()}-stack code.
           {remediation_hint}
        4. If it is a FALSE POSITIVE, explain why and suggest how we could tune the rule or code
           to avoid noise in the future.

        Answer in *strict* JSON only, with this structure:

        {{
          "classification": "TRUE_POSITIVE" or "FALSE_POSITIVE",
          "reasoning": "short explanation",
          "remediation": "code-level remediation suggestion or 'N/A' if FP",
          "notes_for_rule_tuning": "ideas for improving Semgrep rule or code patterns"
        }}

        --- Semgrep finding ---
        Rule ID: {rule_id}
        Severity: {severity}
        Message: {message}
        File: {path}
        Lines: {start_line}–{end_line}

        --- Code snippet ---
        {code_snippet}
        """
    )
    return prompt


def call_ollama(prompt: str) -> str:
    """
    Call Ollama's /api/chat endpoint with the given prompt and return the content string.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "You are a senior Application Security engineer."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()

    return data["message"]["content"].strip()


def analyze_finding_with_llm(finding: dict, stack: str) -> dict:
    code_snippet = extract_code_snippet(finding)
    prompt = build_prompt(finding, code_snippet, stack)

    try:
        content = call_ollama(prompt)
    except Exception as e:
        return {
            "error": "ollama_request_failed",
            "details": str(e),
        }

    try:
        txt = content
        if txt.startswith("```"):
            parts = txt.split("```")
            if len(parts) >= 2:
                txt = parts[1]
            txt = txt.lstrip()
            if txt.lower().startswith("json"):
                txt = txt[4:].lstrip()

        parsed = json.loads(txt)
        return parsed
    except Exception:
        return {"raw_response": content}


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Semgrep findings with a local Ollama LLM."
    )
    parser.add_argument(
        "--stack",
        choices=["php", "java", "node", "python"],
        default="php",
        help="Tech stack context for the LLM (php, java, node, python).",
    )
    args = parser.parse_args()
    stack = args.stack

    data = load_semgrep_results(SEMGREP_JSON_PATH)

    results = data.get("results", [])
    if not results:
        print("No Semgrep results found in JSON.")
        return

    if len(results) > MAX_FINDINGS:
        print(f"Total findings: {len(results)}. Limiting to first {MAX_FINDINGS}.")
        results = results[:MAX_FINDINGS]

    print(
        f"Analyzing {len(results)} findings with Ollama model '{OLLAMA_MODEL}' "
        f"for stack '{stack}'...\n"
    )

    enriched = []

    for idx, finding in enumerate(results, start=1):
        print(
            f"=== Finding {idx}/{len(results)}: "
            f"{finding.get('check_id')} in {finding.get('path')} ==="
        )
        llm_result = analyze_finding_with_llm(finding, stack)
        enriched_item = {
            "semgrep_finding": finding,
            "llm_analysis": llm_result,
        }
        enriched.append(enriched_item)

        print(json.dumps(llm_result, indent=2, ensure_ascii=False))
        print("\n")

    output_path = f"semgrep_results_with_llm_ollama_{stack}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)

    print(f"All done. Enriched results saved to {output_path}")


if __name__ == "__main__":
    main()
