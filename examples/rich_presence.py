import selfcord

# Your Developer Portal Application ID (used for proxying external assets)
APPLICATION_ID = 123456789012345678

# Any direct image URLs (png/jpg/gif). Discord will proxy these.
LARGE_IMAGE_URL = 'image url here'
SMALL_IMAGE_URL = 'image url here'


class MyClient(selfcord.Client):
    async def on_ready(self):
        # Proxy BOTH urls in one call (Discord supports proxying up to 2 at a time).
        proxied_large, proxied_small = await self.proxy_external_application_assets(
            APPLICATION_ID,
            LARGE_IMAGE_URL,
            SMALL_IMAGE_URL,
        )

        activity = selfcord.Activity(
            type=selfcord.ActivityType.playing,
            application_id=APPLICATION_ID,
            name='name',
            details='details',
            state='state',
            assets=selfcord.ActivityAssets(
                large_image=proxied_large,
                large_text='large_text',
                small_image=proxied_small,
                small_text='small_text',
            ),
            buttons=[
                selfcord.ActivityButton('Website', 'https://example.com'),
            ],
        )

        await self.change_presence(activity=activity)
        print(f'Rich presence applied as {self.user} ({self.user.id})')


client = MyClient()
client.run('token')
