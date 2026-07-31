import os
import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load personality prompt
from nico_persona import NICO_SYSTEM_INSTRUCTION

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Initialize Google GenAI Client
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Per-channel context memory (limit to 20 messages / 10 turns for optimal token balance)
MAX_HISTORY = 20
channel_memories = {}

def get_memory(channel_id: int):
    if channel_id not in channel_memories:
        channel_memories[channel_id] = []
    return channel_memories[channel_id]

def add_memory(channel_id: int, role: str, text: str):
    history = get_memory(channel_id)
    history.append(
        types.Content(
            role=role,
            parts=[types.Part.from_text(text=text)]
        )
    )
    if len(history) > MAX_HISTORY:
        channel_memories[channel_id] = history[-MAX_HISTORY:]

class NicoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Nico's slash commands synced successfully.")

bot = NicoBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    # Setting Nico's status in Discord
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening, 
            name="academic puzzles | /solve"
        )
    )

# --- SLASH COMMAND 1: /solve ---
@bot.tree.command(name="solve", description="Ask Nico to explain or solve a math, science, or programming problem")
@app_commands.describe(query="The problem, equation, or topic you'd like to explore")
async def solve(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    channel_id = interaction.channel_id

    add_memory(channel_id, role="user", text=query)

    try:
        # Request generation with Nico's persona system instruction
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=get_memory(channel_id),
            config=types.GenerateContentConfig(
                system_instruction=NICO_SYSTEM_INSTRUCTION,
                temperature=0.4,  # Lower temperature for precise mathematical/logic reasoning
            )
        )

        reply_text = response.text or "I was unable to formulate an answer to that mystery."
        add_memory(channel_id, role="model", text=reply_text)

        # Truncate if reply exceeds Discord message limits
        if len(reply_text) > 1950:
            reply_text = reply_text[:1950] + "\n\n*(The insight continues, but reaches Discord's character limit.)*"

        await interaction.followup.send(reply_text)

    except Exception as e:
        print(f"Error handling query: {e}")
        await interaction.followup.send("An unexpected anomaly occurred while analyzing your request.")

# --- SLASH COMMAND 2: /clear ---
@bot.tree.command(name="clear", description="Clear Nico's memory buffer for this channel")
async def clear(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    if channel_id in channel_memories:
        channel_memories[channel_id] = []
        await interaction.response.send_message("The slate is clean once more. What shall we explore next?", ephemeral=False)
    else:
        await interaction.response.send_message("There are no recent records stored for this channel.", ephemeral=True)

bot.run(DISCORD_TOKEN)