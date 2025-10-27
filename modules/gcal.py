import discord
from discord.ext import tasks, commands
from discord import app_commands

import os
from dotenv import load_dotenv
import requests
import datetime
import dateutil
import logging
import configparser

from google_auth_oauthlib.flow import InstalledAppFlow
import googleapiclient.discovery

config = configparser.ConfigParser(interpolation=None)
config.read("./config.yaml")

logger = logging.getLogger(__name__)
logging.basicConfig(filename='./calendar.log', encoding='utf-8', level=logging.INFO, format="%(asctime)s;%(levelname)s;%(message)s")

load_dotenv()
TOKEN = os.getenv("GCAL_TOKEN")

class CalendarCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot

        scopes = ['https://www.googleapis.com/auth/calendar.events.readonly']
        flow = InstalledAppFlow.from_client_secrets_file('gCalSecret.json', scopes=scopes)
        credentials = flow.run_local_server(port=0)
        self.service: googleapiclient.discovery.Resource = googleapiclient.discovery.build('calendar', 'v3', credentials=credentials)
        
        self.thermoCal = "c_454bf06f6bc96b5ce43d75cba2093607f4ce0fb8d9c17677ec6e3b601def19c4@group.calendar.google.com"

    # region Listeners
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Calendar Module Loaded")
        self.eventsToday.start()
        self.postingChannel = self.bot.get_channel(int(config.get("General", "organize")))

    # end region

    # region Data Functions

    async def gCalToday(self) -> list:
        local = dateutil.tz.gettz('America/New_York')
        timeMax = datetime.datetime.now(local) + datetime.timedelta(days=1)
        timeMin = datetime.datetime.now(local)
        timeMax = datetime.datetime(year=timeMax.year, month=timeMax.month, day=timeMax.day, tzinfo=local)
        timeMin = datetime.datetime(year=timeMin.year, month=timeMin.month, day=timeMin.day, tzinfo=local)

        events_result = self.service.events().list(calendarId=self.thermoCal, timeMax=timeMax.isoformat(), timeMin=timeMin.isoformat()).execute()
        events = events_result.get('items', [])

        eventList = []
        for event in events:
            print(f"Event Summary: {event['summary']}")
            if "dateTime" in event["start"].keys():
                startTime = datetime.datetime.strptime(event['start']['dateTime'], "%Y-%m-%dT%H:%M:%S%z")
                endTime = datetime.datetime.strptime(event['end']['dateTime'], "%Y-%m-%dT%H:%M:%S%z")
            elif "date" in event["start"].keys():
                startTime = datetime.datetime.strptime(event['start']['date'], "%Y-%m-%d")
                endTime = datetime.datetime.strptime(event['end']['date'], "%Y-%m-%d")
            
            eventList.append(tuple((event['summary'], startTime, endTime)))

        return eventList
    # end region

    # region Slash Commands

    # end region

    # region Autolooping Tasks
    @tasks.loop(time=[datetime.time(hour=11)])
    async def eventsToday(self):
        try:
            events = await self.gCalToday()
            if len(events) > 0:
                outString = ""
                TIMEFORMAT = "%I:%M%p"
                for event in events:
                    if event[1] == event[2]:
                        outString = f'All Day: {event[0]}\n' + outString
                    else:
                        outString += f'{event[0]} from {event[1].strftime(TIMEFORMAT)} to {event[2].strftime(TIMEFORMAT)}\n'

                embed = discord.Embed(
                    title=f'Today\'s events:',
                    description=outString,
                    color=discord.Color.random(),
                    timestamp=timeMin
                )
                logger.info("Sent todays events")
                await self.postingChannel.send(embed=embed)
            else:
                logger.info("No events today")

        except Exception as e:
            print(f'Someone shoot me {e}')
            logger.error(e)

    # end region

async def setup(bot: commands.Bot):
    await bot.add_cog(CalendarCog(bot))

if __name__ == "__main__":
    local = dateutil.tz.gettz('America/New_York')
    timeMax = datetime.datetime.now(local) + datetime.timedelta(days=1)
    timeMin = datetime.datetime.now(local)
    timeMax = datetime.datetime(year=timeMax.year, month=timeMax.month, day=timeMax.day, tzinfo=local)
    timeMin = datetime.datetime(year=timeMin.year, month=timeMin.month, day=timeMin.day, tzinfo=local)

    scopes = ['https://www.googleapis.com/auth/calendar.events.readonly']
    flow = InstalledAppFlow.from_client_secrets_file('client_secret_534155768771-rtgqeltsqqj3hb06fvnvf3rqhu9hvq9q.apps.googleusercontent.com.json', scopes=scopes)
    credentials = flow.run_local_server(port=0)
    service: googleapiclient.discovery.Resource = googleapiclient.discovery.build('calendar', 'v3', credentials=credentials)
    
    thermoCal = "c_454bf06f6bc96b5ce43d75cba2093607f4ce0fb8d9c17677ec6e3b601def19c4@group.calendar.google.com"

    events_result = service.events().list(calendarId=thermoCal, timeMax=timeMax.isoformat(), timeMin=timeMin.isoformat()).execute()
    # events_result = service.events().list(calendarId=thermoCal).execute()
    events = events_result.get('items', [])

    eventList = []
    for event in events:
        # print(f"Event Summary: {event['summary']}")
        if "dateTime" in event["start"].keys():
            startTime = datetime.datetime.strptime(event['start']['dateTime'], "%Y-%m-%dT%H:%M:%S%z")
            endTime = datetime.datetime.strptime(event['end']['dateTime'], "%Y-%m-%dT%H:%M:%S%z")
        elif "date" in event["start"].keys():
            startTime = datetime.datetime.strptime(event['start']['date'], "%Y-%m-%d")
            endTime = datetime.datetime.strptime(event['end']['date'], "%Y-%m-%d")
        
        eventList.append(tuple((event['summary'], startTime, endTime)))
    if len(eventList) == 0:
        print("Benis")
    else:
        outString = ""
        TIMEFORMAT = "%I:%M%p"
        for event in eventList:
            if event[1] == event[2]:
                outString = f'All Day: {event[0]}\n' + outString
            else:
                outString += f'{event[0]} from {event[1].strftime(TIMEFORMAT)} to {event[2].strftime(TIMEFORMAT)}\n'


        print(outString)
    # embed = discord.Embed(
    #         title=f'Today\'s events:',
    #         description=f'Photo by {data["owner"]["name"]}\nWith {data["exifInfo"]["make"]} {data["exifInfo"]["model"]}\nhttps://photos.gumplab.com/photos/{decidedPhoto}',
    #         color=discord.Color.random(),
    #         timestamp=timeMin
    #     )