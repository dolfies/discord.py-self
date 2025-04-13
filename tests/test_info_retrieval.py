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
import pytest

from discord import utils


@pytest.mark.asyncio
async def test_build_number():
    async with aiohttp.ClientSession() as session:
        assert await utils.Headers._get_build_number(session) is not None


@pytest.mark.asyncio
async def test_browser_version():
    async with aiohttp.ClientSession() as session:
        assert await utils.Headers._get_browser_version(session) is not None


@pytest.mark.asyncio
async def test_utilities():
    chromium_version = 135
    hdrs = utils.Headers(platform='Windows',
        major_version=chromium_version,
        super_properties={},
        encoded_super_properties=''
    )
    client_hints = hdrs.client_hints

    assert hdrs._get_user_agent(chromium_version, 'Edg') == f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0'
    assert client_hints['Sec-CH-UA'] == '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"'  # no brand name here
    assert client_hints['Sec-CH-UA-Mobile'] == '?0'
    assert client_hints['Sec-CH-UA-Platform'] == '"Windows"'
