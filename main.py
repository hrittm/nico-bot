import asyncio
import os
from aiohttp import web
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


class NicoBot(commands.Bot):
    def __init__(self, state: dict[str, bool]):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.state = state

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
        # Default is disabled to avoid repeated global sync calls during container restarts.
        should_sync = os.getenv("SYNC_COMMANDS", "false").lower() in ("true", "1", "yes")
        if should_sync:
            try:
                sync_guild_id = os.getenv("SYNC_GUILD_ID")
                if sync_guild_id:
                    guild = discord.Object(id=int(sync_guild_id))
                    synced = await self.tree.sync(guild=guild)
                    print(f"🔁 Synced {len(synced)} slash commands to guild {sync_guild_id}.")
                else:
                    synced = await self.tree.sync()
                    print(f"🔁 Synced {len(synced)} slash commands globally.")
            except Exception as e:
                print(f"⚠️ Failed to sync slash commands: {e}")
        else:
            print("ℹ️ Slash command sync skipped (SYNC_COMMANDS is false).")

    async def on_ready(self):
        self.state["is_discord_ready"] = True
        print(f"✅ Logged in as {self.user} (ID: {self.user.id})")
        print("🤖 Nico is online and listening for interactions.")

    async def on_disconnect(self):
        self.state["is_discord_ready"] = False
        print("⚠️ Disconnected from Discord gateway. Reconnecting...")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        print(f"⚠️ App command error: {type(error).__name__}: {error}")

        if interaction.response.is_done():
            await interaction.followup.send(
                "⚠️ Something went wrong while running that command. Please try again in a moment.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "⚠️ Something went wrong while running that command. Please try again in a moment.",
                ephemeral=True
            )


async def handle_health_check(request):
    state: dict[str, bool] = request.app["state"]
    is_discord_ready = state.get("is_discord_ready", False)
    message = (
        "Nico Bot is online and connected to Discord."
        if is_discord_ready
        else "Nico Bot process is running, but Discord is not connected yet."
    )
    return web.Response(text=message, status=200)


async def start_dummy_server(state: dict[str, bool]):
    app = web.Application()
    app["state"] = state
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server listening on port {port} for health checks.")


async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ DISCORD_TOKEN is missing in environment variables.")
        return

    state = {"is_discord_ready": False}

    # Start health server after state exists so health reflects Discord readiness.
    await start_dummy_server(state)

    delay = 15       # Starting backoff delay in seconds
    max_delay = 120   # Maximum backoff cap (2 minutes)

    while True:
        # A fresh NicoBot instance is required on each attempt to avoid using a closed aiohttp session.
        bot = NicoBot(state=state)
        try:
            async with bot:
                await bot.start(token)
            # If start() exits cleanly without exceptions, break out of loop.
            break

        except (discord.errors.HTTPException,
                discord.errors.GatewayNotFound,
                discord.errors.ConnectionClosed,
                aiohttp.ClientError,
                OSError) as e:
            state["is_discord_ready"] = False
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
            state["is_discord_ready"] = False
            first_line = str(e).split("\n")[0][:120]
            print(f"❌ Unexpected error ({type(e).__name__}): {first_line}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Nico shut down cleanly.")