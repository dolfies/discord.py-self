import datetime
import selfcord


class MyClient(selfcord.Client):
    async def on_ready(self):
        # All opaque IDs used below can be found via Spotify's API or by inspecting Spotify URLs
        activity = selfcord.Spotify(
            title='Patiently Waiting',
            track_id='3ORfa5ilEthp2U0TRcv7kv',
            track_type='track',
            artists=['50 Cent', 'Eminem'],
            artist_ids=['3q7HBObVc0L8jNeTe5Gofh', '7dGJo4pcD2V6oG8kP0tJRR'],
            album="Get Rich Or Die Tryin'",
            album_id='4ycNE7y1rp5215g1kkqk1P',
            album_cover_url='https://i.scdn.co/image/ab67616d0000b273f7f74100d5cc850e01172cbf',
            duration=datetime.timedelta(milliseconds=288880),
            party_owner_id=self.user.id,
        )

        await self.change_presence(activity=activity)
        print(f'{self.user} ({self.user.id}) is listening to {activity.title} by {", ".join(activity.artists)}!')


client = MyClient()
client.run('token')
