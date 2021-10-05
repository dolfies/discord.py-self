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

import aiohttp
from asyncio import sleep
import json
import logging

from discord.errors import HTTPException, Forbidden, NotFound

log = logging.getLogger(__name__)

class EmailHandler:
    """A class that represents an email handler.

    This is an abstract class. The library provides a concrete implementation
    under :class:`TempMailWrapper`.

    This class allows you to implement a protocol to receive emails in a different
    way than the built-in library implementation.

    These classes are passed to :class:`auth.Account`.

    Attributes
    -----------
    session: :class:`aiohttp.ClientSession`
        A ClientSession to use when requesting.
    headers: :class:`dict`
        Basic headers (such as a user-agent).
    """

    def __init__(self):
        self.session = None
        self.headers = {}

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

    async def validate_email(self, email):
        """|coro|

        An abstract method that is called before verifying to make sure
        that this email still exists/can be used (i.e. it hasn't expired).

        Parameters
        ----------
        email: :class:`str`
            The email to check.

        Returns
        --------
        :class:`bool`
            Whether it can be used. If not, :meth:`generate_email` will be called shortly.
        """
        raise NotImplementedError

    async def generate_account(self):
        """|coro|

        An abstract method that is called to generate and return an email address.

        This is the email that the account will be verified with.
        """
        raise NotImplementedError

    async def fetch_verification_token(self, email):
        """|coro|

        An abstract method that is called after a verification email is dispatched.

        The value returned should NOT be the click.discord.com link, it should be
        the token retrieved from GETting that link (i.e. if you're redirected to
        'discord.com/verify#token=abcdefg', you should return 'abcdefg').

        This function should wait until the email is received, and raise a RuntimeError
        if it wants the library to resend the email.

        Parameters
        ----------
        email: :class:`str`
            The email to check.
        """
        raise NotImplementedError

class TempMailWrapper(EmailHandler):
    """An email handler that uses the undocumented temp-mail.io API.

    Internally caches email accounts so you can create multiple accounts
    with one handler, as well as delete the email accounts when you're done.

    Attributes
    -----------
    session: Optional[:class:`aiohttp.ClientSession`]
        A ClientSession to use when requesting.
    headers: Optional[:class:`dict`]
        Basic headers (such as a user-agent).
    emails: Optional[dict[:class:`str`, :class:`str`]]
        A dictionary of emails to tokens.
        A token is only needed for deleting the email account.
    """

    BASE = 'https://api.internal.temp-mail.io/api/v3'

    def __init__(self):
        super().__init__()
        self.emails = {}

    async def startup(self, session, headers):
        headers['Origin'] = 'https://temp-mail.io'
        headers['Referer'] = 'https://temp-mail.io/'
        headers['Sec-Fetch-Site'] = 'same-site'
        await super().startup(session, headers)

    async def request(self, method, url, **kwargs):
        base = kwargs.pop('base', self.BASE)
        url = (base + url)

        kwargs['headers'] = kwargs.get('headers', self.headers)

        for tries in range(5):
            try:
                async with self.session.request(method, url, **kwargs) as r:
                    log.debug('%s %s with %s has returned %s', method, url, kwargs.get('data'), r.status)

                    # json_or_text() depends on the headers :(
                    data = await r.text(encoding='utf-8')
                    try:
                        data = json.loads(data)
                    except:
                        pass

                    # The request was successful so just return the text/json
                    if 400 > r.status >= 200:
                        log.debug('%s %s has received %s', method, url, data)
                        return data

                    # We've received a 500 or 502, unconditional retry
                    if r.status in {500, 502}:
                        await sleep(1 + tries * 2)
                        continue

                    # The usual error cases
                    if r.status == 403:
                        raise Forbidden(r, data)
                    elif r.status == 404:
                        raise NotFound(r, data)
                    else:
                        raise HTTPException(r, data)

            # This is handling exceptions from the request
            except OSError as e:
                # Connection reset by peer
                if tries < 4 and e.errno in (54, 10054):
                    continue
                raise

        # We've run out of retries, raise
        if r.status >= 500:
            raise HTTPException(r, data)

        raise HTTPException(r, data)

    async def validate_email(self, email):
        try:
            await self.check_emails(email)
        except HTTPException as exc:
            return False
        else:
            if email in self.emails:
                return True
            return False

    async def generate_account(self):
        data = await self.request('POST', '/email/new')
        self.emails[data['email']] = data.get('token', None)
        return data['email']

    def delete_account(self, email):
        data = {
            'token': self.emails.get(email)
        }
        return self.request('DELETE', f'/email/{email}', json=data)

    def delete_email(self, email, mail_id):
        data = {
            'token': self.emails.get(email)
        }
        return self.request('DELETE', f'/message/{mail_id}', json=data)

    def check_emails(self, email):
        return self.request('GET', f'/email/{email}/messages')

    async def fetch_verification_token(self, email):
        mail = None
        for tries in range(1, 10):
            emails = await self.check_emails(email)
            for m in emails:
                if m['from'] == '"Discord" <noreply@discord.com>':
                    mail = m
            if mail:
                break
            if tries == 9:
                raise RuntimeError('Retry')
            await sleep(0.5 * tries)

        await self.delete_email(email, mail['id'])
        text = mail['body_text']
        index = text.find('Verify Email: ') + 14
        link = text[index:].rstrip('\n')

        headers = self.headers.copy()
        headers['Sec-Fetch-Dest'] = 'document'
        headers['Sec-Fetch-Mode'] = 'navigate'
        headers['Sec-Fetch-Site'] = 'none'
        headers['Sec-Fetch-User'] = '?1'
        headers['Upgrade-Insecure-Requests'] = '1'

        data = await self.request('GET', link, allow_redirects=False, headers=headers, base='')
        return data.split('"')[1].split('=')[-1]
