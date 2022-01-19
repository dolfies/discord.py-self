Discord.py-self
==========

.. image:: https://img.shields.io/pypi/v/discord.py-self.svg
   :target: https://pypi.python.org/pypi/discord.py-self
   :alt: PyPI version info
.. image:: https://img.shields.io/pypi/pyversions/discord.py-self.svg
   :target: https://pypi.python.org/pypi/discord.py-self
   :alt: PyPI supported Python versions

A Modern, Feature-Rich Wrapper meant for Discord Selfbots.

Key Features
-------------

- Fully Asynchronous, using Modern Pythonic structures like `async` and `await`.
- Support for logging.
- Proper rate limit handling.
- Optimised in both speed and memory.

Installing
----------

**Python 3.8 or higher is required**

To install the library without full voice support, you can just run the following command:

.. code:: sh

    # Linux/macOS
    python3 -m pip install -U discord.py-self

    # Windows
    py -3 -m pip install -U discord.py-self


To install the development version, do the following:

.. code:: sh

    $ pip install git+https://github.com/dolfies/discord.py-self@rebase


Quick Example
--------------
Note: Intents are not used, nor are they needed in this library. Also, Discord.py-self uses the same namespace as Discord, using a - `virtual environment <examples/venv.md>`_ for selfbotting is recommended.

.. code:: py

    import discord

    class MyClient(discord.Client):
        async def on_ready(self):
            print('Logged on as', self.user)

        async def on_message(self, message):
            # don't respond to ourselves
            if message.author == self.user:
                return

            if message.content == 'ping':
                await message.channel.send('pong')

    client = MyClient()
    client.run('token')

Bot Example
~~~~~~~~~~~~~

.. code:: py

    import discord
    from discord.ext import commands

    bot = commands.Bot(command_prefix='>')

    @bot.command()
    async def ping(ctx):
        await ctx.send('pong')

    bot.run('token')

You can find more examples in the examples directory.

Links
------

- `Documentation and Changes <https://dolfies.github.io/discord.py-self/>`_
