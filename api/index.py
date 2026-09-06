import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler
from google import genai

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_KEY = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=GEMINI_KEY)

MODEL = "gemini-3.8-flash"

SYSTEM_PROMPT = """
You are the AI assistant inside a Telegram bot.

Be helpful, friendly and concise.
You can help with:
- General questions
- Programming and debugging
- Explaining code
- Writing code
- Mathematics
- Summaries
- Brainstorming
- Translation
- Research
- Technical explanations

When giving code, use proper Markdown code blocks.
Never claim that you performed an action if you did not actually perform it.
"""


def telegram(method, data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    request = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read())


def send_message(chat_id, text):
    # Telegram messages have a practical length limit.
    if len(text) > 4000:
        text = text[:4000] + "\n\n…message shortened."

    telegram("sendMessage", {
        "chat_id": chat_id,
        "text": text
    })


def ask_gemini(prompt):
    response = client.interactions.create(
        model=MODEL,
        input=prompt,
        system_instruction=SYSTEM_PROMPT
    )

    return response.output_text


def help_message():
    return """🤖 AI Bot

Commands:

/start — Start the bot
/help — Show this help
/new — Start a fresh AI conversation
/code — Coding assistant
/research — Research mode

Or simply send me a message.

✨ More tools are coming soon:
• Coding agent
• Web research
• Code execution
• File analysis
• AI model switching
• Memory
• Utilities
"""


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            update = json.loads(body)

            message = update.get("message", {})
            chat = message.get("chat", {})
            text = message.get("text", "")

            if not chat:
                self.send_response(200)
                self.end_headers()
                return

            chat_id = chat["id"]

            if text == "/start":
                send_message(
                    chat_id,
                    "👋 Hey! I'm your AI assistant.\n\n"
                    "Send me anything or type /help."
                )

            elif text == "/help":
                send_message(chat_id, help_message())

            elif text == "/new":
                send_message(
                    chat_id,
                    "🆕 Fresh conversation mode coming next!"
                )

            elif text.startswith("/code"):
                prompt = text[5:].strip()

                if not prompt:
                    send_message(
                        chat_id,
                        "💻 Try:\n/code explain this Python code..."
                    )
                else:
                    reply = ask_gemini(
                        "Act as an expert programming assistant.\n\n"
                        + prompt
                    )
                    send_message(chat_id, reply)

            elif text.startswith("/research"):
                prompt = text[9:].strip()

                if not prompt:
                    send_message(
                        chat_id,
                        "🔎 Try:\n/research latest information about..."
                    )
                else:
                    reply = ask_gemini(
                        "Act as a research assistant. "
                        "Give a clear, structured answer and "
                        "separate known facts from uncertainty.\n\n"
                        + prompt
                    )
                    send_message(chat_id, reply)

            elif text:
                reply = ask_gemini(text)
                send_message(chat_id, reply)

        except Exception as e:
            print("ERROR:", repr(e))

            try:
                if chat:
                    send_message(
                        chat["id"],
                        "😭 Something went wrong. Try again."
                    )
            except Exception:
                pass

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"AI Telegram Bot is running.")
