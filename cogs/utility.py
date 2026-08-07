import io
import json
import os
import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Optional
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

import numpy as np
import matplotlib
# Use non-interactive Agg backend suitable for server environments
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# ---------------------------------------------------------------------------
# Command metadata — used by the /help command
# ---------------------------------------------------------------------------
COMMAND_HELP: dict[str, dict] = {
    "ask": {
        "emoji": "💬",
        "short": "Ask Nico anything with live Google Search grounding.",
        "usage": "`/ask <prompt>`",
        "details": (
            "Sends your question to Nico's AI brain, powered by Google Gemini with **Search Grounding** enabled. "
            "This means Nico can pull in fresh, real-world information to answer your question accurately. "
            "If the search quota is exceeded, she gracefully falls back to her base knowledge.\n\n"
            "**Best for:** General knowledge, current events, concept explanations, recommendations."
        ),
        "example": "`/ask What is the Pauli Exclusion Principle?`",
    },
    "solve": {
        "emoji": "🧠",
        "short": "Deep-thinking academic solver for complex problems.",
        "usage": "`/solve <problem>`",
        "details": (
            "Activates extended thinking mode for rigorous, step-by-step problem solving. "
            "Unlike `/ask`, this mode uses a **neutral academic solver** — no personality, just structured logic. "
            "It restates the problem, walks through numbered steps with reasoning, applies relevant formulas or principles, "
            "and concludes with a clearly labelled final answer.\n\n"
            "**Best for:** Math (calculus, algebra, olympiad), physics, chemistry, formal logic, proofs."
        ),
        "example": "`/solve Prove that √2 is irrational.`",
    },
    "wolf": {
        "emoji": "🧮",
        "short": "Query Wolfram|Alpha for computational results.",
        "usage": "`/wolf <query>`",
        "details": (
            "Sends your query directly to the **Wolfram|Alpha API** and retrieves the primary result pod. "
            "The response is displayed as a high-definition image embed when available, along with a plaintext result. "
            "A button to open the full interactive Wolfram|Alpha page is also included.\n\n"
            "**Best for:** Symbolic math, unit conversions, equation solving, data lookups, function plots."
        ),
        "example": "`/wolf integrate x^2 sin(x) dx`",
    },
    "atom": {
        "emoji": "⚛️",
        "short": "Look up atomic data for any element.",
        "usage": "`/atom <element>`",
        "details": (
            "Queries Nico's **local periodic table database** (offline — no API needed). "
            "You can search by element **name** or **symbol**. "
            "Returns atomic number, atomic mass, category, phase at STP, and electron configuration.\n\n"
            "**Best for:** Quick chemistry reference, homework, lab work."
        ),
        "example": "`/atom Gold` or `/atom Au` or `/atom Oxygen`",
    },
    "pi": {
        "emoji": "π",
        "short": "Print π to up to 1000 decimal places.",
        "usage": "`/pi [digits]`",
        "details": (
            "Prints the value of **π (pi)** to the number of decimal places you specify. "
            "Defaults to 10 decimal places if no argument is provided. "
            "Maximum precision supported is **1000 digits**, stored locally for an instant response.\n\n"
            "**Best for:** Math reference, academic exercises, or just curiosity."
        ),
        "example": "`/pi 50`",
    },
    "graph": {
        "emoji": "📈",
        "short": "Plot a mathematical function y = f(x) as a graph image.",
        "usage": "`/graph <equation> [x_min] [x_max]`",
        "details": (
            "Parses and plots a mathematical function `y = f(x)` over a configurable x range. "
            "Powered by **SymPy** (for safe symbolic parsing) and **Matplotlib** (for rendering). "
            "The graph is rendered in a dark Discord-themed style and returned as an image.\n\n"
            "Supported syntax:\n"
            "- Use `^` or `**` for exponents: `x^2` or `x**2`\n"
            "- Implicit multiplication works: `2x` is treated as `2*x`\n"
            "- Standard math functions available: `sin`, `cos`, `tan`, `exp`, `log`, `sqrt`, `abs`\n\n"
            "**Best for:** Visualising functions, checking homework graphs, exploring curve behaviour."
        ),
        "example": "`/graph x^2 - 4` or `/graph sin(x) -6.28 6.28` or `/graph x/(x-2) -5 5`",
    },
    "ping": {
        "emoji": "🏓",
        "short": "Check Nico's connection latency.",
        "usage": "`/ping`",
        "details": (
            "Measures and displays two latency values:\n"
            "- **WebSocket Latency** — heartbeat latency between the bot and Discord's gateway.\n"
            "- **Response Latency** — time from command submission to first response.\n\n"
            "**Best for:** Diagnosing slowness or verifying the bot is healthy."
        ),
        "example": "`/ping`",
    },
    "req": {
        "emoji": "📬",
        "short": "Submit a bug report or feature suggestion to the developers.",
        "usage": "`/req <type> <details>`",
        "details": (
            "Lets you submit feedback directly to the development team. "
            "Choose between **🐛 Bug Report** (something is broken) or **💡 Feature Suggestion** (something you'd like added). "
            "Your submission is logged in a private developer channel with your username, server, and timestamp. "
            "The confirmation is sent as an ephemeral (private) reply visible only to you.\n\n"
            "**Best for:** Reporting issues, proposing new commands or improvements."
        ),
        "example": "`/req Bug Report` → *The /wolf command returns no image for integrals.*",
    },
    "help": {
        "emoji": "📖",
        "short": "View all commands or get a detailed breakdown of one.",
        "usage": "`/help [command]`",
        "details": (
            "Without any argument, `/help` displays a full overview of every available command with short descriptions. "
            "Pass an optional `command` argument to get a detailed breakdown of that specific command, including "
            "its usage syntax, what it's best suited for, and a concrete example.\n\n"
            "**Best for:** Getting started, understanding what Nico can do."
        ),
        "example": "`/help solve`",
    },
}

