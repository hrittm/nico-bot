# Nico — Academic Discord Bot

> *"To exist is to have knowledge. Why fear the unknown when curiosity is so much more rewarding?"*

**Nico** is a Discord bot built for academic and education-focused servers. Inspired by the calm brilliance of **Nico Robin** from *One Piece*, she acts as an intelligent assistant for students — helping with problem solving, research, science lookups, and computational queries, all with a composed and scholarly touch.

---

## Character

| Attribute | Detail |
|---|---|
| **Inspiration** | [Nico Robin](https://onepiece.fandom.com/wiki/Nico_Robin) — *One Piece* |
| **Nickname** | Light of the Revolution / Demon Child |
| **Bounty** | ฿930,000,000 |
| **Devil Fruit** | [Hana Hana no Mi](https://onepiece.fandom.com/wiki/Hana_Hana_no_Mi) (Flower-Flower Fruit) |
| **Role** | Archaeologist, Scholar, Straw Hat Pirates |

Nico Robin is one of the most intelligent characters in *One Piece* — calm, articulate, and deeply knowledgeable. Having become a scholar at a very young age, surviving alone after the destruction of her home island Ohara, and later finding her place among the Straw Hats, Robin embodies resilience through intellect.

These traits make her persona a natural fit for an academic bot: warm without being loud, precise without being robotic, and always a little interestingly dark.

[Learn more about Nico Robin →](https://onepiece.fandom.com/wiki/Nico_Robin)

---

## Features

| Feature | Description |
|---|---|
| 🤖 **AI Chat (mention)** | @mention Nico in any channel to start a conversation powered by Gemini with live Search Grounding |
| 💬 **`/ask`** | Ask Nico anything — Search Grounding enabled with automatic fallback |
| 🧠 **`/solve`** | Extended thinking mode for rigorous, step-by-step academic problem solving |
| 🧮 **`/wolf`** | Query Wolfram\|Alpha and receive high-definition image result pods |
| 📈 **`/graph`** | Plot any `y = f(x)` function as a dark-themed graph image, powered by SymPy + Matplotlib |
| ⚛️ **`/atom`** | Offline periodic table lookup by element name or symbol |
| π **`/pi`** | Print π to up to 1000 decimal places, instantly |
| 📬 **`/req`** | Submit bug reports or feature suggestions directly to a developer log channel |
| 📖 **`/help`** | Full command overview, or a detailed breakdown of any specific command |
| 🌐 **Health Check Server** | Lightweight HTTP server for uptime monitoring via UptimeRobot / Render |

---

## Commands

| Command | Description |
|---------|-------------|
| `/ask <prompt>` | Ask Nico anything — she uses live Google Search grounding for accurate answers |
| `/solve <problem>` | Deep-thinking academic solver for math, science, and logic (step-by-step, no persona) |
| `/wolf <query>` | Query Wolfram\|Alpha and get the result as an image pod + text |
| `/graph <equation> [x_min] [x_max]` | Plot a `y = f(x)` function as a dark-themed graph image |
| `/atom <element>` | Look up element info by name or symbol |
| `/pi [digits]` | Print π to a specified number of decimal places (max 1000) |
| `/ping` | Check Nico's WebSocket and response latency |
| `/req <type> <details>` | Submit a bug report or feature suggestion to the developers |
| `/help [command]` | View all commands, or get a deep dive on a specific one |
| `@Nico <message>` | Mention Nico in any channel to chat with her directly |

### 💬 `/ask <prompt>`
Ask Nico anything. Uses Google Gemini with **live Search Grounding** enabled for up-to-date, accurate answers. If search quota is exceeded, she automatically falls back to her base knowledge — no interruption.

**Best for:** General knowledge, current events, concept explanations, recommendations.

```
/ask What is the Pauli Exclusion Principle?
/ask Explain the difference between a virus and a bacterium.
```

---

### 🧠 `/solve <problem>`
Activates **extended thinking mode** for structured, step-by-step academic problem solving. This command uses a dedicated neutral solver prompt — no Nico Robin persona, just rigorous logic. Nico will restate the problem, walk through numbered steps with clear reasoning, apply relevant formulas, and conclude with a labelled final answer.

**Best for:** Math (calculus, algebra, olympiad problems), physics, chemistry, formal logic, proofs.

```
/solve Prove that √2 is irrational.
/solve Find all real solutions to x^4 - 5x^2 + 6 = 0.
/solve A 2 kg block slides down a frictionless ramp of height 3 m. Find its speed at the bottom.
```

---

### 🧮 `/wolf <query>`
Sends your query to the **Wolfram|Alpha API** and returns the primary result pod as a high-definition image embed, plus plaintext results where available. A button to open the full interactive Wolfram|Alpha page is included.

**Best for:** Symbolic math, equation solving, unit conversions, data lookups, function plots.

```
/wolf integrate x^2 sin(x) dx
/wolf population of Japan in 2024
/wolf boiling point of ethanol in fahrenheit
```

---

### 📈 `/graph <equation> [x_min] [x_max]`
Parses and plots a mathematical function `y = f(x)` over a configurable x range. Powered by **SymPy** for safe symbolic parsing and **Matplotlib** for rendering. The output is a dark Discord-themed image embed.

**Supported syntax:**
- Use `^` or `**` for exponents: `x^2` or `x**2`
- Implicit multiplication is supported: `2x` → `2*x`
- Standard math functions: `sin`, `cos`, `tan`, `exp`, `log`, `sqrt`, `abs`
- `x_min` and `x_max` default to `-10` and `10` respectively

**Best for:** Visualising functions, checking homework graphs, exploring curve behaviour.

```
/graph x^2 - 4
/graph sin(x) -6.28 6.28
/graph x/(x-2) -5 5
/graph 2x^3 - 3x^2 - 11x + 6
```

---

### ⚛️ `/atom <element>`
Looks up element data from Nico's **local offline periodic table database** — no API required. Accepts element name or symbol.

Returns: Atomic number, atomic mass, category, phase at STP, electron configuration.

```
/atom Gold
/atom Au
/atom Oxygen
```

---

### π `/pi [digits]`
Prints **π (pi)** to the number of decimal places you specify. Defaults to 10. Maximum is 1000 digits, stored locally for an instant response.

```
/pi          → 3.1415926535 (default 10 digits)
/pi 50       → π to 50 decimal places
/pi 1000     → π to 1000 decimal places
```

---

### 🏓 `/ping`
Displays **WebSocket latency** (Discord gateway heartbeat) and **Response latency** (command round-trip time). Useful for diagnosing slowness.

```
/ping
```

---

### 📬 `/req <type> <details>`
Submit feedback directly to the development team. Choose between:
- **🐛 Bug Report** — Something is broken or behaving unexpectedly.
- **💡 Feature Suggestion** — An idea for a new command or improvement.

Submissions are logged in a private developer channel with your username, server name, channel name, and timestamp. Your confirmation is ephemeral (only visible to you).

```
/req Bug Report   → The /wolf command returns no image for integral queries.
/req Feature Suggestion → Add a /define command for dictionary lookups.
```

---

### 📖 `/help [command]`
Without an argument, shows a full overview of all commands. Pass a command name to get a detailed breakdown including usage syntax, what it's best for, and a concrete example.

```
/help              → Full command list
/help solve        → Detailed info on /solve
/help wolf         → Detailed info on /wolf
```

---

### 💬 `@Nico <message>`
Mention Nico directly in any channel to chat with her. She'll respond in character as Nico Robin — calm, scholarly, with the occasional darkly amusing observation. No slash command needed.

```
@Nico what's the difference between nuclear fission and fusion?
@Nico can you explain recursion like I'm 10?
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Discord Library | [discord.py](https://discordpy.readthedocs.io/) v2.3+ |
| AI Model | Google Gemini (`gemini-3.6-flash`) via [`google-genai`](https://pypi.org/project/google-genai/) |
| Compute Engine | [Wolfram\|Alpha API](https://products.wolframalpha.com/api/) v2 |
| Graphing | [Matplotlib](https://matplotlib.org/) + [NumPy](https://numpy.org/) + [SymPy](https://www.sympy.org/) |
| Web Server | [aiohttp](https://docs.aiohttp.org/) |
| Config | [`python-dotenv`](https://pypi.org/project/python-dotenv/) |

---

## Setup & Installation

### Prerequisites
- Python **3.11** or higher
- A Discord Bot Token → [Discord Developer Portal](https://discord.com/developers/applications)
- A Google Gemini API Key → [Google AI Studio](https://aistudio.google.com/)
- A Wolfram|Alpha App ID → [Wolfram Developer Portal](https://developer.wolframalpha.com/)
- A private Discord channel ID for logging `/req` submissions

### 1. Clone the repository
```bash
git clone https://github.com/your-username/nico-bot.git
cd nico-bot
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the root directory with the following keys:

```env
DISCORD_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_google_gemini_api_key
WOLFRAM_APP_ID=your_wolfram_app_id
LOG_CHANNEL_ID=your_log_channel_id
```

> **`LOG_CHANNEL_ID`** — The numeric ID of a private Discord channel where `/req` submissions will be posted. The bot must have **Send Messages** permission in that channel.
>
> To get a channel ID: Enable Developer Mode in Discord settings → right-click the channel → **Copy Channel ID**.

### 5. Run the bot
```bash
python main.py
```

You should see output like:
```
⚡ Loaded cog: cogs.ai
⚡ Loaded cog: cogs.utility
🔁 Synced 8 slash commands globally.
🌐 Web server listening on port 8080 for health checks.
✅ Logged in as Nico#XXXX (ID: ...)
```

> **Note on slash command sync:** Commands are synced globally on every startup. It may take up to **1 hour** for new commands to appear for all users on Discord after first deployment.

---

## Project Structure

```
nico-bot/
├── main.py                   # Bot entry point, cog loader, health check server
├── cogs/
│   ├── ai.py                 # /ask, /solve, @mention handler (Gemini AI)
│   └── utility.py            # /ping, /atom, /pi, /wolf, /req, /help
├── config/
│   ├── __init__.py
│   └── persona.py            # SYSTEM_PROMPT (Nico Robin persona)
│                             # SOLVE_SYSTEM_PROMPT (neutral academic solver)
├── data/
│   ├── periodic_table.json   # Offline element database (118 elements)
│   └── pi_digits.txt         # Pre-computed Pi to 1000 decimal places
├── requirements.txt
├── Procfile                  # Deployment config for Render / Railway
└── .env                      # Environment variables (never committed)
```

---

## Deployment

The bot includes a built-in HTTP health check server that listens on the `PORT` environment variable (default: `8080`). This is required for hosting platforms like **Render** or **Railway** that need an active HTTP endpoint to keep the process alive.

The included `Procfile` configures this automatically:
```
web: python main.py
```

### Keeping the bot alive 24/7
Point an uptime monitoring service to your deployment URL to prevent it from sleeping:
- [UptimeRobot](https://uptimerobot.com) — Free HTTP monitor, pings every 5 minutes
- [Better Stack](https://betterstack.com) — Free tier available

The health check endpoint responds to `GET /` with:
```
Nico Bot is online and running!
```

---

## Contributing

Found a bug or have a feature idea? Use `/req` directly in Discord and Nico will forward it to the development log. Alternatively, open an issue or pull request on GitHub.

---

*Inspired by the resilient scholar who read the Poneglyphs — and lived to tell the tale.*