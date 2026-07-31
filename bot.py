import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Import Nico's persona system prompt
from nico_persona import NICO_SYSTEM_INSTRUCTION

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Initialize Google GenAI Client
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Memory storage per channel ( capped at 20 entries / 10 turns )
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

# --- RENDER DUMMY WEB SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Nico is running.")

def run_health_server():
    # Render assigns an explicit PORT environment variable
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Health server listening on port {port}")
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
            name="academic puzzles | /solve"
        )
    )

# --- SLASH COMMAND: /solve ---
@bot.tree.command(name="solve", description="Ask Nico to solve an equation, code bug, or analyze a diagram")
@app_commands.describe(
    query="Your question or instructions for Nico",
    image="Optional image attachment (diagram, math problem, code screenshot)"
)
async def solve(
    interaction: discord.Interaction, 
    query: str, 
    image: discord.Attachment = None
):
    await interaction.response.defer(thinking=True)
    channel_id = interaction.channel_id

    contents_payload = []

    # 1. Process image if attached
    if image:
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.followup.send("⚠️ Please attach a valid image file (PNG, JPEG, WEBP).")
            return

        image_bytes = await image.read()
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=image.content_type
        )
        contents_payload.append(image_part)

    # 2. Add text query
    contents_payload.append(types.Part.from_text(text=query))

    # 3. Combine with channel context
    full_request_contents = get_memory(channel_id) + [
        types.Content(role="user", parts=contents_payload)
    ]

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_request_contents,
            config=types.GenerateContentConfig(
                system_instruction=NICO_SYSTEM_INSTRUCTION,
                temperature=0.3,
            )
        )

        reply_text = response.text or "I was unable to discern the details of this request."

        # Save to memory buffer
        user_summary = f"[User attached an image: {image.filename}] {query}" if image else query
        add_text_memory(channel_id, role="user", text=user_summary)
        add_text_memory(channel_id, role="model", text=reply_text)

        if len(reply_text) > 1950:
            reply_text = reply_text[:1950] + "\n\n*(Nico's response continues, but reached Discord length limits.)*"

        await interaction.followup.send(reply_text)

    except Exception as e:
        print(f"Error handling query: {e}")
        await interaction.followup.send("An anomaly occurred while analyzing your request.")

# --- SLASH COMMAND: /clear ---
@bot.tree.command(name="clear", description="Clear Nico's memory buffer for this channel")
async def clear(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in channel_memories:
        channel_memories[channel_id] = []
        await interaction.response.send_message("The slate is clean once more. What shall we explore next?", ephemeral=False)
    else:
        await interaction.response.send_message("There are no recent records stored for this channel.", ephemeral=True)

# Main Execution Entry Point
if __name__ == "__main__":
    # Start web server in background thread for Render health checks
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Run Discord Bot
    bot.run(DISCORD_TOKEN)