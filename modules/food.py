import discord
from discord.ext import tasks, commands
from discord import app_commands
import datetime
import logging
import configparser
import zoneinfo
import asyncio

#Referenced Files
import foodBot
import chartwells_queryFast

config = configparser.ConfigParser(interpolation=None)
config.read("./config.yaml")

logger = logging.getLogger(__name__)
logging.basicConfig(filename='food.log', encoding='utf-8', level=logging.DEBUG, format="%(asctime)s;%(levelname)s;%(message)s")

class foodCog(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.food_channel = int(config.get("General", "food"))

        self.poll_question = "When and where are we doing family dinner?"
        self.poll_options = ["McNair", "Wadsworth", "DHH", "4:30", "5:00", "5:30", "6:00"]
        self.dining_hall_is_open = {"McNair" : True, "Wadsworth" : True, "DHH" : True}

    # region Listeners
    @commands.Cog.listener()
    async def on_ready(self):
        self.pullMenuTask.start()
        self.daily_poll_task.start()

    # end region

    # region data functions
    async def dinnerOptions(self, channel, meal):
        menu = foodBot.getMeals(f"{meal}")

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
                self.dining_hall_is_open[hall_name] = False
            else:
                self.dining_hall_is_open[hall_name] = True

        await channel.send(text)

    async def run_dinner_poll(self, channel):
        if channel:

            poll_message = f"**Din Din Poll:** {self.poll_question}\n"
            poll_message += "\n".join([f"{index + 1}. {option}" for index, option in enumerate(self.poll_options)])
            poll_message += "\nReact with the number of your choice!"

            message = await channel.send(poll_message)

            # Add Unicode reactions for the options
            unicode_numbers = ['🇲', '🇼', '🇩', '🕟', '🕔', '🕠', '🕕']
            for index in range(len(self.poll_options)):
                if (index > 2 or self.dining_hall_is_open[self.poll_options[index]]):
                    await message.add_reaction(unicode_numbers[index])

            # Wait for 7 hours before closing the poll (end at 4pm)
            await asyncio.sleep(25200)  # 7 hours in seconds
            self.end_dinner_poll(channel,message)
    

    async def end_dinner_poll(self, channel: discord.channel, message: discord.message.Message):
        # Send a message about the poll results and delete the poll
        # Determine poll results
        results = message.reactions
        max_votes = 0
        time_winner = None
        location_winner = 0
        for i in range(1,3):
            if results[i].count > results[location_winner].count:
                location_winner = i 
        
        if location_winner == 0:
            channel.send("Magnificent McNasty meal")
        elif location_winner == 1:
            channel.send("Wonderful Wads wins")
        else:
            channel.send("Dastardly DHH dinning")
        
        for i in range(3, 7):
            if results[i].count > max_votes:
                max_votes = results[i]
                time_winner = results[i]
        channel.send("eating time at %s" % time_winner.emoji)
        await message.delete()  # Delete the poll message
    # end region

    # region Slash Commands
    @app_commands.command(name="update-menu", description="Updates the Menu Database")
    async def pullMenu(self, interaction: discord.interactions.Interaction):
        print("Getting new menu")
        await interaction.response.send_message("Updating")
        await chartwells_queryFast.main()
        await interaction.response.edit_message("Updated")

    @app_commands.command(name="start-poll", description="Starts a dinner poll in the food channel") #Manually start dinner poll
    async def start_poll(self, interaction: discord.interactions.Interaction):
        # Manually start the daily poll
        channel = self.bot.get_channel(self.food_channel)
        await interaction.response.send_message("Starting Poll...", delete_after=30)
        await self.dinnerOptions(channel, "Dinner")

        await self.run_dinner_poll(channel)

    @app_commands.command(name="lunch_menu", description="Lunch Menu")
    async def lunch_menu(self, interaction: discord.interactions.Interaction):
        await interaction.response.send_message("Accessing...", delete_after=30)
        channel = self.bot.get_channel(interaction.channel_id)
        await self.dinnerOptions(channel, "Lunch")

    @app_commands.command(name="dinner_menu", description="Dinner Menu")
    async def dinner_menu(self, interaction: discord.interactions.Interaction):
        await interaction.response.send_message("Accessing...", delete_after=30)
        channel = self.bot.get_channel(interaction.channel_id)
        await self.dinnerOptions(channel, "Dinner")

    # end region

    # region autolooping tasks
    @tasks.loop(time=datetime.time(hour=7, minute=5, tzinfo=zoneinfo.ZoneInfo("America/Detroit"))) #Refresh Menu at 7 am
    async def pullMenuTask(self):
        await chartwells_queryFast.main()
        
    @tasks.loop(time=datetime.time(hour=9, minute=0, tzinfo=zoneinfo.ZoneInfo("America/Detroit")))
    async def daily_poll_task(self):
        channel = self.bot.get_channel(self.food_channel)
        # print dinner options
        await self.dinnerOptions(channel,"Dinner")

        # Run the poll
        await self.run_dinner_poll(channel)
    # end region
async def setup(bot: commands.Bot):
    await bot.add_cog(foodCog(bot))