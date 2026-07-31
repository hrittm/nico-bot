import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Import Nico's system instruction prompt from persona.py
from persona import NICO_SYSTEM_INSTRUCTION

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Optional dedicated channel ID (Set in Render environment variables or leave 0)
DEDICATED_CHANNEL_ID = int(os.getenv('DEDICATED_CHANNEL_ID', '0'))

# Initialize Google GenAI Client securely
if not GEMINI_API_KEY:
    raise ValueError("CRITICAL: GEMINI_API_KEY environment variable is missing!")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Text memory buffer per channel ( capped at 20 messages / 10 turns )
MAX_HISTORY = 20
channel_memories = {}

def get_memory(channel_id: int):
    if channel_id not in channel_memories:
        channel_memories[channel_id] = []
    return channel_memories[channel_id]

def add_text_memory(channel_id: int, role: str, text: str):
    history = get_memory(channel_id)
    history.append(
        types.Content(
            role=role,
            parts=[types.Part.from_text(text=text)]
        )
    )
    if len(history) > MAX_HISTORY:
        channel_memories[channel_id] = history[-MAX_HISTORY:]

# --- RENDER HEALTH CHECK SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Nico is active.")

    def do_HEAD(self):
        # Keeps Render & UptimeRobot pings quiet and healthy (fixes HTTP 501)
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

    def log_message(self, format, *args):
        # Keeps Render terminal logs clean
        return

def run_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# --- DISCORD BOT SETUP ---
class NicoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Nico's slash commands synced.")

bot = NicoBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening, 
            name="academic questions | /solve"
        )
    )

# --- DEDICATED CHANNEL & DIRECT CHAT LISTENER ---
@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    is_dedicated = DEDICATED_CHANNEL_ID != 0 and message.channel.id == DEDICATED_CHANNEL_ID
    is_mentioned = bot.user.mentioned_in(message)
    is_dm = isinstance(message.channel, discord.DMChannel)

    if is_dedicated or is_mentioned or is_dm:
        async with message.channel.typing():
            channel_id = message.channel.id

            clean_text = message.content.replace(f'<@{bot.user.id}>', '').strip()
            if not clean_text:
                clean_text = "Hello Nico."

            full_request = get_memory(channel_id) + [
                types.Content(role="user", parts=[types.Part.from_text(text=clean_text)])
            ]

            try:
                response = ai_client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=full_request,
                    config=types.GenerateContentConfig(
                        system_instruction=NICO_SYSTEM_INSTRUCTION,
                        temperature=0.3,
                    )
                )

                reply_text = response.text or "I was unable to analyze that query."

                add_text_memory(channel_id, role="user", text=clean_text)
                add_text_memory(channel_id, role="model", text=reply_text)

                if len(reply_text) > 1950:
                    reply_text = reply_text[:1950] + "\n\n*(Response truncated due to length limits.)*"

                await message.reply(reply_text)

            except Exception as e:
                print(f"[ERROR in on_message]: {e}")
                await message.reply("An anomaly occurred while processing your request.")

    await bot.process_commands(message)

# --- SLASH COMMAND: /solve ---
@bot.tree.command(name="solve", description="Ask Nico an academic question or problem")
@app_commands.describe(query="Your question or problem for Nico")
async def solve(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    channel_id = interaction.channel_id

    full_request = get_memory(channel_id) + [
        types.Content(role="user", parts=[types.Part.from_text(text=query)])
    ]

    try:
        response = ai_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=full_request,
            config=types.GenerateContentConfig(
                system_instruction=NICO_SYSTEM_INSTRUCTION,
                temperature=0.3,
            )
        )

        reply_text = response.text or "I was unable to analyze that query."

        add_text_memory(channel_id, role="user", text=query)
        add_text_memory(channel_id, role="model", text=reply_text)

        if len(reply_text) > 1950:
            reply_text = reply_text[:1950] + "\n\n*(Response truncated due to length limits.)*"

        await interaction.followup.send(reply_text)

    except Exception as e:
        print(f"[ERROR in /solve]: {e}")
        await interaction.followup.send("An anomaly occurred while analyzing your request.")

# --- SLASH COMMAND: /clear ---
@bot.tree.command(name="clear", description="Clear Nico's memory buffer for this channel")
async def clear(interaction: discord.Interaction):
    # Defer immediately to prevent 3-second timeouts
    await interaction.response.defer(ephemeral=False)
    
    channel_id = interaction.channel_id
    if channel_id in channel_memories and len(channel_memories[channel_id]) > 0:
        channel_memories[channel_id] = []
        await interaction.followup.send("The slate is clean once more. What shall we explore next?")
    else:
        # Note: If you want this fallback to be hidden from others, change ephemeral=True 
        # but keep in mind defer(ephemeral=False) forces the followup to match visibility.
        await interaction.followup.send("There are no recent records stored for this channel.")

if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    bot.run(DISCORD_TOKEN)