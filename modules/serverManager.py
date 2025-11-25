import discord
from discord.ext import tasks, commands
from discord import app_commands
import datetime
import configparser
import asyncio

from mcrcon import MCRcon

config = configparser.ConfigParser(interpolation=None)
config.read("./config.yaml")

class serverManCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.serverIP = config.get("mcIP")
        self.rconPort = int(config.get("rconPort"))
        self.rconPass = config.get("rconPass")

    @app_commands.command(name="getplayers", description="Gets the current players on the server")
    async def playerCount(self, interaction: discord.interactions.Interaction):
        with MCRcon(self.serverIP, self.rconPass, self.rconPort) as mcr:
            resp = mcr.command("")

        await interaction.response.send_message(resp)

async def setup(bot: commands.Bot):
    await bot.add_cog(serverManCog(bot))