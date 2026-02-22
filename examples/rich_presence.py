import discord

# Your Developer Portal Application ID
APPLICATION_ID = 123456789012345678

# Any direct image URLs (png/jpg/gif)
LARGE_IMAGE_URL = 'image url here'
SMALL_IMAGE_URL = 'image url here'


class MyClient(discord.Client):
    async def on_ready(self):
        # External URLs are automatically proxied through Discord's CDN
        # when passed directly to large_image/small_image.
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            application_id=APPLICATION_ID,
            name='name',
            details='details',
            state='state',
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
