import asyncio
import os
from aiohttp import web
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

        # 2. Sync Slash Commands ONCE on startup
        try:
            synced = await self.tree.sync()
            print(f"🔁 Synced {len(synced)} slash commands globally.")
        except Exception as e:
            print(f"⚠️ Failed to sync slash commands: {e}")

    async def on_ready(self):
        # Only print connection message, DO NOT sync tree here!
        print(f"✅ Logged in as {self.user} (ID: {self.user.id})")


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
    await start_dummy_server()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN is missing in environment variables.")
        return

    # Retry loop with exponential backoff for Cloudflare / Discord 429 rate limits.
    #
    # IMPORTANT: A fresh NicoBot() must be created on every attempt.
    # When `async with bot:` exits (even due to an exception), discord.py closes
    # the underlying aiohttp ClientSession. Reusing the same bot object on the
    # next iteration means calling .start() on a closed session, which raises:
    #   RuntimeError: Session is closed
    # Creating a new instance gives a brand-new session for each attempt.
    max_retries = 5
    delay = 15  # start with 15 seconds

    for attempt in range(1, max_retries + 1):
        bot = NicoBot()  # ← fresh instance each time to avoid closed-session errors
        try:
            async with bot:
                await bot.start(token)
            break  # clean exit — no need to retry
        except discord.errors.HTTPException as e:
            if e.status == 429:
                print(f"⚠️ Discord/Cloudflare rate limit hit (429). Attempt {attempt}/{max_retries}.")
                if attempt < max_retries:
                    print(f"⏳ Waiting {delay} seconds before retrying...")
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff: 15s → 30s → 60s → 120s → 240s
                else:
                    print("❌ Max retries reached. Exiting.")
                    raise
            else:
                raise
        except Exception as e:
            print(f"❌ Unexpected connection error: {e}")
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Nico shut down cleanly.")