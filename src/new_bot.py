import os
import discord
import time
import threading
from asyncio import TimeoutError as AsyncTimeout, sleep

client = discord.Client(fetch_offline_members=False)
users_list_lock = threading.Lock()
playing_list_lock = threading.Lock()

returning_users = set()
currently_playing_guilds = set()
currently_playing_channels = set()


async def hala_bel_khamis():  # TODO - not be in GMT
    return time.gmtime().tm_wday == (3 or 4 or 5)  # If today is thu, fri or sat (0 is mon, 6 is sun)


async def currently_playing(guild_hash, channel_hash):
    global currently_playing_channels
    global currently_playing_guilds

    if channel_hash in currently_playing_channels:
        return True

    elif guild_hash in currently_playing_guilds:
        while guild_hash in currently_playing_guilds:
            await sleep(3)  # Waits until the bot has finished in playing in the other guild channel

    with playing_list_lock:
        currently_playing_channels.add(channel_hash)
        currently_playing_guilds.add(guild_hash)
    return False


async def cleanup(channel_hash, guild_hash):
    global playing_list_lock
    global currently_playing_channels
    global currently_playing_guilds

    with playing_list_lock:
        currently_playing_guilds.remove(guild_hash)
        currently_playing_channels.remove(channel_hash)


async def have_a_nice_weekend(member):
    pass  # TODO feature/implement_nice_weekend_prints


async def play(channel, member):
    try:
        voice_client = await channel.connect()
        voice_client.play(
            source=discord.FFmpegOpusAudio(
                source='./resources/encoded.opus',
                bitrate=48
            )
                #after=lambda: have_a_nice_weekend(member)
                # TODO set after
        )

    except (AsyncTimeout, discord.opus.OpusNotLoaded) as e:
        await voice_client.disconnect(force=True)
        return  # TODO An Error happened and it makes me sad, print something

    except discord.ClientException:
        return

    finally:
        await cleanup(hash(channel), hash(channel.guild))


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')


@client.event
async def on_voice_state_update(member, before, after):
    global returning_users
    global users_list_lock

    if hala_bel_khamis():
        if not after.deaf and not after.self_deaf:
            if (before.channel is None and after.channel is not None) or (before.deaf or before.self_deaf):
                if hash(member) not in returning_users:
                    playing = await currently_playing(hash(after.channel.guild), hash(after.channel))
                    if not playing:
                        with users_list_lock:
                            returning_users.add(hash(member))
                        await play(after.channel, member)

    elif len(returning_users) != 0:
        with users_list_lock:
            returning_users.clear()


print(f'Discord API version: {discord.__version__}')
client.run(os.environ['BOT_TOKEN'])
