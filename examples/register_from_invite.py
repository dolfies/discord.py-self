import asyncio
import logging

from loguru import logger as log
from twocaptcha import TwoCaptcha

import discord
from discord import Account

# I kind of prefer loguru and have therefore implemented its intercept handler to have it log over python default logging
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = log.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        log.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[InterceptHandler()], level=logging.DEBUG)


async def captcha_handler(captcha_service, captcha_sitekey):
    # I would recommend to use https://capmonster.cloud/en/ over 2captcha (0.60 / 1k hcaptchas)
    # and edit the hosts file according to https://zennolab.atlassian.net/wiki/spaces/APIS/pages/105349123/How+do+I+connect+CapMonster.cloud+to+a+program
    # to 65.21.216.235 2captcha.com
    config = {
        'apiKey': "API_KEY_HERE",
        'pollingInterval': 10,
        'defaultTimeout': 600
    }
    # https://github.com/2captcha/2captcha-python/ is being (actively) maintained by 2captcha.com and almost every captcha provider implements their API, it works reliably
    captcha_solver = TwoCaptcha(**config)

    func = getattr(captcha_solver, captcha_service)
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(None, func, *(captcha_sitekey, "https://discord.com"))

    try:
        result = await future
        log.debug(f"Solved {captcha_service} successfully, returning solution...")
        return result['code']  # {'captchaId': 'cap_id', 'code': 'cap_sol' }
    except Exception as e:
        log.error("[%s] -> %s", e.__class__.__name__, str(e))


class MyClient(discord.Client):
    async def on_ready(self):
        log.info(f'Logged on as {self.user}', )


async def register():

    # dont use the aiohttp.BasicAuth object, instead use the username:password@ip:port syntax for user-pw auth proxies,
    # as aiohttp will throw if there is an 'Authorization' key inside the headers combined with an auth object
    # also note https proxies are not supported by aiohttp
    proxy = "http://username:password@ip:port"

    account = Account(proxy=proxy)
    if token := await account._unclaimed_register(username='USERNAME_HERE', invite='INVITE_CODE_HERE', captcha_handler=captcha_handler):
        client = MyClient(proxy=proxy)
        # attempt to keep the session from the generated account, not sure if it works properly?
        client.http.__session = account.http.session
        # if everything worked out fine, the client will connect just fine but it will be locked and you will not see it joining the target guild
        await client.start(token)

# you are going to need multiple different proxies for testing this, as you will get 429s very quickly after 1-2 attempts
asyncio.run(register())

# now you tell me why we get the created account phone-locked instantly and if we verify it (by phone and email) manually in the browser it gets disabled straight away x)
# for phone numbers: https://sms-activate.ru/en/ and emails: https://buyaccs.com/
