# OLLAMA_OPEN-INTERPRETER

# OLLAMA Open Interpreter Agent

A local AI assistant that combines the power of [Ollama](https://ollama.com) (for language modeling) with [Open Interpreter](https://github.com/KillianLucas/open-interpreter) (for code and task execution). This hybrid agent can:

- Chat naturally using a local LLM via Ollama
- Run Python code and system-level tasks using Open Interpreter
- Automatically log all interactions in JSON format 
---

## Features

- ✅ Use **Ollama models** (like `llama2`, `phi3`, `mistral`, etc.)
- ✅ Use **Open Interpreter** for task execution (e.g., file management, Python execution)
- ✅ **Automatic logging** of responses into JSON files (`logs/`)
- ✅ Differentiates between LLM queries and code tasks
- ✅ Easy interactive CLI with commands like `/oi` and `/model`

---

## 📦 Requirements

Install dependencies using:

```bash
pip install -r requirements.txt
```
or
```bash
pip install aiohttp python-dotenv open-interpreter

