#cogs file for ping.py

import discord
from discord.ext import commands
from discord import app_commands

class PingCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)  # in ms
        await interaction.response.send_message(f"Pong! {interaction.user.display_name}, latency is {latency}ms.")

async def setup(bot: commands.Bot):
    await bot.add_cog(PingCog(bot))