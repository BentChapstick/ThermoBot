import os
import sys
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
import datetime
import asyncio

# Bot intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

FILEPATH = os.path.dirname(__file__)

# region Instantiation
if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    SERVER = os.getenv("SERVER")

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    client = commands.Bot(command_prefix='!', intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    # client.loop.create_task(schedule_daily_poll())  # Start the daily schedule task
    await client.tree.sync()

    print("---Ready---")

# endregion


# deprecated
# async def schedule_daily_poll():
#     await client.wait_until_ready()
#     channel = client.get_channel(FOODCHANNEL)
#     while not client.is_closed():
#         try:
#             now = datetime.datetime.now()
#             target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

#             if now > target_time:
#                 target_time += datetime.timedelta(days=1)

#             delay = (target_time - now).total_seconds()
#             await asyncio.sleep(delay)

#             # Get dinner options
#             await dinnerOptions(channel, "Dinner")

#             # Run the poll
#             await run_dinner_poll(channel)
#         except asyncio.CancelledError:
#             break  # Gracefully stop the loop if the task is cancelled
#         except Exception as e:
#             print(f"Error in scheduled poll task: {e}")
#             await asyncio.sleep(60)  # Try again after a minute in case of unexpected error

# endregion

async def load_extensions():
    """Load all modules/extensions/cogs from specificed directories"""
    dir_list = ['modules']
    exclusion_list = ['help']
    for dir_ in dir_list:
        print(f'=== Attempting to load all extensions in {dir_} directory ...')
        for filename in os.listdir(f'./{dir_}'):
            module = filename[:-3]
            if filename.endswith('.py') and module not in exclusion_list:
                try:
                    await client.load_extension(f'{dir_}.{module}')
                    print(f'\tSuccessfully loaded extension: {module}')
                except Exception as err:
                    exc = f'{type(err).__name__}: {err}'
                    print(f'\tFailed to load extension:  {module}\n\t\t{exc}')
    for excl_module in exclusion_list:
        print(f'=== Excluding the extension: {excl_module}')


def log_in():
    """Login function"""
    print('=== Initializing startup sequence ...')
    asyncio.run(load_extensions())
    print('=== Attempting to log in to bot ...')
    try:
        client.run(TOKEN) #Keep at the end of the file
    except discord.errors.HTTPException or discord.errors.LoginFailure as error:
        print('\nDiscord: Unsuccessful login:', error)
    else:
        sys.exit("Login Unsuccessful")


if __name__ == '__main__':
    log_in()