# This example demonstrates how to use the CAPTCHA handler mechanism to show hCaptcha challenges to users using a PyQt6-based webview

import asyncio
import multiprocessing
import multiprocessing.connection
import sys
from typing import Any, Dict

# These dependencies are not automatically included with discord.py and need to be installed separately:
# pip install pyqt6 pyqt-hcaptcha qasync
import qasync
from PyQt6.QtWidgets import QApplication
from PyQtHCaptcha import HCaptchaConfig, HCaptchaWebView, HCaptchaError, HCaptchaSize

import discord
from discord.ext import commands


class WebviewProcess:
    # We must run the webview in a separate process as PyQt does not support being run in a thread, and we don't want to block the main bot process while the user is solving the CAPTCHA
    # The process will communicate the result back to the main process using a multiprocessing Pipe

    view: HCaptchaWebView
    future: asyncio.Future[str]

    def __init__(self, conn: multiprocessing.connection.Connection, config: Dict[str, Any], invisible: bool):
        self.conn = conn
        self.config_dict = config
        self.invisible = invisible

    @classmethod
    def start(cls, conn: multiprocessing.connection.Connection, config: Dict[str, Any], invisible: bool):
        app = QApplication(sys.argv)
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)

        handler = cls(conn, config, invisible)
        with loop:
            loop.run_until_complete(handler.run())

    # The hCaptcha widget emits various signals for different events

    def on_loaded(self):
        print('\nhCaptcha widget loaded successfully')

    def on_success(self, token: str):
        print('hCaptcha solved successfully')
        if not self.future.done():
            self.future.set_result(token)
        self.view.hide()

    def on_failure(self, error: HCaptchaError):
        if not self.future.done():
            self.future.set_exception(Exception(f'hCaptcha Error: {error.name}'))
        self.view.hide()

    def on_expired(self):
        print('hCaptcha token expired')

    def on_show(self):
        print('hCaptcha challenge required')
        if self.invisible:
            # Invisible captcha requested a challenge
            self.view.show()

    def on_open(self):
        print('hCaptcha challenge opened')

    def on_challenge_expired(self):
        print('hCaptcha challenge expired before completion')
        if self.invisible:
            # Invisible captchas are supposed to be automatic
            self.view.hide()
            self.view.execute()

    def on_close(self, irreversible: bool):
        if irreversible and not self.future.done():
            self.future.set_exception(asyncio.CancelledError('hCaptcha window was closed'))
            return
        print('hCaptcha challenge dismissed by user')
        if self.invisible:
            # Invisible captchas are supposed to be automatic
            self.view.hide()
            self.view.execute()

    async def run(self):
        loop = asyncio.get_running_loop()
        self.future = loop.create_future()

        try:
            cfg = HCaptchaConfig(**self.config_dict)
        except Exception as e:
            self.conn.send({'error': f'Invalid config: {e}'})
            self.conn.close()
            return

        if self.invisible:
            # Invisible captchas don't immediately show UI
            cfg.size = HCaptchaSize.invisible

        self.view = HCaptchaWebView(cfg)
        self.view.setWindowTitle('hCaptcha')

        # Connect signals to class methods
        self.view.onLoaded.connect(self.on_loaded)
        self.view.onSuccess.connect(self.on_success)
        self.view.onFailure.connect(self.on_failure)
        self.view.onExpired.connect(self.on_expired)
        self.view.onShow.connect(self.on_show)
        self.view.onOpen.connect(self.on_open)
        self.view.onChallengeExpired.connect(self.on_challenge_expired)
        self.view.onClose.connect(self.on_close)

        if not self.invisible:
            self.view.show()

        try:
            token = await self.future
            self.conn.send({'token': token})
        except Exception as e:
            self.conn.send({'error': str(e)})
        finally:
            try:
                self.view.close()
            except Exception:
                pass
            self.conn.close()


async def show_captcha(exc: discord.CaptchaRequired, client: commands.Bot) -> str:
    """Show a CAPTCHA challenge to the user and return the solved token."""
    if exc.service != 'hcaptcha':
        raise NotImplementedError(f'Unsupported captcha service: {exc.service}')

    config = {
        'sitekey': exc.sitekey,
        'rqdata': exc.rqdata,
        'url': 'https://discord.com/channels/@me',
    }

    ctx = multiprocessing.get_context('spawn')
    parent_conn, child_conn = ctx.Pipe()
    proc = ctx.Process(target=WebviewProcess.start, args=(child_conn, config, exc.should_serve_invisible), daemon=False)
    proc.start()

    try:
        while True:
            if parent_conn.poll():
                result = parent_conn.recv()
                break
            await asyncio.sleep(0.05)
    finally:
        try:
            parent_conn.close()
        except Exception:
            pass

    if not isinstance(result, dict):
        raise RuntimeError('Unexpected helper response')

    if 'token' in result:
        return result['token']
    raise RuntimeError(result.get('error', 'Unknown error from hCaptcha helper'))


# If you have a custom bot class, you can also override the ``handle_captcha()`` method to implement the same logic
bot = commands.Bot(command_prefix='?', captcha_handler=show_captcha)


@bot.command()
async def join(ctx, invite: str):
    """Join a server using an invite link."""
    # This may or may not trigger a CAPTCHA challenge based on various factors such as the server, the account, and Discord's internal risk assessment
    result = await ctx.bot.accept_invite(invite)
    await ctx.send(f'Joined server {result.guild.name!r} (ID: {result.guild.id})!')


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


if __name__ == '__main__':
    bot.run('token')
