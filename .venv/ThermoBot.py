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

poll_question = "When and where are we doing family dinner?"
poll_options = ["McNair", "Wads", "4:30", "5:00", "5:30", "6:00"]


async def schedule_daily_poll():
    await client.wait_until_ready()
    channel = client.get_channel(organizeEventsChannelID)
    while not client.is_closed():
        now = datetime.datetime.now()
        target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)  # Set your desired time here

        # If the target time is in the past, set it for the next day
        if now > target_time:
            target_time += datetime.timedelta(days=1)

        # Calculate the delay until the target time
        delay = (target_time - now).total_seconds()
        await asyncio.sleep(delay)  # Wait until the target time

        # Now we can run the poll
        await run_dinner_poll(channel)


async def run_dinner_poll(channel):
    if channel:
        poll_message = f"**Din Din Poll:** {poll_question}\n"
        poll_message += "\n".join([f"{index + 1}. {option}" for index, option in enumerate(poll_options)])
        poll_message += "\nReact with the number of your choice!"

        message = await channel.send(poll_message)

        # Add Unicode reactions for the options
        unicode_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣']
        for index in range(len(poll_options)):
            await message.add_reaction(unicode_numbers[index])


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    client.loop.create_task(schedule_daily_poll())  # Start the daily schedule task


@client.command()
async def start_poll(ctx):
    """Manually start the daily poll."""
    channel = client.get_channel(organizeEventsChannelID)
    await run_dinner_poll(channel)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id == quoteChannelID and not message.author.bot:
        print(f"Checking message: {message.content}")  # Debugging output
        # Check if the message does not contain either quote
        if '"' not in message.content and "'" not in message.content:
            print("Deleting message: No quotes found")  # Debugging output
            try:
                await message.delete()
            except discord.Forbidden:
                print("Missing permissions to delete messages.")
            except discord.HTTPException:
                print("Failed to delete the message.")
        else:
            print("Message retained: Quotes found")  # Debugging output

    await client.process_commands(message)

with open("Token", 'r') as file:
    token = file.read()
client.run(token)