````markdown
#  Semgrep + LLM Security Analyzer (Ollama Edition)

This project connects **Semgrep** static analysis findings to a **local Large Language Model (LLM)** via **Ollama**, so you can triage and remediate vulnerabilities **without sending code to external APIs**.

It supports multiple stacks via a simple CLI flag:

- `php`   → PHP / Laravel
- `java`  → Java / Spring
- `node`  → Node.js / npm
- `python` → Python 3 / pip

The core logic lives in:  

`LLM/llm_analysis.py`

Semgrep produces JSON findings, and the script sends each finding (plus code context) to a local LLM. The LLM responds with:

- `classification` → TRUE_POSITIVE / FALSE_POSITIVE  
- `reasoning` → why it matters (or not)  
- `remediation` → how to fix  
- `notes_for_rule_tuning` → suggestions to reduce noise  

All of this is stored in an enriched JSON file, ready for CI/CD, dashboards, or Jira.

---

##  Project Structure (simplified)

```text
.
├── LLM/
│   └── llm_analysis.py         # Main script that talks to Ollama
├── semgrep_results.json        # Semgrep output (generated)
├── semgrep_results_with_llm_ollama_<stack>.json   # Enriched output (generated)
├── requirements.txt
└── README.md
````

> Replace `<stack>` with `php`, `java`, `node`, or `python`.

---

## ⚙️ Prerequisites

You’ll need:

* **Python 3.8+**
* **Semgrep** installed locally
* **Ollama** installed and running
* A model pulled in Ollama (e.g. `llama3.1`)

### 1. Install Semgrep

**Option A – Homebrew (macOS)**

```bash
brew install semgrep
```

**Option B – pip / pipx**

```bash
# pipx (recommended if available)
pipx install semgrep

# OR classic pip (global / user)
pip install --user semgrep
```

Check it worked:

```bash
semgrep --version
```

---

### 2. Install and set up Ollama

1. Download & install from the [Ollama website](https://ollama.ai) (macOS / Linux).
2. Pull a model (for example):

```bash
ollama pull llama3.1
```

3. Make sure the Ollama service is running (usually it auto-starts).

> The script defaults to `OLLAMA_MODEL = "llama3.1"`.
> You can change this inside `LLM/llm_analysis.py` if you use another model.

---

### 3. Python virtual environment + dependencies

From the **root of this repo**:

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

That will install the Python dependencies (currently just `requests` for the HTTP call to Ollama).

Anytime you come back to the project, re-activate:

```bash
source .venv/bin/activate
```

---

##  How It Works (High-level)

1. You run **Semgrep** on your codebase and output JSON.
2. You run `LLM/llm_analysis.py` with a `--stack` argument.
3. The script:

   * Reads `semgrep_results.json`
   * Extracts code snippets (with some context lines)
   * Builds a stack-aware prompt (PHP, Java, Node, or Python)
   * Sends it to a local LLM via Ollama
   * Parses the JSON-like response
   * Writes an enriched JSON file with both Semgrep data and LLM analysis

---

##  Usage: End-to-end Examples

All commands assume you are in the **root of the repo**, with `.venv` activated.

---

### 1️ PHP / Laravel (or generic PHP)

Run Semgrep:

```bash
semgrep \
  --config p/php \
  --config p/owasp-top-ten \
  --json \
  --output semgrep_results.json \
  .
```

Then run the LLM analysis:

```bash
python LLM/llm_analysis.py --stack php
```

This will:

* Analyze findings as PHP/Laravel-style code
* Print results to the console
* Save enriched results to:

```text
semgrep_results_with_llm_ollama_php.json
```

---

###  Java / Spring

Run Semgrep (example config):

```bash
semgrep \
  --config p/java \
  --json \
  --output semgrep_results.json \
  .
```

Then:

```bash
python LLM/llm_analysis.py --stack java
```

Output file:

```text
semgrep_results_with_llm_ollama_java.json
```

---

###  Node.js / npm (Express, Nest, etc.)

Run Semgrep:

```bash
semgrep \
  --config p/nodejs \
  --json \
  --output semgrep_results.json \
  .
```

Then:

```bash
python LLM/llm_analysis.py --stack node
```

Output file:

```text
semgrep_results_with_llm_ollama_node.json
```

---

###  Python 3 / pip (Django, Flask, FastAPI, etc.)

Run Semgrep:

```bash
semgrep \
  --config p/python \
  --json \
  --output semgrep_results.json \
  .
