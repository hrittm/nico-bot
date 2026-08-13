import asyncio
import os
from aiohttp import web
import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class NicoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        # 1. Load Cogs
        cogs = ["cogs.ai", "cogs.utility"]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"⚡ Loaded cog: {cog}")
            except Exception as e:
                print(f"❌ Failed to load cog {cog}: {e}")

        # 2. Sync Slash Commands
        # To avoid hitting Discord's strict global sync rate limits during restarts,
        # you can set SYNC_COMMANDS=false in your environment once commands are registered.
        should_sync = os.getenv("SYNC_COMMANDS", "true").lower() in ("true", "1", "yes")
        if should_sync:
            try:
                synced = await self.tree.sync()
                print(f"🔁 Synced {len(synced)} slash commands globally.")
            except Exception as e:
                print(f"⚠️ Failed to sync slash commands: {e}")

    async def on_ready(self):
        print(f"✅ Logged in as {self.user} (ID: {self.user.id})")
        print("🤖 Nico is online and listening for interactions.")


async def handle_health_check(request):
    return web.Response(text="Nico Bot is online and running!")


async def start_dummy_server():
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server listening on port {port} for health checks.")


async def main():
    # Start web server immediately so Render/UptimeRobot health checks pass
    await start_dummy_server()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN is missing in environment variables.")
        return

    delay = 15       # Starting backoff delay in seconds
    max_delay = 120   # Maximum backoff cap (2 minutes)

    while True:
        # A fresh NicoBot instance must be created on every attempt to provide
        # a new aiohttp ClientSession and avoid "RuntimeError: Session is closed"
        bot = NicoBot()
        try:
            async with bot:
                await bot.start(token)
            # If start() exits cleanly without exceptions, break out of loop
            break

        except (discord.errors.HTTPException,
                discord.errors.GatewayNotFound,
                discord.errors.ConnectionClosed,
                aiohttp.ClientError,
                OSError) as e:
            status = getattr(e, "status", None)
            if status == 429:
                print(f"⚠️ Discord/Cloudflare 429 Rate Limit. Backing off for {delay}s...")
            elif status and 500 <= status < 600:
                print(f"⚠️ Cloudflare/Discord Server Error ({status}) - Render IP may be temporarily blocked. Waiting {delay}s...")
            else:
                first_line = str(e).split("\n")[0][:120]
                print(f"⚠️ Discord connection error ({status or type(e).__name__}): {first_line}. Waiting {delay}s...")

            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)

        except Exception as e:
            first_line = str(e).split("\n")[0][:120]
            print(f"❌ Unexpected error ({type(e).__name__}): {first_line}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Nico shut down cleanly.")