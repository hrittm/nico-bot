import io
import json
import os
import time
import urllib.parse
import xml.etree.ElementTree as ET
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

class WolframView(discord.ui.View):
    def __init__(self, query: str):
        super().__init__(timeout=180)
        encoded_query = urllib.parse.quote(query)
        web_url = f"https://www.wolframalpha.com/input?i={encoded_query}"
        
        self.add_item(discord.ui.Button(
            label="🌐 Open Full Web View", 
            style=discord.ButtonStyle.link, 
            url=web_url
        ))

class LocalUtilities(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.periodic_data = self._load_periodic_table()
        self.pi_data = self._load_pi_digits()

    def _load_periodic_table(self):
        file_path = os.path.join(DATA_DIR, "periodic_table.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _load_pi_digits(self):
        file_path = os.path.join(DATA_DIR, "pi_digits.txt")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return "3.14159"

    @app_commands.command(name="ping", description="Check Nico's response latency.")
    async def ping(self, interaction: discord.Interaction):
        start_time = time.perf_counter()
        await interaction.response.send_message("🏓 Pinging...")
        end_time = time.perf_counter()

        api_latency = round(self.bot.latency * 1000)
        bot_latency = round((end_time - start_time) * 1000)

        embed = discord.Embed(
            title="🏓 Pong!",
            color=discord.Color.green()
        )
        embed.add_field(name="WebSocket Latency", value=f"`{api_latency} ms`", inline=True)
        embed.add_field(name="Response Latency", value=f"`{bot_latency} ms`", inline=True)

        await interaction.edit_original_response(content=None, embed=embed)

    @app_commands.command(name="atom", description="Look up atomic properties for an element.")
    @app_commands.describe(element="Name or symbol of the element (e.g., Oxygen, Au, Carbon)")
    async def atom(self, interaction: discord.Interaction, element: str):
        query = element.strip().lower()

        matched_data = None
        for key, info in self.periodic_data.items():
            if query in [key, info["name"].lower(), info["symbol"].lower()]:
                matched_data = info
                break

        if not matched_data:
            await interaction.response.send_message(
                f"❌ Element `{element}` not found in local database.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"⚛️ {matched_data['name']} ({matched_data['symbol']})",
            color=discord.Color.blue()
        )
        embed.add_field(name="Atomic Number", value=str(matched_data["atomic_number"]), inline=True)
        embed.add_field(name="Atomic Mass", value=matched_data["atomic_mass"], inline=True)
        embed.add_field(name="Category", value=matched_data["category"], inline=True)
        embed.add_field(name="Phase (STP)", value=matched_data["phase"], inline=True)
        embed.add_field(name="Electron Config", value=f"`{matched_data['electron_configuration']}`", inline=False)
        embed.set_footer(text="Nico Local Science Database")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pi", description="Print Pi to a specified number of decimal places.")
    @app_commands.describe(digits="Number of decimal places to view (1 to 1000).")
    async def pi(self, interaction: discord.Interaction, digits: int = 10):
        if digits < 1:
            await interaction.response.send_message("Please request at least 1 digit.", ephemeral=True)
            return
        if digits > 1000:
            await interaction.response.send_message("Maximum supported precision is 1000 digits.", ephemeral=True)
            return

        pi_str = self.pi_data[: 2 + digits]

        if len(pi_str) > 1900:
            await interaction.response.send_message(f"**π to {digits} decimal places:**\n```\n{pi_str[:1900]}...\n```")
        else:
            await interaction.response.send_message(f"**π to {digits} decimal places:**\n```{pi_str}```")

    @app_commands.command(name="wolf", description="Query Wolfram|Alpha with crisp, high-definition result pods.")
    @app_commands.describe(query="What would you like Wolfram|Alpha to compute?")
    async def wolf(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        app_id = os.getenv("WOLFRAM_APP_ID")
        if not app_id:
            await interaction.followup.send("⚠️ Wolfram App ID is not configured in `.env`.")
            return

        encoded_query = urllib.parse.quote(query)
        full_api_url = f"https://api.wolframalpha.com/v2/query?appid={app_id}&input={encoded_query}&mag=2.0&magstep=2"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(full_api_url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(f"⚠️ Wolfram API returned HTTP `{resp.status}`.")
                        return

                    xml_data = await resp.text()
                    root = ET.fromstring(xml_data)

                    if root.attrib.get("success") == "false":
                        await interaction.followup.send("🔴 Wolfram|Alpha could not compute a result for that query.")
                        return

                    pods = root.findall("pod")
                    main_pod = None
                    input_pod = None

                    for pod in pods:
                        pod_id = pod.attrib.get("id", "").lower()
                        if pod.attrib.get("primary") == "true" or "result" in pod_id or "solution" in pod_id or "plot" in pod_id:
                            main_pod = pod
                            break
                        if "input" in pod_id and not input_pod:
                            input_pod = pod

                    if not main_pod and len(pods) > 1:
                        main_pod = pods[1]
                    elif not main_pod and len(pods) > 0:
                        main_pod = pods[0]

                    img_element = main_pod.find(".//img") if main_pod is not None else None
                    plaintext_element = main_pod.find(".//plaintext") if main_pod is not None else None
                    
                    input_text = input_pod.find(".//plaintext").text if input_pod is not None and input_pod.find(".//plaintext") is not None else query

                    embed = discord.Embed(
                        title="🧮 Wolfram|Alpha Result",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Input", value=f"`{input_text}`", inline=False)

                    if plaintext_element is not None and plaintext_element.text:
                        embed.add_field(name="Result", value=f"```\n{plaintext_element.text}\n```", inline=False)

                    view = WolframView(query=query)

                    if img_element is not None and img_element.attrib.get("src"):
                        img_url = img_element.attrib.get("src")
                        async with session.get(img_url) as img_resp:
                            if img_resp.status == 200:
                                img_bytes = await img_resp.read()
                                file = discord.File(io.BytesIO(img_bytes), filename="result_pod.png")
                                embed.set_image(url="attachment://result_pod.png")
                                await interaction.followup.send(embed=embed, file=file, view=view)
                                return

                    await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            await interaction.followup.send(f"⚠️ Error querying Wolfram|Alpha: `{str(e)}`")

    @app_commands.command(name="req", description="Submit a feature request or bug report to the developers.")
    @app_commands.choices(req_type=[
        app_commands.Choice(name="🐛 Bug Report", value="Bug Report"),
        app_commands.Choice(name="💡 Feature Suggestion", value="Feature Suggestion")
    ])
    @app_commands.describe(
        req_type="Select whether this is a bug report or a feature idea.",
        details="Describe the bug or feature in detail."
    )
    async def req(self, interaction: discord.Interaction, req_type: app_commands.Choice[str], details: str):
        log_channel_id = os.getenv("LOG_CHANNEL_ID")

        if not log_channel_id:
            await interaction.response.send_message(
                "⚠️ Log channel is not configured on the bot server yet.", ephemeral=True
            )
            return

        channel = self.bot.get_channel(int(log_channel_id))
        if not channel:
            await interaction.response.send_message(
                "⚠️ Could not access the log channel. Please notify an admin.", ephemeral=True
            )
            return

        color = discord.Color.red() if req_type.value == "Bug Report" else discord.Color.green()
        log_embed = discord.Embed(
            title=f"New Submission: {req_type.value}",
            description=details,
            color=color,
            timestamp=interaction.created_at
        )
        log_embed.set_author(name=f"{interaction.user} (ID: {interaction.user.id})", icon_url=interaction.user.display_avatar.url)
        if interaction.guild:
            log_embed.add_field(name="Server", value=interaction.guild.name, inline=True)
            log_embed.add_field(name="Channel", value=interaction.channel.name, inline=True)

        await channel.send(embed=log_embed)

        await interaction.response.send_message(
            f"✅ Thank you! Your {req_type.value.lower()} has been delivered to the developers.",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(LocalUtilities(bot))