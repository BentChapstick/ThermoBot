import os

import discord
from discord.ext import commands
from discord import app_commands
import datetime
import requests
import random

class XKCDCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.XKCDCURRENT = "https://xkcd.com/info.0.json"
        self.XKCDARCHIVE = "https://xkcd.com/{number}/info.0.json"

    #XKCD Get Current
    @app_commands.command(name="xkcd-cur", description="Current XKCD Comic")
    async def xkcdcur(self, interaction: discord.interactions.Interaction):
        comic:dict = self.latestxkcd()
        embed = discord.Embed(
            title=comic["title"],
            color=discord.Color.random(),
            description=comic["alt"],
            timestamp=datetime.datetime(year=int(comic["year"]),month=int(comic["month"]),day=int(comic["day"]))
        ).set_image(
            url=comic["img"]
        )
        await interaction.response.send_message(embed=embed)

    #XKCD Get Random
    @app_commands.command(name="xkcd-rand", description="Random XKCD Comic")
    async def xkcdrand(self, interaction: discord.interactions.Interaction):
        comic:dict = self.randomXKCD()
        embed = discord.Embed(
            title=comic["title"],
            color=discord.Color.random(),
            description=comic["alt"],
            timestamp=datetime.datetime(year=int(comic["year"]),month=int(comic["month"]),day=int(comic["day"]))
        ).set_image(
            url=comic["img"]
        )
        await interaction.response.send_message(embed=embed)

    def latestxkcd(self) -> dict:
        r = requests.get(self.XKCDCURRENT)
        intake = r.json()
        return intake

    def maxXKCD(self) -> int:
        return int(self.latestxkcd()["num"])

    def randomXKCD(self) -> dict:
        r= requests.get(self.XKCDARCHIVE.format(number=random.randint(1, self.maxXKCD())))
        intake = r.json()
        return intake

async def setup(bot: commands.Bot):
    await bot.add_cog(XKCDCog(bot))