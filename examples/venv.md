Creating Virtual Environments in Python
----------------------
Before I tell you how to do this, let me explain why it's useful. Virtual Environments are mainly used when you want to use different versions of packages in different projects, or when you want to use different packages with the same names in different projects without them overwriting each other. A prime example of this is Discord.py-self and Discord.py, when you install Discord.py, you can simply do `import discord`, similarly, when you import Discord.py-self, you can also do `import discord`. This confuses Python, instead, it'll import whichever one you've downloaded most recently, which is not ideal for running Normal bots and Selfbots on the same machine, instead, we use Virtual Environments to seperate packages from polluting each other.

## How to make a Virtual Environment
