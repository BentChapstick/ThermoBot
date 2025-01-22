import discord
from discord.ext import commands, tasks
import datetime
import asyncio

# Bot intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

# Channel IDs
debugChannelID = 1280991837913481278
quoteChannelID = 1280656734196596858
organizeEventsChannelID = 1299157684162920479
actionLogChannelID = 1305223850153480245

poll_question = "When and where are we doing family dinner?"
poll_options = ["McNair", "Wads", "4:30", "5:00", "5:30", "6:00"]


async def schedule_daily_poll():
    await client.wait_until_ready()
    channel = client.get_channel(organizeEventsChannelID)
    while not client.is_closed():
        try:
            now = datetime.datetime.now()
            target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

            if now > target_time:
                target_time += datetime.timedelta(days=1)

            delay = (target_time - now).total_seconds()
            await asyncio.sleep(delay)

            # Run the poll
            await run_dinner_poll(channel)
        except asyncio.CancelledError:
            break  # Gracefully stop the loop if the task is cancelled
        except Exception as e:
            print(f"Error in scheduled poll task: {e}")
            await asyncio.sleep(60)  # Try again after a minute in case of unexpected error

async def run_dinner_poll(channel):
    if channel:
        poll_message = f"**Din Din Poll:** {poll_question}\n"
        poll_message += "\n".join([f"{index + 1}. {option}" for index, option in enumerate(poll_options)])
        poll_message += "\nReact with the number of your choice!"

        message = await channel.send(poll_message)

        # Add Unicode reactions for the options
        unicode_numbers = ['🇲', '🇼', '🕟', '🕔', '🕠', '🕕']
        for index in range(len(poll_options)):
            await message.add_reaction(unicode_numbers[index])

        # Wait for 7 hours before closing the poll (end at 4pm)
        await asyncio.sleep(25200)  # 7 hours in seconds
        end_dinner_poll(channel,message)

async def end_dinner_poll(channel, message):
    # Send a message about the poll results and delete the poll
    # Determine poll results
    results = message.reactions
    max_votes = 0
    time_winner = null
    if results[0].count > results[1].count:
        channel.send("Magnificent McNasty meal")
    else:
        channel.send("Wonderful Wads wins")
    for i in range(2, 6):
        if results[i].count > max_votes:
            max_votes = results[i]
            time_winner = results[i]
    channel.send("eating time at %s" % time_winner.emoji)
    await message.delete()  # Delete the poll message

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    client.loop.create_task(schedule_daily_poll())  # Start the daily schedule task


@client.command()
async def start_poll(ctx):
    # Manually start the daily poll
    channel = client.get_channel(organizeEventsChannelID)
    await run_dinner_poll(channel)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not message.author.bot:
        if 'Ping' in message.content or 'ping' in message.content:
            await message.channel.send('Pong')


    if message.channel.id == quoteChannelID and not message.author.bot:
        await actionLogMessage(f"Checking message by {message.author}: {message.content}")
        # Check if the message does not contain either quote
        if '"' not in message.content and "'" not in message.content\
                and '“' not in message.content:
            await actionLogMessage("Deleting message: No quotes found")
            try:
                await message.delete()
            except discord.Forbidden:
                await actionLogMessage("Missing permissions to delete messages.")
            except discord.HTTPException:
                await actionLogMessage("Failed to delete the message.")
        else:
            await actionLogMessage("Message retained: Quotes found")  # Debugging output

    await client.process_commands(message)

async def actionLogMessage(message):
    channel = client.get_channel(actionLogChannelID)
    await channel.send(message)

try:
    with open("Token", 'r') as file:
        token = file.read()
except FileNotFoundError:
    print("Token file not found. Please ensure the 'Token' file exists.")
    exit(1)
except Exception as e:
    print(f"An error occurred: {e}")
    exit(1)

try:
    client.run(token)
except Exception as e:
    print(f"An error occurred: {e}")