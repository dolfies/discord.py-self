"""
The MIT License (MIT)

Copyright (c) 2021-present Dolfies

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from asyncio import sleep
from functools import partial
from inspect import getmembers
from logging import getLogger
from sys import modules
from threading import Thread, Timer

from discord.utils import Browser, cached_property, ExpiringQueue

try:
    from flask import Flask, request, render_template, jsonify
    has_flask = True
except ImportError:
    has_flask = False

class _Harvester(Flask):  # Inspired from https://github.com/NoahCardoza/CaptchaHarvester
    def __init__(self, domain='discord.com', sitekey='f5561ba9-8f1e-40ca-9b5b-a0b3f719ef34', *, host='127.0.0.1', port=5000, log=False):
        super().__init__(__name__, static_url_path='/')

        self.__domain = domain
        self.__sitekey = sitekey
        self.__host = host
        self.__port = port
        self.__server = (host, port)
        self.__tokens = ExpiringQueue(105)

        getLogger('werkzeug').disabled = not log
        modules['flask.cli'].show_server_banner = lambda *x: None

        self.add_url_rule('/', methods=['GET', 'POST'], view_func=self.forger)
        for attr, func in getmembers(self):
            if attr.startswith('api_'):
                self.add_url_rule(f'/api/{attr[4:].replace("_", "-")}', view_func=func)

    def run(self, *args, **kwargs):
        target = partial(super().run, *args, **kwargs, host=self.__host, port=self.__port, ssl_context='adhoc', use_reloader=False)
        thread = Thread(target=target, daemon=True)
        thread.start()

    @cached_property
    def tokens(self):
        return self.__tokens

    async def fetch_token(self, *, wait=True):
        return await self.__tokens.get(wait)

    # Pages

    async def forger(self):
        if request.method == 'GET':
            return render_template('hcaptcha.html', domain=self.__domain, sitekey=self.__sitekey,
                                   server=f'https://{self.__host}:{self.__port}')

        if request.method == 'POST':
            token = request.form.get('h-captcha-response')
            if token:
                await self.__tokens.put(token)
            return ('', 204)

    async def api_tokens(self):
        return jsonify(self.__tokens.to_list())

    async def api_token_count(self):
        return str(len(self.__tokens.to_list()))

    async def api_token(self):
        tokens = self.__tokens
        if tokens.empty():
            return ('Out of tokens.', 425)
        return await tokens.get()

class CaptchaHandler:
    """A class that represents a captcha handler.

    This is an abstract class. The library provides a concrete implementation
    under :class:`CaptchaSolver`.

    This class allows you to implement a protocol to solve captchas in a better
    way than the built-in library implementation.

    These classes are passed to :class:`auth.Account`.

    Attributes
    -----------
    session: :class:`aiohttp.ClientSession`
        A ClientSession to use when requesting.
    headers: :class:`dict`
        Basic headers (such as a user-agent).
    """

    async def startup(self, session, headers):
        """|coro|

        An abstract method that is called by the library at startup.

        This helps the handler by giving it a ClientSession and header
        information.

        Parameters
        -----------
        session: :class:`aiohttp.ClientSession`
            A ClientSession to use when requesting.
        headers: :class:`dict`
            Basic headers (such as a user-agent).
        """
        self.session = session
        self.headers = headers

    async def prefetch_token(self):
        """|coro|

        An abstract method that is called a bit before a captcha token is required.
        
        It's meant to signal the handler to generate a token if there isn't one
        so there isn't a delay if :meth:`fetch_token` is called.
        """
        raise NotImplementedError

    async def fetch_token(self, data):
        """|coro|

        An abstract method that is called to fetch a captcha token.

        If there is no token available, it should wait until one is
        generated before returning.

        Parameters
        ------------
        data: :class:`str`
            The raw error from Discord containing the captcha info.

        Returns
        --------
        :class:`str`
            A captcha token.
        """
        raise NotImplementedError

class CaptchaSolver(CaptchaHandler):
    """A captcha handler for Discord.

    Currently this only works with hCaptcha (as it seems to be the only one
    Discord is actively using). However, ReCaptcha can be added if need be.

    Parameters
    -----------
    browser: Union[:class:`str`, :class:`~discord.enums.BrowserEnum`]
        The browser to launch.
    domain: :class:`str`
        The base domain serving the captcha. Should always be 'discord.com'.
    sitekey: :class:`str`
        The domain's sitekey. The one for hCaptcha is 'f5561ba9-8f1e-40ca-9b5b-a0b3f719ef34'.
    host: :class:`str`
        The host for the harvester server. Passed to Flask.
    port: :class:`int`
        The port for the harvester server. Passed to Flask.

    Attributes
    -----------
    harvester: :class:`Harvester`
        The server instance of the captcha handler.
    browser: :class:`Browser`
        The browser instance of the captcha handler.
    """
    def __init__(self, browser=None, domain='discord.com', sitekey='f5561ba9-8f1e-40ca-9b5b-a0b3f719ef34',
                 *, host='127.0.0.1', port=5000, log=False):
        if not has_flask:
            raise RuntimeError("Flask library needed in order to use this handler")

        self.domain = domain
        self.sitekey = sitekey
        self.server = (host, port)
        self.log = log

        self.browser = Browser(browser)
        self.harvester = None

    async def startup(self, *args):
        self.harvester = harvester = _Harvester(self.domain, self.sitekey, host=self.server[0],
                                                port=self.server[1], log=self.log)
        harvester.run()

    @cached_property
    def tokens(self):
        """ExpiringQueue[:class:`str`]: A queue of all the current tokens."""
        return self.harvester.tokens

    def launch_browser(self, width=400, height=500, *, args=[], extensions=None):
        """Launches a browser window with the captcha harvester running.

        The captchas should automatically be solved, but on the off chance
        there's a challenge, it will wait for a user to solve it.

        Parameters
        -----------
        width: :class:`int`
            The width of the app window. Defaults to 400.
        height :class:`int`
            The height of the app window. Defaults to 500.
        args: List[:class:`str:`]
            A list of extra arguments to pass to the browser.
        extensions: :class:`str`
            Extensions to load with the browser.
        """
        browser = self.browser
        if not browser.running:
            browser.launch(self.domain, self.server, width, height, args, extensions)

    def stop_browser(self):
        """Closes the currently running browser window."""
        browser = self.browser
        if browser.running:
            browser.stop()

    async def prefetch_token(self):
        if self.tokens.empty():
            self.launch_browser()

    async def fetch_token(self, data):
        assert data.get('captcha_service') == 'hcaptcha'

        if self.tokens.empty():
            self.launch_browser()

        token = await self.harvester.fetch_token()
        self.stop_browser()

        return token
