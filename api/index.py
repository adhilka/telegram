import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler

from google import genai


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

MODEL = "gemini-3.8-flash"

client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================
# TEMPORARY MEMORY
# ============================================================
#
# IMPORTANT:
# Vercel Functions are serverless.
# This dictionary is NOT guaranteed to survive deployments,
# cold starts, or different function instances.
#
# It is useful for testing Phase 2.
# Persistent database memory comes in the next phase.
#

CONVERSATIONS = {}


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are an advanced AI assistant running inside a Telegram bot.

Your job is to be useful, accurate, friendly and concise.

Capabilities available to you may include:

- General conversation
- Programming
- Debugging
- Mathematics
- Python execution
- Web research
- Current information
- URL analysis
- Summaries
- Explanations
- Brainstorming
- Technical help

IMPORTANT:

1. Never claim you used a tool if you did not.
2. If web search is enabled, use current information when appropriate.
3. If code execution is enabled, actually use it when calculations,
   data processing, or verification would benefit from execution.
4. Explain programming answers clearly.
5. Put programming code inside Markdown code blocks.
6. Do not reveal API keys, environment variables, or secrets.
7. If something cannot be verified, say so.
8. Keep normal Telegram responses reasonably concise.
"""


# ============================================================
# TELEGRAM API
# ============================================================

def telegram(method, data):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    request = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def send_typing(chat_id):
    try:
        telegram(
            "sendChatAction",
            {
                "chat_id": chat_id,
                "action": "typing"
            }
        )
    except Exception:
        pass


def send_message(chat_id, text):
    if not text:
        text = "I couldn't generate a response."

    # Telegram messages should stay below the message-size limit.
    # Split long AI responses into several messages.
    chunks = []

    while len(text) > 3900:
        cut = text.rfind("\n", 0, 3900)

        if cut < 1000:
            cut = 3900

        chunks.append(text[:cut])
        text = text[cut:].lstrip()

    if text:
        chunks.append(text)

    for chunk in chunks:
        telegram(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": chunk
            }
        )


# ============================================================
# GEMINI
# ============================================================

def run_gemini(
    chat_id,
    prompt,
    use_search=False,
    use_code=False,
    use_url=False
):
    tools = []

    if use_search:
        tools.append(
            {
                "type": "google_search"
            }
        )

    if use_code:
        tools.append(
            {
                "type": "code_execution"
            }
        )

    if use_url:
        tools.append(
            {
                "type": "url_context"
            }
        )

    previous_id = CONVERSATIONS.get(chat_id)

    request = {
        "model": MODEL,
        "input": prompt,
        "system_instruction": SYSTEM_PROMPT
    }

    if previous_id:
        request["previous_interaction_id"] = previous_id

    if tools:
        request["tools"] = tools

    interaction = client.interactions.create(**request)

    # Save the latest interaction for this Telegram chat.
    CONVERSATIONS[chat_id] = interaction.id

    return interaction.output_text


# ============================================================
# HELP
# ============================================================

def help_text():
    return """🤖 AI ASSISTANT

💬 Normal chat
Just send a message.

🧠 Conversation
/new
Start a fresh conversation.

/status
Show bot status.

🔎 Research
/research <question>
Use Google Search for current information.

💻 Coding
/code <request>
Use Gemini's Python execution environment.

🔗 URL
/url <URL + question>
Analyze information from a public URL.

🧮 Calculator
/calc <math problem>
Use Python to calculate and verify.

Examples:

/research What are the latest developments in space exploration?

/code Find the bug in this Python program: ...

/url https://example.com summarize this page

/calc 987654321 * 123456789

