import discord

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if not message.content.startswith('"') and message.channel.id == 1280656734196596858:
        await message.delete()

    if message.content.startswith("Ping"):
        await message.channel.send("Pong!")

with open("Token", 'r') as file:
    token = file.read()
client.run(token)
