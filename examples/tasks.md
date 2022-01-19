Tasks
------------------
This library contains an extension to create 'tasks', essentially, functions that are run every x amount of seconds, minutes, or hours.

## Basic Example
```python
from discord.ext import tasks
@tasks.loop(seconds=5)
async def print_hello():
    print("Hello")
print_hello.start()
```
Without using tasks.loop(), most people would do something like
```python
import time
while True:
    print("Hello")
    time.sleep(5)
```
This works, but it prevents anything else from running. If you use code like this inside your bot, your bot will not function as expected.

You can read more about async and blocking [here](blocking.md)

## Sending a message to a channel every 1 minute
```python
@tasks.loop(minutes=1)
async def send_message():
    channel = bot.get_channel(channel_id_int)
    await channel.send("Hello")
send_message.start()
```
This creates a loop that runs every minute, that sends the text 'Hello' to the aforementioned channel.

discord.ext.commands.tasks essentially just takes a function that you define, and runs it at set intervals.

Now, there's an issue with the previous example regarding sending a message, the first time the loop runs, you will get an error saying 'NoneType has no attribute send', or something similar. This happens because the bot is not ready before the task starts running, how can our task send a message to discord if it's not even connected to discord yet? (This greatly simplifies what actually happens with on_ready) To make sure the function starts *only* when the bot is ready, we must do one of the following.
```python
@tasks.loop(minutes=1)
async def send_message():
    channel = bot.get_channel(channel_id_int)
    await channel.send("Hello")

@bot.event
async def on_ready():
    send_message.start()
```
This might seem like the best solution, but while it works, it's not the most elegant, and is not recommended for larger/more official bots. Instead, consider using
```python
@tasks.loop(minutes=1)
async def send_message():
    channel = bot.get_channel(channel_id_int)
    await channel.send("Hello")

@send_message.before_loop
async def before_send_message():
    await bot.wait_until_ready()
```
This code makes your task wait until the bot is ready before starting, it is more elegant and allows for further customisation before the loop starts.

## Making the task run x amount of times before stopping
There are times where you want your function to be run, let's say five times for the sake of this example before stopping. The simplest approach would be
```python
n = 0
@tasks.loop(seconds=5)
async def send_message():
    global n
    if n == 5:
        send_message.stop()
        return
    channel = bot.get_channel(id)
    await channel.send('Hello')
    n += 1
```
This definitely works, but there's a more elegant way to it.
```python
@tasks.loop(minutes=1, count=5)
async def send_message():
    channel = bot.get_channel(id)
    await channel.send("Hello")
```
This function will return five times, with a delay of 1 minute between runs, and then will not run anymore.

## Running code before a loop starts, gets cancelled or when a loop is finished running
Before start - 
```python
@tasks.loop(minutes=1)
async def send_message():
    channel = bot.get_channel(channel_id_int)
    await channel.send("Hello")

@send_message.before_loop
async def before_send_message():
    await bot.wait_until_ready()
```
Waits until bot is ready

On Loop End (Completion) -
```python
@tasks.loop(minutes=1, count=5)
async def send_message():
    channel = bot.get_channel(id)
    await channel.send("Hello")

@send_message.after_loop
async def after_send_message():
    print('Done.')
```
This code prints `Done.` after five iterations.

On Loop Cancellation -
```python
@tasks.loop(minutes=1, count=5)
async def send_message():
    channel = bot.get_channel(id)
    await channel.send("Hello")

@send_message.after_loop
async def after_send_message():
    if send_message.is_being_cancelled():
        print('Task Cancelled.')
```
This code waits until the loop is complete, then checks if it was cancelled before running our code.

[Documentation for tasks](https://discordpy.readthedocs.io/en/stable/ext/tasks/index.html)
