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
        self.serverIP = config.get("General","mcIP")
        self.rconPort = int(config.get("General", "rconPort"))
        self.rconPass = config.get("General", "rconPass")

    @app_commands.command(name="getplayers", description="Gets the current players on the server")
    async def playerCount(self, interaction: discord.interactions.Interaction):
        with MCRcon(self.serverIP, self.rconPass, self.rconPort) as mcr:
            resp = mcr.command("list")

        await interaction.response.send_message(resp)

    @app_commands.command(name="addwhitelist", description="add your minecraft username to the server whitelist")
    async def addWhitelist(self, interaction: discord.interactions.Interaction, username: str):
        with MCRcon(self.serverIP, self.rconPass, self.rconPort) as mcr:
            resp = mcr.command(f"whitelist add {username}")
        print(f"Server responded: {resp}")
        await interaction.response.send_message(resp)

async def setup(bot: commands.Bot):
    await bot.add_cog(serverManCog(bot))