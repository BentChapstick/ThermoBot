import discord
from discord.ext import tasks, commands
from discord import app_commands
import requests
import datetime
import dateutil
import shutil
import logging
import configparser

config = configparser.ConfigParser(interpolation=None)
config.read("./config.yaml")

logger = logging.getLogger(__name__)
logging.basicConfig(filename='weather.log', encoding='utf-8', level=logging.DEBUG)

HEADER = {
    'User-Agent': 'Personal Weather Bot',
    'From': 'cec@conklinsystems.com'
}

class weatherCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.morningWeather.start()
        self.auroraCheck.start()
    
# region Slash Commands
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
        await interaction.response.send_message("Check DMs", delete_after=60)

        target = await self.geoCode(city, state)
        embed, file = await self.getWeather(float(target['lat']), float(target['lon']))

        author = await self.bot.fetch_user(interaction.user.id)
        await author.send(embed=embed, file=file)

    @app_commands.command(name="aurora_forecast", description="3 Hours Aurora Prediction")
    async def aurora_forecast(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pulling...", delete_after=30)
        target_channel = self.bot.get_channel(interaction.channel_id)

        try:
            embed, file = await self.getAurora3hour()
            await target_channel.send(embed=embed, file=file)
        except Exception as e:
            await target_channel.send(f'Error pulling Forecast')
            logger.log(logging.FATAL, e)

    @app_commands.command(name="aurora_soon_forecast", description="Half Hour Aurora Prediction")
    async def aurora_soon_forecast(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pulling...", delete_after=30)
        target_channel = self.bot.get_channel(interaction.channel_id)

        try:
            embed, file = await self.getAuroraHalfHour()
            await target_channel.send(embed=embed, file=file)
        except Exception as e:
            await target_channel.send(f'Error pulling Forecast')
            logger.log(logging.FATAL, e)

    #Run Refresh
    # @app_commands.command(name="start_weather", description="Why isn't this task starting?")
    # async def start_weather(self, interaction: discord.interactions.Interaction):
    #     await interaction.response.send_message("Attempting to start morning weather...", delete_after=30)
    #     self.morningWeather.start()
# end region

# region Private Functions
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
    
    async def get3hour(self): #Aurora Forecast
        FILE = f'geospace_3_hour.png'
        fileRequest = requests.get(f'https://services.swpc.noaa.gov/images/geospace/{FILE}', stream=True)
        
        with open(f'./ImageCache/{FILE}', "wb") as f:
            shutil.copyfileobj(fileRequest.raw, f)

        futureForecast = discord.File(f'./ImageCache/{FILE}')

        embed = discord.Embed(
            title=f'NOAA 3 Hour Aurora Forecast',
            color=discord.Color.random(),
            timestamp=datetime.datetime.now()
        )

        embed.set_image(
            url=f'attachment://{FILE}'
        )

        return embed, futureForecast
# end region

# region Autolooping Tasks
    @tasks.loop(minutes=30)
    async def auroraCheck(self):
        TIMEFORMAT = "%Y-%m-%dT%H:%M:%S%z"
        local = dateutil.tz.gettz('America/New_York')

        r = requests.get(f'https://services.swpc.noaa.gov/json/ovation_aurora_latest.json', headers=HEADER)
        data = r.json()
        obTime = datetime.datetime.strptime(data["Observation Time"], TIMEFORMAT)
        forcastTime = datetime.datetime.strptime(data["Forecast Time"], TIMEFORMAT)

        target = self.geoCode("Houghton", "Mi")
        print(target)
        # print(type(target["lat"]))
        # print(obTime)
        print(forcastTime.astimezone(local))
        best: list
        for forcast in data["coordinates"]: #[Longitude, Latitude, Aurora]
            if target["lon"] < 0:
                lon = int(360 + target["lon"])
            else:
                lon = int(target["lon"])

            lat = int(target["lat"])

            if forcast[0] == lon and forcast[1] == lat:
                best = forcast
        if best > self.threshold and (self.lastaurorapub + datetime.timedelta(days=1)) < datetime.datetime.now():
            self.lastaurorapub = datetime.datetime.now()
            target_channel = self.bot.get_channel(self.announcements_channel)

            try:
                embed, file = await self.getAuroraHalfHour()
                embed.description = f'Aurora Likelyhood passed above {self.threshold}'
                await target_channel.send(embed=embed, file=file)
            except Exception as e:
                await target_channel.send(f'Error pulling Forecast')
            logger.log(logging.FATAL, e)

    # @tasks.loop(hours=1)
    @tasks.loop(time=[datetime.time(hour=11)]) 
    async def morningWeather(self): #Morning Weather

        #Thermo

        try:
            target = await self.geoCode("Houghton", "Mi")
            embed, file = await self.getWeather(float(target['lat']), float(target['lon']))
            author = await self.bot.fetch_channel(1281273813556006932) #Bot Spam
            await author.send(embed=embed, file=file)
        except Exception as e:
            logging.error("Failed to send weather information to Thermo General")
            logging.critical(e)
        else:
            print(f'Weather sent to Thermo at {datetime.datetime.now().strftime("%X")}')

# end region

async def setup(bot: commands.Bot):
    await bot.add_cog(weatherCog(bot))