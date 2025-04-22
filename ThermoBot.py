import discord
from discord.ext import commands, tasks
import datetime
import asyncio
import zoneinfo


#Referenced Files
import foodBot
import chartwells_queryFast
import xkcd

# Bot intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

# Channel IDs
debugChannelID = 1280991837913481278
quoteChannelID = 1280656734196596858
organizeEventsChannelID = 772510418920144936
FOODCHANNEL = 1358906415426830387
# organizeEventsChannelID = 1299157684162920479
actionLogChannelID = 1305223850153480245

SERVER = 1280656645231218793

poll_question = "When and where are we doing family dinner?"
poll_options = ["McNair", "Wads", "4:30", "5:00", "5:30", "6:00"]


async def schedule_daily_poll():
    await client.wait_until_ready()
    channel = client.get_channel(FOODCHANNEL)
    while not client.is_closed():
        try:
            now = datetime.datetime.now()
            target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

            if now > target_time:
                target_time += datetime.timedelta(days=1)

            delay = (target_time - now).total_seconds()
            await asyncio.sleep(delay)

            # Get dinner options
            await dinnerOptions(channel)

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
    time_winner = None
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

# Read database and send the dinner options
async def dinnerOptions(channel):
    menu = foodBot.getMeals("Dinner")

    text = ""

    text += f"# Today's Options\n"
    for food_hall in foodBot.Hall:
        hall_name = food_hall.value[0]
        locations = food_hall.value[1]

        text += f"## {hall_name}\n"
        # total food options for the hall (out of all sub-locations)
        total_options_count = 0
        for location in locations:
            location_text = ""
            # count of options at the specific sub-location
            location_options_count = 0
            location_text += f"### {location}\n"
            menu_items = menu[hall_name][location]
            for food_option in menu_items:
                location_options_count += 1
                location_text += ("- " + food_option + '\n')

            # if this sub-location has any food options, print the
            # location and its options
            if location_options_count > 0:
                total_options_count += location_options_count
                text += location_text

        # if the hall had no food options for any of its sub-locations,
        # print is a closed
        if total_options_count <= 0:
            text += "- Closed\n"

    await channel.send(text)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    client.loop.create_task(schedule_daily_poll())  # Start the daily schedule task
    pullMenuTask.start()
    await client.tree.sync(guild=discord.Object(id=SERVER))


@client.command()
async def start_poll(ctx):
    # Manually start the daily poll
    channel = client.get_channel(FOODCHANNEL)
    await dinnerOptions(channel)

    await run_dinner_poll(channel)    

# region AutoLooped Tasks
@tasks.loop(time=datetime.time(hour=7, minute=5, tzinfo=zoneinfo.ZoneInfo("America/Detroit"))) #Refresh Menu at 7 am
async def pullMenuTask():
    await chartwells_queryFast.main()
    

# end region

# region Slash Commands

@client.tree.command( #XKCD Get Current
    name="xkcd-cur",
    description="Current XKCD Comic",
    guild=discord.Object(id=SERVER)
)
async def xkcdcur(interaction: discord.interactions.Interaction):
    comic:dict = xkcd.latestxkcd()
    embed = discord.Embed(
        title=comic["title"],
        color=discord.Color.random(),
        description=comic["alt"],
        timestamp=datetime.datetime(year=int(comic["year"]),month=int(comic["month"]),day=int(comic["day"]))
    ).set_image(
        url=comic["img"]
    )
    await interaction.response.send_message(embed=embed)

@client.tree.command( #XKCD Get Random
    name="xkcd-rand",
    description="Random XKCD Comic",
    guild=discord.Object(id=SERVER)
)
async def xkcdrand(interaction: discord.interactions.Interaction):
    comic:dict = xkcd.randomXKCD()
    embed = discord.Embed(
        title=comic["title"],
        color=discord.Color.random(),
        description=comic["alt"],
        timestamp=datetime.datetime(year=int(comic["year"]),month=int(comic["month"]),day=int(comic["day"]))
    ).set_image(
        url=comic["img"]
    )
    await interaction.response.send_message(embed=embed)

#Pull and populate the Database with food options.
@client.tree.command(
    name="update-menu",
    description="Updates the Menu Database",
    guild=discord.Object(id=SERVER)
)
async def pullMenu(interaction: discord.interactions.Interaction):
    print("Getting new menu")
    await chartwells_queryFast.main()

# endregion

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not message.author.bot:
        if 'Ping' in message.content or 'ping' in message.content.lower():
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


