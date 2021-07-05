from discord import Embed
from discord.colour import Color as colors
from discord.ext import commands
import io
import textwrap
import contextlib
import traceback

from cogs import default
import utils

class Admin(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  def cleanup_code(self, content):
    """Automatically removes code blocks from the code."""
    if content.startswith("```") and content.endswith("```"):
      return "\n".join(content.split("\n")[1:-1])

    return content.strip("` \n")

  @commands.command(hidden = True)
  async def load(self, ctx, *, module):
    """Loads a module."""
    try:
      self.bot.load_extension(module)
    except commands.ExtensionError as e:
      rawIO = io.StringIO()
      traceback.print_exc(file = rawIO)
      bedem = Embed(title = "Error", color = colors.orange())
      bedem.set_footer(text = "{0}#{1} • {2}" .format(ctx.author.name, str(ctx.author.discriminator), str(utils.current_time())), icon_url = ctx.author.avatar_url)
      bedem.add_field(name = "Exception:", value = f"```python\n{e.__class__.__name__}: {e}```", inline = False)
      bedem.add_field(name = "Traceback:", value = f"```python\n{rawIO.getvalue()}```", inline = False)
      return await ctx.send(embed = bedem)
    else:
      bedem = Embed(title = "Success!", color = colors.green(), description = ":white_check_mark: Successfully loaded module.")
      bedem.set_footer(text = "{0}#{1} • {2}" .format(ctx.author.name, str(ctx.author.discriminator), str(utils.current_time())), icon_url = ctx.author.avatar_url)
      await ctx.send(embed = bedem)

  @commands.command(hidden = True)
  async def unload(self, ctx, *, module):
    """Unloads a module."""
    try:
      self.bot.unload_extension(module)
    except commands.ExtensionError as e:
      rawIO = io.StringIO()
      traceback.print_exc(file = rawIO)
      bedem = Embed(title = "Error", color = colors.orange())
      bedem.set_footer(text = "{0}#{1} • {2}" .format(ctx.author.name, str(ctx.author.discriminator), str(utils.current_time())), icon_url = ctx.author.avatar_url)
      bedem.add_field(name = "Exception:", value = f"```python\n{e.__class__.__name__}: {e}```", inline = False)
      bedem.add_field(name = "Traceback:", value = f"```python\n{rawIO.getvalue()}```", inline = False)
      return await ctx.send(embed = bedem)
    else:
      bedem = Embed(title = "Success!", color = colors.green, description = ":white_check_mark: Successfully unloaded module.")
      bedem.set_footer(text = "{0}#{1} • {2}" .format(ctx.author.name, str(ctx.author.discriminator), str(utils.current_time())), icon_url = ctx.author.avatar_url)
      await ctx.send(embed = bedem)

  @commands.group(name="reload", hidden=True, invoke_without_command=True)
  async def _reload(self, ctx, *, module):
    """Reloads a module."""
    try:
      self.bot.reload_extension(module)
    except commands.ExtensionError as e:
      rawIO = io.StringIO()
      traceback.print_exc(file = rawIO)
      bedem = Embed(title = "Error", color = colors.orange)
      bedem.set_footer(text = "{0}#{1} • {2}" .format(ctx.author.name, str(ctx.author.discriminator), str(utils.current_time())), icon_url = ctx.author.avatar_url)
      bedem.add_field(name = "Exception:", value = f"```python\n{e.__class__.__name__}: {e}```", inline = False)
      bedem.add_field(name = "Traceback:", value = f"```python\n{rawIO.getvalue()}```", inline = False)
      return await ctx.send(embed = bedem)
    else:
      bedem = Embed(title = "Success!", color = colors.green(), description = ":white_check_mark: Successfully reloaded module.")
      bedem.set_footer(text = "{0}#{1} • {2}" .format(ctx.author.name, str(ctx.author.discriminator), str(utils.current_time())), icon_url = ctx.author.avatar_url)
      await ctx.send(embed = bedem)

  @_reload.command(name="all", hidden=True)
  async def _reload_all(self, ctx):
    """Reloads all modulest."""
    try:
      for module in default:
        self.bot.reload_extension(module)
    except commands.ExtensionError as e:
      rawIO = io.StringIO()
      traceback.print_exc(file = rawIO)
      bedem = Embed(title = "Error", color = colors.orange())
      bedem.set_footer(text = "{0}#{1} • {2}" .format(ctx.author.name, str(ctx.author.discriminator), str(utils.current_time())), icon_url = ctx.author.avatar_url)
      bedem.add_field(name = "Exception:", value = f"```python\n{e.__class__.__name__}: {e}```", inline = False)
      bedem.add_field(name = "Traceback:", value = f"```python\n{rawIO.getvalue()}```", inline = False)
      return await ctx.send(embed = bedem)
    else:
      bedem = Embed(title = "Success!", color = colors.green(), description = ":white_check_mark: Successfully reloaded all module.")
      bedem.set_footer(text = "{0}#{1} • {2}" .format(ctx.author.name, str(ctx.author.discriminator), str(utils.current_time())), icon_url = ctx.author.avatar_url)
      await ctx.send(embed = bedem)

#  @commands.command(pass_context=True, hidden=True, name="eval")
  async def _eval(self, ctx, *, body: str):
    """Evaluates a code"""

    env = {
      "bot": self.bot,
      "ctx": ctx,
      "self": self
    }

    env.update(globals())

    body = self.cleanup_code(body)
    stdout = io.StringIO()
    stderr = io.StringIO()

    to_compile = f"async def func():\n{textwrap.indent(body, '  ')}"

    try:
      exec(to_compile, env)
    except Exception as e:
      traceback.print_exc(file = stderr)
      bedem = Embed(title = "Error", color = colors.orange())
      bedem.set_footer(text = "{0}#{1} • {2}" .format(ctx.author.name, str(ctx.author.discriminator), str(utils.current_time())), icon_url = ctx.author.avatar_url)
      bedem.add_field(name = "Exception:", value = f"```python\n{e.__class__.__name__}: {e}```", inline = False)
      bedem.add_field(name = "Traceback:", value = f"```python\n{stderr.getvalue()}```", inline = False)
      return await ctx.send(embed = bedem)

    func = env["func"]
    try:
      with contextlib.redirect_stdout(stdout):
        ret = await func()
    except Exception as e:
      traceback.print_exc(file = stderr)
      bedem = Embed(title = "Error", color = colors.orange())
      bedem.set_footer(text = "{0}#{1} • {2}" .format(ctx.author.name, str(ctx.author.discriminator), str(utils.current_time())), icon_url = ctx.author.avatar_url)
      bedem.add_field(name = "Exception:", value = f"```python\n{e.__class__.__name__}: {e}```", inline = False)
      bedem.add_field(name = "Traceback:", value = f"```python\n{stderr.getvalue()}```", inline = False)
      return await ctx.send(embed = bedem)
    else:
      value = stdout.getvalue()
      try:
        await ctx.message.add_reaction("\u2705")
      except:
        pass

    if not stdout.getvalue() == "\
":
      bedem = Embed(title = "Success!", color = colors.green())
      bedem.set_footer(text = "{0}#{1} • {2}" .format(ctx.author.name, str(ctx.author.discriminator), str(utils.current_time())), icon_url = ctx.author.avatar_url)
      bedem.add_field(name = "Output:", value = f"```\n{stdout.getvalue()}```")
      await ctx.send(embed = bedem)

def setup(bot):
  bot.add_cog(Admin(bot))
