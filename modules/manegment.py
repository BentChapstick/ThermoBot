import discord
from discord.ext import tasks, commands
from discord import app_commands

import logging
import configparser

config = configparser.ConfigParser(interpolation=None)
config.read("./config.yaml")

logger = logging.getLogger(__name__)
logging.basicConfig(filename='management.log', encoding='utf-8', level=logging.DEBUG)

class ManageCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.quotes
        self.actions

    # region Listeners
    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.message.Message):
        if message.author == self.bot.user:
            return

        # Any message that was not sent by the bot
        if not message.author.bot:
            if 'Ping' in message.content or 'ping' in message.content.lower():
                await message.channel.send('Pong')

            if 'Pong' in message.content or 'pong' in message.content.lower():
                await message.channel.send('ping')

        # Verify messages sent in the quotes channel contain quotes. 
        if message.channel.id == quoteChannelID and not message.author.bot:
            await actionLogMessage(f"Checking message by {message.author}: {message.content}")
            # Check if the message does not contain either quote
            if '"' not in message.content and "'" not in message.content\
                    and '“' not in message.content:
                await actionLogMessage("Deleting message: No quotes found")
                try:
                    await message.delete()
                except discord.Forbidden:
                    await actionLogMessage("Missing permissions to delete messages.")
                except discord.HTTPException:
                    await actionLogMessage("Failed to delete the message.")
            else:
                await actionLogMessage("Message retained: Quotes found")  # Debugging output

        await self.bot.process_commands(message)

    async def actionLogMessage(message):
        channel = self.bot.get_channel(actionLogChannelID)
        await channel.send(message)
    # end region

    # region data functions
    
    # end region

    # region Slash Commands

    # end region

    # region autolooping tasks


async def setup(bot: commands.Bot):
    await bot.add_cog(ManageCog(bot))