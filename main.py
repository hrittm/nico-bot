import asyncio
import os
from aiohttp import web
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"🔁 Synced {len(synced)} slash commands globally.")
    except Exception as e:
        print(f"⚠️ Failed to sync slash commands: {e}")

async def load_extensions():
    cogs = ["cogs.ai", "cogs.utility"]
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f"⚡ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog}: {e}")

# Simple HTTP health check handler for Render & UptimeRobot
async def handle_health_check(request):
    return web.Response(text="Nico Bot is online and running!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render automatically injects the PORT environment variable
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server listening on port {port} for health checks.")

async def main():
    # Start the dummy HTTP server alongside the Discord bot
    await start_dummy_server()
    
    async with bot:
        await load_extensions()
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            print("❌ DISCORD_TOKEN is missing in environment variables.")
            return
        await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Nico shut down cleanly.")