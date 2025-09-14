import discord
from discord.ext import tasks, commands
from discord import app_commands
import requests
import datetime
import shutil
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)

HEADER = {
    'User-Agent': 'Personal Weather Bot',
    'From': 'cec@conklinsystems.com'
}

class weatherCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @app_commands.command(name="testweather", description="Test Weather Api")
    async def weathertest(self, interaction: discord.Interaction):
        try:
            DETROIT = {"LAT": 42.32899673212555, "LONG": -83.03964650833097}
            target = await self.geoCode("Detroit", "Mi")
            embed, file = await self.getWeather(float(target['lat']), float(target['lon']))

            await interaction.response.send_message(embed=embed, file=file)
        except Exception as e:
            logging.error("Failed to get weather information")
            logging.critical(e)
        else:
            logging.info(f'Weather test successful')

    @app_commands.command(name="weather", description="Lookup Weather in target city")
    async def weather(self, interaction: discord.Interaction, city: str, state: str):
        target = await self.geoCode(city, state)
        embed, file = await self.getWeather(float(target['lat']), float(target['lon']))

        await interaction.response.send_message("Check DMs")
        author = await self.bot.fetch_user(interaction.user.id)
        await author.send(embed=embed, file=file)

    #Run Refresh
    @app_commands.command(name="start_weather", description="Why isn't this task starting?")
    async def start_weather(self, interaction: discord.interactions.Interaction):
        await interaction.response.send_message("Attempting to start morning weather...", delete_after=30)
        self.morningWeather.start()

    async def geoCode(self, city: str, state: str) -> dict:
        r = requests.get(f'https://nominatim.openstreetmap.org/search?q={city},{state},USA&format=json', headers=HEADER)
        return {"lat": float(r.json()[0]["lat"]), "lon": float(r.json()[0]["lon"])}

    async def getWeather(self, lat: float, long: float) -> discord.Embed:

        loc = requests.get(url=f'https://api.weather.gov/points/{lat:.4f},{long:.4f}', headers=HEADER).json()
        forecast = requests.get(url=f'{loc["properties"]["forecast"]}', headers=HEADER).json()
        today = forecast["properties"]["periods"][0]
        tonight = forecast["properties"]["periods"][1]

        fileRequest = requests.get(f'https://radar.weather.gov/ridge/standard/{loc["properties"]["radarStation"]}_loop.gif', stream=True)

        with open(f'./ImageCache/{loc["properties"]["radarStation"]}_loop.gif', "wb") as f:
            shutil.copyfileobj(fileRequest.raw, f)

        radarForecast = discord.File(f'./ImageCache/{loc["properties"]["radarStation"]}_loop.gif', filename=f'{loc["properties"]["radarStation"]}_loop.gif')

        embed = discord.Embed(
            title=f'{loc["properties"]["relativeLocation"]["properties"]["city"]}, {loc["properties"]["relativeLocation"]["properties"]["state"]}',
            color=discord.Color.random(),
            # description=f'Today: {today["detailedForecast"]}\nTonight: {tonight["detailedForecast"]}',
            timestamp=datetime.datetime.now()
        )
        embed.set_image(
            url=f'attachment://{loc["properties"]["radarStation"]}_loop.gif'
        )
        embed.add_field(
            name="Today",
            value=f'{today["detailedForecast"]}',
            inline=False
        )
        embed.add_field(
            name="Tonight",
            value=f'{tonight["detailedForecast"]}',
            inline=False
        )
        return embed, radarForecast
    
    # @tasks.loop(hours=1)
    @tasks.loop(time=[datetime.time(hour=11)]) 
    async def morningWeather(self): #Morning Weather

        #Cormac

        try:
            target = await self.geoCode("Houghton", "Mi")
            embed, file = await self.getWeather(float(target['lat']), float(target['lon']))
            author = await self.bot.fetch_user(339471265427619840)
            await author.send(embed=embed, file=file)
        except Exception as e:
            logging.error("Failed to send weather information to Cormac")
            logging.critical(e)
        else:
            print(f'Weather sent to Cormac at {datetime.datetime.now().strftime("%X")}')


async def setup(bot: commands.Bot):
    await bot.add_cog(weatherCog(bot))