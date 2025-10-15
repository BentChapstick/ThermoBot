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
        self.quotes = int(config.get("General", "quotes"))
        self.actions_channel = int(config.get("General", "actionlog"))

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
            if 'ping' in message.content.lower():
                index = message.content.lower().find('ping')
                if message.content[index] == 'P':
                    await message.channel.send('Pong')
                else:
                    await message.channel.send('pong')

            if 'pong' in message.content.lower():
                index = message.content.lower().find('pong')
                if message.content[index] == 'P':
                    await message.channel.send('Ping')
                else:
                    await message.channel.send('ping')

        # Verify messages sent in the quotes channel contain quotes. 
        if message.channel.id == self.quotes and not message.author.bot:
            await self.actionLogMessage(f"Checking message by {message.author}: {message.content}")
            # Check if the message does not contain either quote
            if '"' not in message.content and "'" not in message.content\
                    and '“' not in message.content:
                await self.actionLogMessage("Deleting message: No quotes found")
                try:
                    await message.delete()
                except discord.Forbidden:
                    await self.actionLogMessage("Missing permissions to delete messages.")
                except discord.HTTPException:
                    await self.actionLogMessage("Failed to delete the message.")
            else:
                await self.actionLogMessage("Message retained: Quotes found")  # Debugging output

        await self.bot.process_commands(message)

    async def actionLogMessage(self, message):
        channel = self.bot.get_channel(self.actions_channel)
        await channel.send(message)
    # end region

    # region data functions
    
    # end region

    # region Slash Commands

    # end region

    # region autolooping tasks


async def setup(bot: commands.Bot):
    await bot.add_cog(ManageCog(bot))