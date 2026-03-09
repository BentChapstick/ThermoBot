from pathlib import Path
import discord
from discord.ext import tasks, commands
from discord import app_commands

import datetime
import dateutil
import logging
import configparser
import asyncio

from oauth2client.service_account import ServiceAccountCredentials
import googleapiclient.discovery

config = configparser.ConfigParser(interpolation=None)
config.read("./config.yaml")

logger = logging.getLogger(__name__)
logging.basicConfig(filename='./calendar.log', encoding='utf-8', level=logging.INFO, format="%(asctime)s;%(levelname)s;%(message)s")

class CalendarCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.interface = calendarInterface()

    # region Listeners
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Calendar Module Loaded")
        self.eventsToday.start()

    # end region

    async def eventEmbed(self, titlecard: str, description: str) -> discord.Embed:
        embed = discord.Embed(
            title=titlecard,
            description=description,
            color=discord.Color.random(),
            timestamp=datetime.datetime.now()
        )

        return embed
    # region Slash Commands
    @app_commands.command(name="test_calendar", description="Test Calendar Integration")
    async def test_calendar(self, interaction: discord.Interaction):
        try:
            events = await self.interface.gCalFuture()
            if len(events) > 0:
                processed = await self.interface.eventProcess(events)

                embed = await self.eventEmbed(f'Today\'s events:', processed)

                logger.info("Sent todays events")
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("No events today")
                logger.info("No events today")

        except Exception as e:
            print(f'Someone shoot me\n {e}')
            logger.error(e)

    @app_commands.command(name="calendar_future", description="# days into future")
    async def calendar_future(self, interaction: discord.Interaction, days: int):
        try:
            events = await self.interface.gCalFuture(days)
            if len(events) > 0:
                processed = await self.interface.eventProcess(events)

                embed = await self.eventEmbed(f'#{days} days into the future events:', processed)
    
                logger.info("Sent calendar events")
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(f'No events in the next {days} days')
                logger.info("No events in scope")

        except Exception as e:
            print(f'Someone shoot me {e}')
            logger.error(e)
    # end region

    # region Autolooping Tasks
    # @tasks.loop(hours=1)
    @tasks.loop(time=[datetime.time(hour=11)])
    async def eventsToday(self):
        postingChannel = await self.bot.fetch_channel(int(config.get("General", "organize")))
        try:
            events = await self.interface.gCalFuture()
            if len(events) > 0:
                processed = await self.interface.eventProcess()

                embed = await self.eventEmbed(f'Today\'s events:', processed)

                logger.info("Sent todays events")
                await postingChannel.send(embed=embed)
            else:
                logger.info("No events today")

        except Exception as e:
            print(f'Someone shoot me \n {e}')
            logger.error(e)

    # end region

async def setup(bot: commands.Bot):
    await bot.add_cog(CalendarCog(bot))

class calendarInterface():
    def __init__(self):
        scopes = ['https://www.googleapis.com/auth/calendar.events.readonly']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(f'{Path(__file__).parent.parent}/gCalSecret.json', scopes=scopes)
        self.service: googleapiclient.discovery.Resource = googleapiclient.discovery.build('calendar', 'v3', credentials=credentials)
        
        self.thermoCal = "c_454bf06f6bc96b5ce43d75cba2093607f4ce0fb8d9c17677ec6e3b601def19c4@group.calendar.google.com"

    async def gCalFuture(self, days: int = 1) -> list:
        local = dateutil.tz.gettz('America/New_York')
        timeMax = datetime.datetime.now(local) + datetime.timedelta(days=days)
        timeMin = datetime.datetime.now(local)
        timeMax = datetime.datetime(year=timeMax.year, month=timeMax.month, day=timeMax.day, tzinfo=local)
        timeMin = datetime.datetime(year=timeMin.year, month=timeMin.month, day=timeMin.day, tzinfo=local)

        events_result = self.service.events().list(calendarId=self.thermoCal, timeMax=timeMax.isoformat(), timeMin=timeMin.isoformat()).execute()
        events = events_result.get('items', [])

        eventList = []
        for event in events:
            location = None
            # print(f"Event Summary: {event['summary']}")
            if "dateTime" in event["start"].keys():
                startTime = datetime.datetime.strptime(event['start']['dateTime'], "%Y-%m-%dT%H:%M:%S%z")
                endTime = datetime.datetime.strptime(event['end']['dateTime'], "%Y-%m-%dT%H:%M:%S%z")
            elif "date" in event["start"].keys():
                startTime = datetime.datetime.strptime(event['start']['date'], "%Y-%m-%d")
                endTime = datetime.datetime.strptime(event['start']['date'], "%Y-%m-%d")

            if "location" in event.keys():
                location = event["location"]
            
            eventList.append(tuple((event['summary'], startTime, endTime, location)))

        return eventList
    
    async def eventProcess(self, events: list) -> str:
        outString = ""
        TIMEFORMAT = "%I:%M%p"
        for event in events:
            if event[1] == event[2]:
                if event[3] is not None:
                    outString = f'All Day: {event[0]} at {event[3]} \n' + outString
                else:
                    outString = f'All Day: {event[0]}\n' + outString
            else:
                if event[3] is not None:
                    outString += f'{event[0]} at {event[3]} from {event[1].strftime(TIMEFORMAT)} to {event[2].strftime(TIMEFORMAT)}\n'
                else:
                    outString += f'{event[0]} from {event[1].strftime(TIMEFORMAT)} to {event[2].strftime(TIMEFORMAT)}\n'
        return outString
    
if __name__ == "__main__":
    interface = calendarInterface()
    events = asyncio.run(interface.gCalFuture())
    print(asyncio.run(interface.eventProcess(events)))