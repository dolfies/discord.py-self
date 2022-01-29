Creating Virtual Environments in Python
----------------------
Before I tell you how to do this, let me explain why it's useful. Virtual Environments are mainly used when you want to use different versions of packages in different projects, or when you want to use different packages with the same names in different projects without them overwriting each other. A prime example of this is Discord.py-self and Discord.py, when you install Discord.py, you can simply do `import discord`, similarly, when you import Discord.py-self, you can also do `import discord`. This confuses Python, instead, it'll import whichever one you've downloaded most recently, which is not ideal for running Normal bots and Selfbots on the same machine, instead, we use Virtual Environments to seperate packages from polluting each other.

## How to make a Virtual Environment
`python -m venv /dir`
`/dir` is essentially the name of your Virtual environment, along with the folder name.

Once you run this command, you should see a file called `dir`. To enable to the Virtual Environment, do `source dir/bin/activate`, replacing `dir` with the name of your Virtual Environment.

Now, you're in your virtual environment, you can install packages like you normally would, create a requirements.txt for your project, and the feature we want, seperating packages with the same name.

Run `python -m pip install discord.py-self`, and then run your code (`python main.py`).

To exit a virtual environment, type `deactivate` in the terminal. A virtual environment is just a clean python environment with no packages installed.
