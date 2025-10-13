import discord
from discord.ext import tasks, commands
from discord import app_commands

import logging
import configparser

config = configparser.ConfigParser(interpolation=None)
config.read("./config.yaml")

logger = logging.getLogger(__name__)
logging.basicConfig(filename='food.log', encoding='utf-8', level=logging.DEBUG)

class foodCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    # region Listeners
    @commands.Cog.listener()
    async def on_ready(self):
        pass
    # end region

    # region data functions
    
    # end region

    # region Slash Commands

    # end region

    # region autolooping tasks


async def setup(bot: commands.Bot):
    await bot.add_cog(foodCog(bot))