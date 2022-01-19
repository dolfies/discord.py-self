Basic Bot Example
------------------
This example tells you how to create a bot that can be used by anyone, with the prefix `!`. This bot showcases `on_ready` and `bot.command()`.

To make this a bot that only *you* (the account being botted) can use, change
```python
bot = commands.Bot(command_prefix='!')
```
to
```python
bot = commands.Bot(command_prefix='!', self_bot=True)
```


## Example
```python
from discord.ext import commands
# Importing Bot from discord.ext.commands

bot = commands.Bot(command_prefix='!')
# This variable initializes the Bot class with the prefix "!"
# Intents are not used at all in this library, *do not try using them*

@bot.event
# This is a decorator, it tells the bot to listen for an 'event', which can be anything at all that happens
async def on_ready():
    # Over here, we're waiting for a special event called 'on_ready', which is triggered when the selfbot successfully connects to Discord Servers (essentially, logging in)
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    # This would print 'Logged in as <bot username> (<bot id>)', when the bot successfully logs in

@bot.command()
# This decorator creates a command, the commands name is the same as the function name
async def ping(ctx):
    """This command sends 'Pong, {latency}ms delay.' when called.

    Args:
        ctx (context): The ctx object, containing the User who called the command, the channel it was called in, and other useful information.
    """
    await ctx.reply(f"Pong, {round(bot.latency * 1000)}ms delay.")
    # This line replies to the message with 'Pong, <latency>ms delay.', where latency is the bot's "ping" or latency to Discord Servers

token = "Your user token here"
bot.run(token)
# This line runs the bot, with the token you provided. If this line is not present, the bot will not actually connect to Discord servers, meaning that you won't be able to use it.
```