HELP_EMBED_COLOR = discord.Color.from_rgb(120, 80, 200)  # Deep violet — calm & scholarly


# ---------------------------------------------------------------------------
# Wolfram link button view
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # /ping
    # -----------------------------------------------------------------------
    @app_commands.command(name="ping", description="Check Nico's response latency.")
    async def ping(self, interaction: discord.Interaction):
        start_time = time.perf_counter()
        await interaction.response.send_message("🏓 Pinging...")
        end_time = time.perf_counter()

        api_latency = round(self.bot.latency * 1000)
        bot_latency = round((end_time - start_time) * 1000)

        embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
        embed.add_field(name="WebSocket Latency", value=f"`{api_latency} ms`", inline=True)
        embed.add_field(name="Response Latency", value=f"`{bot_latency} ms`", inline=True)

        await interaction.edit_original_response(content=None, embed=embed)

    # -----------------------------------------------------------------------
    # /atom
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # /pi
    # -----------------------------------------------------------------------
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
            await interaction.response.send_message(
                f"**π to {digits} decimal places:**\n```\n{pi_str[:1900]}...\n```"
            )
        else:
            await interaction.response.send_message(f"**π to {digits} decimal places:**\n```{pi_str}```")

    # -----------------------------------------------------------------------
    # /wolf
    # -----------------------------------------------------------------------
    @app_commands.command(name="wolf", description="Query Wolfram|Alpha with crisp, high-definition result pods.")
    @app_commands.describe(query="What would you like Wolfram|Alpha to compute?")
    async def wolf(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        app_id = os.getenv("WOLFRAM_APP_ID")
        if not app_id:
            await interaction.followup.send("⚠️ Wolfram App ID is not configured in `.env`.")
            return

        encoded_query = urllib.parse.quote(query)
        full_api_url = (
            f"https://api.wolframalpha.com/v2/query"
            f"?appid={app_id}&input={encoded_query}&mag=2.0&magstep=2"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(full_api_url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(f"⚠️ Wolfram API returned HTTP `{resp.status}`.")
                        return

                    xml_data = await resp.text()
                    root = ET.fromstring(xml_data)

                    if root.attrib.get("success") == "false":
                        await interaction.followup.send(
                            "🔴 Wolfram|Alpha could not compute a result for that query."
                        )
                        return

                    pods = root.findall("pod")
                    main_pod = None
                    input_pod = None

                    for pod in pods:
                        pod_id = pod.attrib.get("id", "").lower()
                        if (
                            pod.attrib.get("primary") == "true"
                            or "result" in pod_id
                            or "solution" in pod_id
                            or "plot" in pod_id
                        ):
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

                    input_text = (
                        input_pod.find(".//plaintext").text
                        if input_pod is not None and input_pod.find(".//plaintext") is not None
                        else query
                    )

                    embed = discord.Embed(title="🧮 Wolfram|Alpha Result", color=discord.Color.red())
                    embed.add_field(name="Input", value=f"`{input_text}`", inline=False)

                    if plaintext_element is not None and plaintext_element.text:
                        embed.add_field(
                            name="Result",
                            value=f"```\n{plaintext_element.text}\n```",
                            inline=False
                        )

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

    # -----------------------------------------------------------------------
    # /graph
    # -----------------------------------------------------------------------
    @app_commands.command(
        name="graph", 
        description="Plot a mathematical function y = f(x) and view the graph as an image."
    )
    @app_commands.describe(
        equation="The function to plot, e.g., '2x^2 - 4x + 1', 'sin(x)', or 'x/(x-2)'",
        x_min="Minimum x range (default: -10)",
        x_max="Maximum x range (default: 10)"
    )
    async def graph(
        self, 
        interaction: discord.Interaction, 
        equation: str, 
        x_min: float = -10.0, 
        x_max: float = 10.0
    ):
        await interaction.response.defer()

        if x_min >= x_max:
            await interaction.followup.send("⚠️ `x_min` must be strictly less than `x_max`.")
            return

        try:
            # 1. Safely parse the user equation string
            x = sp.Symbol('x')
            transformations = standard_transformations + (
                implicit_multiplication_application,
                convert_xor
            )
            
            # Restrict parsing symbols to x and common standard math functions
            parsed_expr = parse_expr(
                equation, 
                transformations=transformations, 
                local_dict={'x': x}
            )

            # Convert SymPy expression into a fast, vectorised NumPy function
            func = sp.lambdify(x, parsed_expr, modules=['numpy'])

            # 2. Generate x and y data points
            x_vals = np.linspace(x_min, x_max, 1000)

            # Suppress division-by-zero warnings from NumPy (e.g., asymptotes)
            with np.errstate(divide='ignore', invalid='ignore'):
                y_vals = func(x_vals)

            # Convert y_vals to float array if lambdify returned a single scalar/constant
            if not isinstance(y_vals, np.ndarray):
                y_vals = np.full_like(x_vals, float(y_vals))

            y_vals = y_vals.astype(float)

            # Mask infinities first (e.g., vertical asymptotes)
            y_vals[~np.isfinite(y_vals)] = np.nan

            # Dynamically clip extreme outliers using IQR to avoid distorting the plot.
            # This handles asymptotes that land just inside the finite range without
            # incorrectly clipping large-valued but legitimate functions.
            finite_vals = y_vals[np.isfinite(y_vals)]
            if len(finite_vals) > 0:
                q1, q3 = np.percentile(finite_vals, [5, 95])
                iqr = q3 - q1
                clip_margin = max(iqr * 5, 10)  # At least ±10 units of headroom
                y_vals[y_vals > q3 + clip_margin] = np.nan
                y_vals[y_vals < q1 - clip_margin] = np.nan

        except Exception as err:
            await interaction.followup.send(
                f"⚠️ Could not parse equation `{equation}`.\n"
                f"**Error:** `{str(err)}`\n"
                f"*Examples of valid expressions:* `x^2 - 4`, `2x + 3`, `sin(x)`, `x*exp(-x)`"
            )
            return

        # 3. Create dark-themed Matplotlib figure.
        # Use explicit rcParams instead of plt.style.use() to avoid touching
        # global matplotlib state, which is unsafe when multiple /graph calls
        # run concurrently on the same thread pool.
        fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
        fig.patch.set_facecolor("#36393F")
        ax.set_facecolor("#2F3136")
        for spine in ax.spines.values():
            spine.set_edgecolor("#72767D")
        ax.tick_params(colors="#DCDDDE")

        # Plot function curve
        ax.plot(x_vals, y_vals, label=f"y = {parsed_expr}", color="#5865F2", linewidth=2.5)

        # Axes and grid
        ax.axhline(0, color="#FFFFFF", linewidth=0.8, alpha=0.7)
        ax.axvline(0, color="#FFFFFF", linewidth=0.8, alpha=0.7)
        ax.grid(True, linestyle="--", alpha=0.25, color="#FFFFFF")

        # Labels and title
        ax.set_title(
            f"Graph of $y = {sp.latex(parsed_expr)}$",
            fontsize=14, color="#FFFFFF", pad=12
        )
        ax.set_xlabel("x", fontsize=11, color="#DCDDDE")
        ax.set_ylabel("y", fontsize=11, color="#DCDDDE")
        ax.set_xlim(x_min, x_max)
        ax.legend(
            loc="upper right",
            facecolor="#2F3136",
            edgecolor="none",
            labelcolor="#DCDDDE"
        )

        fig.tight_layout()

        # 4. Save plot to in-memory buffer and send as Discord file attachment
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        buffer.seek(0)
        plt.close(fig)  # Always close to free memory

        embed = discord.Embed(
            title=f"📈 Graph of y = {parsed_expr}",
            description=f"Plotted over x ∈ [{x_min}, {x_max}]",
            color=discord.Color.from_rgb(88, 101, 242)  # Discord blurple
        )
        embed.set_image(url="attachment://graph.png")
        embed.set_footer(text="Nico Graph Engine  •  Powered by SymPy & Matplotlib")

        file = discord.File(buffer, filename="graph.png")
        await interaction.followup.send(embed=embed, file=file)

    # -----------------------------------------------------------------------
    # /req
    # -----------------------------------------------------------------------
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

        # Defer the interaction FIRST to prevent a "did not respond" error if
        # channel.send is slow or raises an exception before we can reply.
        await interaction.response.defer(ephemeral=True)

        color = discord.Color.red() if req_type.value == "Bug Report" else discord.Color.green()
        log_embed = discord.Embed(
            title=f"New Submission: {req_type.value}",
            description=details,
            color=color,
            timestamp=interaction.created_at
        )
        log_embed.set_author(
            name=f"{interaction.user} (ID: {interaction.user.id})",
            icon_url=interaction.user.display_avatar.url
        )
        if interaction.guild:
            log_embed.add_field(name="Server", value=interaction.guild.name, inline=True)
            log_embed.add_field(name="Channel", value=interaction.channel.name, inline=True)

        await channel.send(embed=log_embed)

        await interaction.followup.send(
            f"✅ Thank you! Your {req_type.value.lower()} has been delivered to the developers.",
            ephemeral=True
        )

    # -----------------------------------------------------------------------
    # /help
    # -----------------------------------------------------------------------
    @app_commands.command(name="help", description="View all of Nico's commands, or get a deep dive on a specific one.")
    @app_commands.describe(command="The command you'd like to learn more about.")
    @app_commands.choices(command=[
        app_commands.Choice(name="💬 ask", value="ask"),
        app_commands.Choice(name="🧠 solve", value="solve"),
        app_commands.Choice(name="🧮 wolf", value="wolf"),
        app_commands.Choice(name="📈 graph", value="graph"),
        app_commands.Choice(name="⚛️ atom", value="atom"),
        app_commands.Choice(name="π  pi", value="pi"),
        app_commands.Choice(name="🏓 ping", value="ping"),
        app_commands.Choice(name="📬 req", value="req"),
        app_commands.Choice(name="📖 help", value="help"),
    ])
    async def help(
        self,
        interaction: discord.Interaction,
        command: Optional[app_commands.Choice[str]] = None
    ):
        if command is None:
            # --- Full overview embed ---
            embed = discord.Embed(
                title="📖 Nico — Command Reference",
                description=(
                    "Hello! I'm Nico — your calm, scholarly academic assistant. "
                    "Here's a full overview of what I can do.\n"
                    "Use `/help <command>` to get a detailed breakdown of any specific command."
                ),
                color=HELP_EMBED_COLOR
            )

            for cmd_name, info in COMMAND_HELP.items():
                embed.add_field(
                    name=f"{info['emoji']}  `/{cmd_name}` — {info['short']}",
                    value=f"Usage: {info['usage']}",
                    inline=False
                )

            embed.add_field(
                name="\u200b",
                value="💡 You can also **@mention me** in any channel to start a conversation directly.",
                inline=False
            )
            embed.set_footer(text="Nico Bot  •  /help <command> for detailed info")

            await interaction.response.send_message(embed=embed)

        else:
            # --- Detailed view for a specific command ---
            info = COMMAND_HELP.get(command.value)
            if not info:
                await interaction.response.send_message("❌ Command not found.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"{info['emoji']}  `/{command.value}`",
                description=info["details"],
                color=HELP_EMBED_COLOR
            )
            embed.add_field(name="Usage", value=info["usage"], inline=False)
            embed.add_field(name="Example", value=info["example"], inline=False)
            embed.set_footer(text="Nico Bot  •  /help to see all commands")

            await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LocalUtilities(bot))