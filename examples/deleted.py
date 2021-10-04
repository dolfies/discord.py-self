import discord

TOKEN = '' # How to obtain your token: https://discordhelp.net/discord-token

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def on_message(self, message):
        if message.author == self.user:
            if message.content.startswith('!deleteme'):
                msg = await message.channel.send('I will delete myself now...')
                await msg.delete()

                # this also works
                await message.channel.send('Goodbye in 3 seconds...', delete_after=3.0)

    async def on_message_delete(self, message):
        fmt = '{0.author} has deleted the message: {0.content}'
        await message.channel.send(fmt.format(message))

client = MyClient()
client.run(TOKEN)
