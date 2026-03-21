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

from discord import HeadersContext


@pytest.mark.asyncio
async def test_build_number():
    async with aiohttp.ClientSession() as session:
        assert await HeadersContext.scrape_client_build_number(session) is not None


@pytest.mark.asyncio
async def test_browser_version():
    async with aiohttp.ClientSession() as session:
        assert await HeadersContext.fetch_chrome_version(session) is not None


@pytest.mark.asyncio
async def test_utilities():
    chromium_version = 135
    hdrs = HeadersContext(
        platform='Windows', browser_major_version=chromium_version, browser_type='edge', super_properties={}, encoded_super_properties=''
    )
    client_hints = hdrs.client_hints

    assert (
        hdrs.format_chromium_user_agent(chromium_version, 'Windows', 'Edg')
        == f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chromium_version}.0.0.0 Safari/537.36 Edg/{chromium_version}.0.0.0'
    )
    assert (
        client_hints['Sec-CH-UA'] == f'"Microsoft Edge";v="{chromium_version}", "Not-A.Brand";v="8", "Chromium";v="{chromium_version}"'
    )
    assert client_hints['Sec-CH-UA-Mobile'] == '?0'
    assert client_hints['Sec-CH-UA-Platform'] == f'"{hdrs.platform}"'
