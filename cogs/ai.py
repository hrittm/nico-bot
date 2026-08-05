import os
import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types
from google.genai.errors import APIError

SYSTEM_PROMPT = """
You are Nico, a friendly, witty, smart, and approachable AI assistant for our Discord community.
- Your tone should feel natural, enthusiastic, and relatable to teenagers and young adults.
- Keep responses engaging, well-formatted, and concise unless deep detail is requested.
- If live search results are available, use them to provide up-to-date information seamlessly.
"""

class AICommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        api_key = os.getenv("GEMINI_API_KEY")
        self.ai_client = genai.Client(api_key=api_key)

    @app_commands.command(name="ask", description="Ask Nico anything! With live search and automatic fallback.")
    @app_commands.describe(prompt="What would you like to ask Nico?")
    async def ask(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()

        # Attempt 1: Try generating content with Google Search Grounding enabled
        try:
            response = self.ai_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.7,
                    tools=[{"google_search": {}}]
                )
            )
            text_output = response.text if response.text else "Hmm, I couldn't get an answer for that."

        except APIError as api_err:
            # Handle rate limits or quota exceeded errors gracefully
            err_msg = str(api_err).lower()
            if "quota" in err_msg or "rate limit" in err_msg or "429" in err_msg:
                try:
                    # Fallback Attempt: Generate response WITHOUT Search Grounding
                    response = self.ai_client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT + "\nNote: Live web search is currently throttled, answer using internal knowledge.",
                            temperature=0.7
                        )
                    )
                    text_output = f"{response.text}\n\n*(⚡ Note: Live search quota reached; responded using internal AI knowledge)*"
                except Exception as fallback_err:
                    text_output = f"⚠️ Quota exceeded and fallback failed: `{str(fallback_err)}`"
            else:
                text_output = f"⚠️ API Error: `{str(api_err)}`"
        except Exception as e:
            text_output = f"⚠️ Unexpected error: `{str(e)}`"

        # Enforce Discord 2000 character limit
        if len(text_output) > 2000:
            await interaction.followup.send(f"{text_output[:1990]}\n\n*(Truncated due to length)*")
        else:
            await interaction.followup.send(text_output)

    @app_commands.command(name="solve", description="Deep-thinking mode for complex math, science, or logic problems.")
    @app_commands.describe(problem="The problem or question you need solved step-by-step.")
    async def solve(self, interaction: discord.Interaction, problem: str):
        await interaction.response.defer()

        try:
            response = self.ai_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=f"Please solve this step-by-step with clear reasoning:\n\n{problem}",
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=1024),
                    temperature=0.2,
                )
            )

            text_output = response.text if response.text else "I couldn't produce a solution for this problem."

            if len(text_output) > 2000:
                await interaction.followup.send(f"**🧠 Solution:**\n\n{text_output[:1950]}\n\n*(Truncated due to length limit)*")
            else:
                await interaction.followup.send(f"**🧠 Solution:**\n\n{text_output}")

        except Exception as e:
            await interaction.followup.send(f"⚠️ An error occurred while solving: `{str(e)}`")

async def setup(bot: commands.Bot):
    await bot.add_cog(AICommands(bot))