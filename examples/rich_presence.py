import discord

# Your Application ID (used for proxying external assets)
APPLICATION_ID = 123456789012345678

# Any direct image URLs (png/jpg/gif)
LARGE_IMAGE_URL = 'image url here'
SMALL_IMAGE_URL = 'image url here'


class MyClient(discord.Client):
    async def on_ready(self):
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            application_id=APPLICATION_ID,
            name='name',
            details='details',
            state='state',
            # Note: If you are constantly changing activity with the same assets,
            # upload them manually with self.proxy_external_application_assets() to avoid
            # unnecessary requests
            assets=discord.ActivityAssets(
                large_image=LARGE_IMAGE_URL,
                large_text='large_text',
                small_image=SMALL_IMAGE_URL,
                small_text='small_text',
            ),
            buttons=[
                discord.ActivityButton('Website', 'https://example.com'),
            ],
        )

        await self.change_presence(activity=activity)
        print(f'Rich presence applied as {self.user} ({self.user.id})')


client = MyClient()
client.run('token')