✨ More coming:
• Persistent database memory
• File uploads
• PDF analysis
• OpenRouter fallback
• Multiple AI models
• Agent workflows
• Admin controls
• Usage statistics
"""


# ============================================================
# COMMAND HELPERS
# ============================================================

def command_argument(text, command):
    return text[len(command):].strip()


# ============================================================
# WEBHOOK
# ============================================================

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

        self.wfile.write(
            b"Telegram AI Bot is running."
        )

    def do_POST(self):

        chat = {}

        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            raw_body = self.rfile.read(length)

            update = json.loads(
                raw_body.decode("utf-8")
            )

            message = update.get(
                "message",
                {}
            )

            chat = message.get(
                "chat",
                {}
            )

            if not chat:
                self.finish()
                return

            chat_id = chat["id"]

            text = message.get(
                "text",
                ""
            ).strip()

            if not text:
                self.finish()
                return

            send_typing(chat_id)

            # ==================================================
            # /start
            # ==================================================

            if text == "/start":

                send_message(
                    chat_id,
                    "👋 Heyyy!\n\n"
                    "I'm your AI assistant 🤖✨\n\n"
                    "Send me a message or type /help."
                )

            # ==================================================
            # /help
            # ==================================================

            elif text == "/help":

                send_message(
                    chat_id,
                    help_text()
                )

            # ==================================================
            # /new
            # ==================================================

            elif text == "/new":

                CONVERSATIONS.pop(
                    chat_id,
                    None
                )

                send_message(
                    chat_id,
                    "🆕 New conversation started!\n\n"
                    "Your previous AI context has been cleared."
                )

            # ==================================================
            # /status
            # ==================================================

            elif text == "/status":

                memory_status = (
                    "active"
                    if chat_id in CONVERSATIONS
                    else "empty"
                )

                send_message(
                    chat_id,
                    "🟢 Bot online\n\n"
                    f"Model: {MODEL}\n"
                    f"Conversation memory: {memory_status}\n"
                    "Google Search: available\n"
                    "Python execution: available\n"
                    "URL analysis: available"
                )

            # ==================================================
            # /research
            # ==================================================

            elif text.startswith("/research"):

                prompt = command_argument(
                    text,
                    "/research"
                )

                if not prompt:

                    send_message(
                        chat_id,
                        "🔎 Usage:\n\n"
                        "/research your question"
                    )

                else:

                    answer = run_gemini(
                        chat_id,
                        prompt,
                        use_search=True
                    )

                    send_message(
                        chat_id,
                        "🔎 " + answer
                    )

            # ==================================================
            # /code
            # ==================================================

            elif text.startswith("/code"):

                prompt = command_argument(
                    text,
                    "/code"
                )

                if not prompt:

                    send_message(
                        chat_id,
                        "💻 Usage:\n\n"
                        "/code your programming request"
                    )

                else:

                    answer = run_gemini(
                        chat_id,
                        prompt,
                        use_code=True
                    )

                    send_message(
                        chat_id,
                        "💻 " + answer
                    )

            # ==================================================
            # /url
            # ==================================================

            elif text.startswith("/url"):

                prompt = command_argument(
                    text,
                    "/url"
                )

                if not prompt:

                    send_message(
                        chat_id,
                        "🔗 Usage:\n\n"
                        "/url https://example.com summarize this"
                    )

                else:

                    answer = run_gemini(
                        chat_id,
                        prompt,
                        use_url=True
                    )

                    send_message(
                        chat_id,
                        "🔗 " + answer
                    )

            # ==================================================
            # /calc
            # ==================================================

            elif text.startswith("/calc"):

                prompt = command_argument(
                    text,
                    "/calc"
                )

                if not prompt:

                    send_message(
                        chat_id,
                        "🧮 Usage:\n\n"
                        "/calc 123456 * 987654"
                    )

                else:

                    answer = run_gemini(
                        chat_id,
                        "Calculate and verify this mathematically. "
                        "Use Python code execution when useful.\n\n"
                        + prompt,
                        use_code=True
                    )

                    send_message(
                        chat_id,
                        "🧮 " + answer
                    )

            # ==================================================
            # NORMAL AI CHAT
            # ==================================================

            else:

                answer = run_gemini(
                    chat_id,
                    text
                )

                send_message(
                    chat_id,
                    answer
                )

        except Exception as error:

            print(
                "BOT ERROR:",
                repr(error)
            )

            try:

                if chat:

                    send_message(
                        chat["id"],
                        "😭 Something went wrong.\n\n"
                        "Please try again."
                    )

            except Exception:
                pass

        self.finish()

    def finish(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain"
        )
        self.end_headers()

        self.wfile.write(
            b"OK"
        )
