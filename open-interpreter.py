import json
import time
import asyncio
import aiohttp
from interpreter import interpreter
import os
from typing import Optional
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

class OpenInterpreterChatAgent:
    def __init__(self, ollama_url: str = None, ollama_model: str = None):
        self.ollama_url = ollama_url or OLLAMA_BASE_URL
        self.ollama_model = ollama_model or OLLAMA_MODEL
        self.session = None
        self.setup_interpreter()
        print(f"[System] Using Ollama at {self.ollama_url} with model '{self.ollama_model}'")

    def setup_interpreter(self):
        interpreter.auto_run = True
        interpreter.safe_mode = "off"
        interpreter.local = True
        interpreter.offline = True

        interpreter.llm.model = f"ollama/{self.ollama_model}"
        interpreter.llm.api_base = self.ollama_url
        interpreter.llm.supports_vision = False
        interpreter.llm.supports_functions = False

        interpreter.system_message = (
            "You are a helpful assistant that can execute code and perform file operations. "
            "When asked to perform a task, write and execute the necessary code. "
            "Be direct and execute tasks without asking for confirmation."
            "Never return empty json responses, always provide a valid JSON object."
        )
        print("[System] Open Interpreter configured for local Ollama use")

    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close_session(self):
        if self.session:
            await self.session.close()

    def append_to_json_log(self, filename: str, data: dict):
        filepath = os.path.join(LOG_DIR, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump([data], f, indent=2, ensure_ascii=False)
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            existing_data.append(data)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)

    async def stream_ollama_response(self, message: str) -> str:
        await self.create_session()

        headers = {"Content-Type": "application/json"}

        system_prompt = (
            "When asked for code, provide clean, well-formatted examples using the appropriate language. Add comments if necessary."
        )

        payload = {
            "model": self.ollama_model,
            "prompt": f"{system_prompt}\n\nUser: {message}\nAssistant:",
            "stream": True,
            "options": {
                "temperature": 0.4,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": 4096
            }
        }

        complete_response = ""
        full_raw_output = ""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            async with self.session.post(f"{self.ollama_url}/api/generate", json=payload, headers=headers) as resp:
                async for line in resp.content:
                    if line:
                        data = line.decode("utf-8").strip()
                        full_raw_output += data + "\n"
                        try:
                            chunk = json.loads(data)
                            token = chunk.get("response", "")
                            if token:
                                print(token, end="", flush=True)
                                complete_response += token
                        except json.JSONDecodeError:
                            continue
            print()

            filtered_response = complete_response.replace("<think>", "").replace("</think>", "").strip()

            clean_data = {
                "timestamp": timestamp,
                "user": message,
                "response": filtered_response
            }

            raw_data = {
                "timestamp": timestamp,
                "user": message,
                "response": complete_response.strip()
            }

            self.append_to_json_log("ollama_response_clean_log.json", clean_data)
            self.append_to_json_log("ollama_response_raw_log.json", raw_data)

            return filtered_response or "I understand. How can I help you?"
        except Exception as e:
            print(f"[Error] Ollama streaming failed: {e}")
            return f"Error connecting to Ollama: {e}"

    def execute_with_interpreter(self, task: str) -> str:
        print(f"\n[OpenInterpreter] Executing: {task}")
        try:
            interpreter.messages = []
            result = interpreter.chat(task, display=False)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(result, list) and result:
                last = result[-1]
                if isinstance(last, dict):
                    response = last.get("content") or last.get("output") or "Task completed."
                else:
                    response = str(last)
            else:
                response = "Task completed."
            log_data = {
                "timestamp": timestamp,
                "user": task,
                "response": response
            }
            self.append_to_json_log("open_interpreter_log.json", log_data)
            return response
        except Exception as e:
            return f"[Error] Interpreter failed: {e}"

    def is_file_task(self, msg: str) -> bool:
        keywords = ["file", "folder", "create", "write", "save", "list", "delete"]
        return any(kw in msg.lower() for kw in keywords)

    async def process_message(self, message: str, force_interpreter: bool = False) -> str:
        if force_interpreter or self.is_file_task(message):
            print("[Routing] Using Open Interpreter")
            return self.execute_with_interpreter(message)
        else:
            print("[Routing] Using Ollama")
            return await self.stream_ollama_response(message)

    async def interactive_mode(self):
        print("\n=== Chat Agent (Ollama + Open Interpreter) ===")
        print("Commands: /oi <msg>, /model, /help, /quit")
        try:
            while True:
                msg = input("You: ").strip()
                if msg in ["/quit", "exit"]:
                    break
                elif msg == "/help":
                    print("/oi <msg>: Force interpreter\n/model: Show model info\n/quit: Exit")
                elif msg == "/model":
                    print(f"Using model: {self.ollama_model} at {self.ollama_url}")
                elif msg.startswith("/oi "):
                    task = msg[4:].strip()
                    result = self.execute_with_interpreter(task)
                    print(f"\nAssistant: {result}")
                elif msg:
                    response = await self.process_message(msg)
                    print(f"\nAssistant: {response}")
        except Exception as e:
            print(f"[Error] Chat loop failed: {e}")
        finally:
            await self.close_session()


class ChatAgent:
    def __init__(self, ollama_url: str = None, ollama_model: str = None):
        self.core_agent = OpenInterpreterChatAgent(ollama_url, ollama_model)

    async def chat_loop(self):
        await self.core_agent.interactive_mode()


async def main():
    agent = ChatAgent()
    await agent.chat_loop()


if __name__ == "__main__":
    asyncio.run(main())
