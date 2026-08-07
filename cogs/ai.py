import asyncio
import os
import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Import from config/persona.py
from config.persona import SYSTEM_PROMPT, SOLVE_SYSTEM_PROMPT


class AICommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        api_key = os.getenv("GEMINI_API_KEY")
        self.ai_client = genai.Client(api_key=api_key)

    async def _generate_response(self, prompt: str) -> str:
        """Helper method to handle Gemini API generation with search grounding and fallback.

        Uses asyncio.to_thread to run the blocking SDK call off the event loop,
        preventing the bot from freezing for all users during generation.
        """
        try:
            # Attempt 1: Try generating content with Google Search Grounding enabled.
            # Wrapped in asyncio.to_thread because generate_content is a blocking call.
            response = await asyncio.to_thread(
                lambda: self.ai_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.7,
                        tools=[{"google_search": {}}]
                    )
                )
            )
            return response.text if response.text else "Hmm, I couldn't get an answer for that."

        except APIError as api_err:
            err_msg = str(api_err).lower()
            if "quota" in err_msg or "rate limit" in err_msg or "429" in err_msg:
                try:
                    # Fallback Attempt: Generate response WITHOUT Search Grounding.
                    response = await asyncio.to_thread(
                        lambda: self.ai_client.models.generate_content(
                            model="gemini-3.6-flash",
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                temperature=0.7
                            )
                        )
                    )
                    return response.text if response.text else "Hmm, I couldn't get an answer for that."
                except Exception as fallback_err:
                    return f"⚠️ Quota exceeded and fallback failed: `{str(fallback_err)}`"
            else:
                return f"⚠️ API Error: `{str(api_err)}`"
        except Exception as e:
            return f"⚠️ Unexpected error: `{str(e)}`"

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages sent by any bot (including Nico itself)
        if message.author.bot:
            return

        # Trigger if Nico is mentioned in the message
        if self.bot.user in message.mentions:
            # Strip both standard user mentions (<@id>) and nickname mentions (<@!id>)
            clean_prompt = (
                message.content
                .replace(f"<@{self.bot.user.id}>", "")
                .replace(f"<@!{self.bot.user.id}>", "")
                .strip()
            )

            if not clean_prompt:
                await message.reply("Hey there! How can I help you today?")
                return

            async with message.channel.typing():
                text_output = await self._generate_response(clean_prompt)

            if len(text_output) > 2000:
                await message.reply(f"{text_output[:1990]}\n\n*(Truncated due to length)*")
            else:
                await message.reply(text_output)

    @app_commands.command(name="ask", description="Ask Nico anything! With live search and automatic fallback.")
    @app_commands.describe(prompt="What would you like to ask Nico?")
    async def ask(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()

        text_output = await self._generate_response(prompt)

        if len(text_output) > 2000:
            await interaction.followup.send(f"{text_output[:1990]}\n\n*(Truncated due to length)*")
        else:
            await interaction.followup.send(text_output)

    @app_commands.command(name="solve", description="Deep-thinking mode for complex math, science, or logic problems.")
    @app_commands.describe(problem="The problem or question you need solved step-by-step.")
    async def solve(self, interaction: discord.Interaction, problem: str):
        await interaction.response.defer()

        try:
            # Uses SOLVE_SYSTEM_PROMPT: a neutral, rigorous academic solver — no Nico Robin persona.
            # Wrapped in asyncio.to_thread to avoid blocking the event loop.
            response = await asyncio.to_thread(
                lambda: self.ai_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=f"Solve the following problem:\n\n{problem}",
                    config=types.GenerateContentConfig(
                        system_instruction=SOLVE_SYSTEM_PROMPT,
                        thinking_config=types.ThinkingConfig(thinking_budget=1024),
                        temperature=0.2,
                    )
                )
            )

            text_output = response.text if response.text else "I couldn't produce a solution for this problem."

            if len(text_output) > 2000:
                await interaction.followup.send(
                    f"**🧠 Solution:**\n\n{text_output[:1950]}\n\n*(Truncated due to length limit)*"
                )
            else:
                await interaction.followup.send(f"**🧠 Solution:**\n\n{text_output}")

        except Exception as e:
            await interaction.followup.send(f"⚠️ An error occurred while solving: `{str(e)}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(AICommands(bot))