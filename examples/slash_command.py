"""Slash command exemple using bot extension."""
import asyncio

import discord
from discord.ext import commands

# Define the bot instance.
bot = commands.Bot(command_prefix="!", self_bot=True)

@bot.event
async def on_ready():
    # Log when the bot is ready.
    print(f"Logged in as @{bot.user.name}({bot.user.id})!")

@bot.command()
async def bump(ctx: commands.Context):
    # For this exemple, we are going to  bump a server three times.

    # Get the SlashCommand object with the command name and the
    # application_id, optional, but recommended to avoid commands confusions.
    command = [_ for _ in await ctx.channel.application_commands() if _.name == 'bump' and _.application_id == 1111111111111111][0]

    for i in range(3):
        # Invoke the slash command.
        await command.__call__(channel=ctx.channel)
        # Log the bump
        print(f"Bumped {ctx.guild.name}({ctx.guild.id}) for the {i + 1} time into {ctx.channel.name}({ctx.channel.id}).")
        # Wait before bumping again
        await asyncio.sleep(7200)

    print("Done !")

bot.run("YOUR_TOKEN")