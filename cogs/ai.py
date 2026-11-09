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

    async def _resolve_message(self, channel: discord.abc.Messageable, message_id: int) -> discord.Message | None:
        """Safely fetch a message by ID without raising errors on missing/deleted messages."""
        try:
            return await channel.fetch_message(message_id)
        except (discord.NotFound, discord.HTTPException, discord.Forbidden):
            return None

    async def _build_conversation_history(self, message: discord.Message) -> list[types.Content]:
        """Reconstruct the conversation history leading up to the given message.

        Traverses the `message.reference` reply chain backwards up to 10 turns.
        If in a DM and not a reply, gathers recent direct messages.
        Formats the conversation turns into `types.Content` for Gemini multi-turn generation.
        """
        chain: list[discord.Message] = [message]
        curr = message
        max_depth = 10

        # 1. Follow reply chain backwards
        while curr.reference and curr.reference.message_id and len(chain) < max_depth:
            parent = None
            if isinstance(curr.reference.resolved, discord.Message):
                parent = curr.reference.resolved
            else:
                parent = await self._resolve_message(curr.channel, curr.reference.message_id)

            if parent:
                chain.append(parent)
                curr = parent
            else:
                break

        # 2. If in a DM and not a reply chain, pull recent DM history
        if len(chain) == 1 and isinstance(message.channel, discord.DMChannel):
            try:
                recent = [m async for m in message.channel.history(limit=8, before=message)]
                for m in recent:
                    if not m.author.bot or m.author == self.bot.user:
                        chain.append(m)
            except Exception:
                pass

        # Chronological order: oldest message first, current message last
        chain.reverse()

        contents: list[types.Content] = []
        for msg in chain:
            role = "model" if msg.author == self.bot.user else "user"
            clean_text = (
                msg.content
                .replace(f"<@{self.bot.user.id}>", "")
                .replace(f"<@!{self.bot.user.id}>", "")
                .strip()
            )

            # If text is empty (e.g. bot sent an embed or attachment), parse embed text
            if not clean_text and msg.embeds:
                embed_texts = []
                for emb in msg.embeds:
                    if emb.title:
                        embed_texts.append(emb.title)
                    if emb.description:
                        embed_texts.append(emb.description)
                    for f in emb.fields:
                        embed_texts.append(f"{f.name}: {f.value}")
                clean_text = "\n".join(embed_texts).strip()

            if not clean_text:
                continue

            # Merge consecutive turns with the same role (Gemini expects alternating turns)
            if contents and contents[-1].role == role:
                prev_text = contents[-1].parts[0].text
                contents[-1].parts[0].text = f"{prev_text}\n{clean_text}"
            else:
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=clean_text)]
                    )
                )

        # Gemini requires multi-turn chats to start with a 'user' turn
        if contents and contents[0].role == "model":
            contents.insert(
                0,
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="[Continuing our previous conversation]")]
                )
            )

        return contents

    async def _generate_response(self, contents: str | list[types.Content]) -> str:
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
                    contents=contents,
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
                            contents=contents,
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

        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.bot.user in message.mentions

        # Check if this message is a direct reply to Nico
        is_reply_to_me = False
        if message.reference and message.reference.message_id:
            referenced_msg = None
            if isinstance(message.reference.resolved, discord.Message):
                referenced_msg = message.reference.resolved
            else:
                referenced_msg = await self._resolve_message(message.channel, message.reference.message_id)

            if referenced_msg and referenced_msg.author == self.bot.user:
                is_reply_to_me = True

        # Trigger if mentioned, if directly replying to Nico, or in a DM
        if not (is_mentioned or is_reply_to_me or is_dm):
            return

        # Strip both standard user mentions (<@id>) and nickname mentions (<@!id>)
        clean_prompt = (
            message.content
            .replace(f"<@{self.bot.user.id}>", "")
            .replace(f"<@!{self.bot.user.id}>", "")
            .strip()
        )

        if not clean_prompt and not message.attachments:
            await message.reply("Hey there! How can I help you today?")
            return

        async with message.channel.typing():
            conversation_history = await self._build_conversation_history(message)
            contents = conversation_history if conversation_history else clean_prompt
            text_output = await self._generate_response(contents)

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