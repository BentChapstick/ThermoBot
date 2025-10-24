import discord
from discord.ext import tasks, commands
from discord import app_commands

import os
from dotenv import load_dotenv
import requests
import datetime
import peewee
import shutil
import logging
import configparser
import random

config = configparser.ConfigParser(interpolation=None)
config.read("./config.yaml")
DATABASE = peewee.SqliteDatabase(config.get("General", "database"))

load_dotenv()
TOKEN = os.getenv("IMMICH_TOKEN")
TIMEFORMAT = "%Y-%m-%dT%H:%M:%S%z"
HEADER = {
"Accept": "application/json",
'User-Agent': 'Thermo Bot',
'From': 'cec@conklinsystems.com',
'x-api-key': TOKEN,
"shared": "true"
}


logger = logging.getLogger(__name__)
logging.basicConfig(filename='./randomPicture.log', encoding='utf-8', level=logging.INFO, format="%(asctime)s;%(levelname)s;%(message)s")

class RandomImageCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        DATABASE.create_tables([Albums])

    # region Listeners
    @commands.Cog.listener()
    async def on_ready(self):
        self.postingChannel = self.bot.get_channel(int(config.get("General", "general")))
        self.pullRandom.start()

    # end region

    # region data functions
    async def getAlbums(self) -> list:
        albums = Albums.select()
        reordered = [album.uuid for album in albums]
        return reordered
    
    async def randomImage(self):
        FILE = f'randomThermo.jpg'
        albums = await self.getAlbums()

        temp = []
        for album in albums:
            r = requests.request("GET", f'https://photos.gumplab.com/api/albums/{album}', headers=HEADER)
            data = r.json()
            for thing in data["assets"]:
                temp.append(thing["id"])
        
        photos = list(set(temp))
        decidedPhoto = random.choice(photos)
        

        r = requests.request("GET", f'https://photos.gumplab.com/api/assets/{decidedPhoto}', headers=HEADER)
        fileRequest = requests.request("GET", f'https://photos.gumplab.com/api/assets/{decidedPhoto}/thumbnail', headers=HEADER, stream=True)

        with open(f'./ImageCache/{FILE}', "wb") as f:
            shutil.copyfileobj(fileRequest.raw, f)

        data:dict = r.json()

        thumbnail = discord.File(f'./ImageCache/{FILE}')

        embed = discord.Embed(
            title=f'{data["originalFileName"]}',
            description=f'Photo by {data["owner"]["name"]}\nWith {data["exifInfo"]["make"]} {data["exifInfo"]["model"]}\nhttps://photos.gumplab.com/photos/{decidedPhoto}',
            color=discord.Color.random(),
            timestamp=datetime.datetime.strptime(data["exifInfo"]["dateTimeOriginal"], TIMEFORMAT)
        )

        embed.set_image(
            url=f'attachment://{FILE}'
        )

        return embed, thumbnail

        print(data["owner"]["name"])
        print(f'{data["exifInfo"]["make"]} {data["exifInfo"]["model"]}')
        print(datetime.datetime.strptime(data["exifInfo"]["dateTimeOriginal"], TIMEFORMAT))

    # end region

    # region Slash Commands
    @app_commands.command(name="album_add", description="Add Album to search database")
    async def album_add(self, interaction: discord.Interaction, uuid: str, name: str):
        try:
            r = requests.request("GET", f'https://photos.gumplab.com/api/albums/{uuid}', headers=HEADER)
            # s = requests.request("GET", f'https://photos.gumplab.com/api/shared-links', headers=HEADER, json={"id": uuid})
        except Exception as e:
            await interaction.response.send_message("Error pinging photo server")
            logger.critical(e)
            return
        if r.status_code != 200:
            await interaction.response.send_message("Invalid album UUID", delete_after=300)
        else:
            Albums.replace(uuid=uuid, name=name).execute()
            logger.info(f'{interaction.user.name} added {name}-{uuid} to album database')
            await interaction.response.send_message(f'Added {name} to album database', delete_after=60)

    @app_commands.command(name="album_list", description="List albums in database")
    async def album_list(self, interaction: discord.Interaction):
        albums = Albums.select()
        reordered = [album.name for album in albums]
        await interaction.response.send_message(f'Album List: {reordered}', delete_after=300)

    @app_commands.command(name="album_random", description="Returns a random image")
    async def album_random(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pulling...", delete_after=30)
        target_channel = self.bot.get_channel(interaction.channel_id)
        try:
            embed, file = await self.randomImage()
            embed.set_footer(text=f'Requested by: {interaction.user.nick}')
            await target_channel.send(embed=embed, file=file)
        except Exception as e:
            await interaction.response.send_message("Error Pulling Image")
            print(f'Someone shoot me {e}')
            logger.error(e)
    # end region

    # region autolooping tasks
    # @tasks.loop(hours=1)
    @tasks.loop(time=[datetime.time(hour=11)])
    async def pullRandom(self):
        try:
            embed, file = await self.randomImage()
            await self.postingChannel.send(embed=embed, file=file)
        except Exception as e:
            print(f'Someone shoot me {e}')
            logger.error(e)

    # end region

async def setup(bot: commands.Bot):
    await bot.add_cog(RandomImageCog(bot))

class Albums(peewee.Model):
    uuid = peewee.TextField(primary_key=True)
    name = peewee.TextField(null=True)
    share = peewee.TextField(null=True)

    class Meta:
        database = DATABASE

if __name__ == "__main__":
    # r = requests.request("GET", f'https://photos.gumplab.com/api/albums', headers=HEADER)
    uuid = "7ecd0203-a496-4cf9-9dce-9b6a71131123"
    # for album in albums:
    # r = requests.request("POST", f'https://photos.gumplab.com/api/shared-links', headers=HEADER, json={"albumId": uuid, "expiresAt": str(datetime.datetime(year=2025, month=11, day=1)), "type": "ALBUM"})
    # print(r.json())
    r = requests.request("GET", f'https://photos.gumplab.com/api/shared-links', headers=HEADER, json={"id": uuid})
    data = r.json()
    # print(data)1
    print(r.json()[0]["key"])