```

Then:

```bash
python LLM/llm_analysis.py --stack python
```

Output file:

```text
semgrep_results_with_llm_ollama_python.json
```

> Note: the exact Semgrep configs (`p/java`, `p/nodejs`, `p/python`) are just examples.
> You can plug in any Semgrep rulesets or custom config you like.

---

##  `llm_analysis.py` Behavior Details

Key things the script does:

* Reads `semgrep_results.json`

* Limits the number of processed findings (to avoid huge runs):

  ```python
  MAX_FINDINGS = 20
  ```

  You can change this inside `LLM/llm_analysis.py`.

* For each finding:

  * Reads the source file

  * Extracts ~5 lines before and after the finding line range

  * Builds a **stack-specific prompt**:

    * PHP: parameterized queries via Eloquent/PDO, Blade escaping, CSRF, validation.
    * Java: Spring Security, Bean Validation, prepared statements, safe controllers.
    * Node: Express middlewares, input validation, helmet, CSRF, safe env/secrets handling.
    * Python: Django/Flask/FastAPI security features, ORMs, CSRF, secure settings.

  * Calls Ollama’s `/api/chat` endpoint:

    ```python
    POST http://localhost:11434/api/chat
    ```

  * Asks the model to respond in **strict JSON**:

    ```json
    {
      "classification": "TRUE_POSITIVE",
      "reasoning": "...",
      "remediation": "...",
      "notes_for_rule_tuning": "..."
    }
    ```

  * Tries to parse it as JSON (even if wrapped in ```json fences)

  * Falls back to returning `raw_response` if parsing fails

* Writes all combined data to:

  ```text
  semgrep_results_with_llm_ollama_<stack>.json
  ```

---

##  Example Enriched Output

A single entry in `semgrep_results_with_llm_ollama_php.json` will look like:

```json
{
  "semgrep_finding": {
    "check_id": "php.lang.security.injection.tainted-filename.tainted-filename",
    "path": "instructions.php",
    "start": { "line": 42, "col": 5 },
    "end": { "line": 45, "col": 1 },
    "extra": {
      "message": "User-controlled data flows into a file path.",
      "severity": "ERROR"
    }
    // ... other Semgrep metadata ...
  },
  "llm_analysis": {
    "classification": "TRUE_POSITIVE",
    "reasoning": "The filename comes directly from user input ...",
    "remediation": "Use a whitelist of allowed filenames or map identifiers...",
    "notes_for_rule_tuning": "Rule could ignore cases where the value is validated..."
  }
}
```

You can then:

* Parse this JSON in another script
* Generate Markdown reports
* Create Jira tickets per TRUE_POSITIVE, with ready-made remediation text

---

##  Customization

You can tweak several things inside `LLM/llm_analysis.py`:

* **Model**:

  ```python
  OLLAMA_MODEL = "llama3.1"
  ```

* **Max findings to analyze**:

  ```python
  MAX_FINDINGS = 20
  ```

* **Stack descriptions & remediation hints**:

  Functions:

  ```python
  stack_context_text(stack: str) -> str
  remediation_style_hint(stack: str) -> str
  ```

  These control the “persona” and remediation style per stack.

* **Prompt structure**:

  The function:

  ```python
  build_prompt(finding, code_snippet, stack)
  ```

  If you want more or less detail, adjust here.

---

##  Troubleshooting

### “No Semgrep results found in JSON.”

* Check that `semgrep_results.json` exists in the project root.
* Ensure you used the `--json --output semgrep_results.json` flags.

### Connection errors to Ollama

* Confirm Ollama is running:

  ```bash
  ps aux | grep ollama
  ```

* Test the API:

  ```bash
  curl http://localhost:11434/api/tags
  ```

* Ensure the model is pulled:

  ```bash
  ollama pull llama3.1
  ```

### Model returns non-JSON output

* The script already tries to strip ```json fences.
* Sometimes smaller models hallucinate formatting.
  You can:

  * Use a stronger model in Ollama.
  * Tighten the instructions in `build_prompt()`.
  * Add a fallback that logs bad responses for later inspection.

---

##  `requirements.txt`

Place this file in the repo root:

```txt
requests>=2.31.0
```

If later you add more Python tooling (e.g., for generating Markdown reports, pushing to Jira, etc.), update this file and rerun:

```bash
pip install -r requirements.txt
```

---

##  Who Is This For?

* Security Engineers
* DevSecOps / AppSec folks
* Developers who want **contextual, stack-aware explanations** of static analysis findings, locally.

No cloud API keys. No code leaving your machine. Just **Semgrep + Ollama + Python**.

---

Happy hacking — and if you ever want a `report_to_markdown.py` or a Jira integration script for this repo, we can bolt that on next. 😈🔐

```

::contentReference[oaicite:0]{index=0}
```
