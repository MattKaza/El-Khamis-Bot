import os
import discord
import time
import threading
from asyncio import TimeoutError as AsyncTimeout, sleep

bot_client = discord.Client(fetch_offline_members=False)
users_list_lock = threading.Lock()
playing_list_lock = threading.Lock()
returning_users = set()


def hala_bel_khamis():
    return time.gmtime().tm_wday == (3 or 4 or 5)  # If today is thu, fri or sat (0 is mon, 6 is sun)


def key(user):
    return hash(hash(user) * hash(user.guild))


async def have_a_nice_weekend(member):
    message = '{0}, Have a nice weekend! <3'.format(member.mention)
    await member.send(message)
    print('[!] Successfuly sent {0} to {1}'.format(message, member))


async def play(voice_client):
    try:
        voice_client.play(
            source=discord.FFmpegOpusAudio(
                source='./resources/encoded.opus',
                bitrate=48
            ),
        )
        print('... Started playing at {0}\{1}...'.format(voice_client.guild, voice_client.channel))
        while voice_client.is_playing():
            await sleep(3)
        print('... Finished playing at {0}\{1}...'.format(voice_client.guild, voice_client.channel))
    
    finally:
        await voice_client.disconnect(force=True)
        print('[+] Successfuly disconnected from {0}\{1}'.format(voice_client.guild, voice_client.channel))

    
async def connect_and_play(channel, member):
    global bot_client
    
    try:
        print('[+] Trying to play for {0} at {1}\{2}'.format(member, channel.guild, channel))
        voice_client = await channel.connect()
        await play(voice_client)
    
    except discord.errors.ClientException:
        # We either can't connect because we are already playing on this channel or on this guild
        
        if bot_client.user in channel.members:    
            print('[!] {0} joined {1}\{2}, where I\'m already playing'.format(member, channel.guild, channel))
            
            while bot_client.user in channel.members:
                await sleep(3)
        
        else:
            print('[!] {0} joined {1}\{2}, but I\'m probably already playing in that guild'.format(member, channel.guild, channel))
            while channel.guild.me.voice.channel is not None:
                await sleep(3)
            connect_and_play(channel, member)
            # TODO check that it works
            
    finally:
        with users_list_lock:
            if key(member) not in returning_users:
                await have_a_nice_weekend(member)
                returning_users.add(key(member))


@bot_client.event
async def on_ready():
    print(f'{bot_client.user} has connected to Discord!')


@bot_client.event
async def on_voice_state_update(member, before, after):
    global bot_client
    global returning_users
    global users_list_lock

    def is_deaf():
        return (after.deaf or after.self_deaf)

    def was_deaf():
        return (before.deaf or before.self_deaf)
    
    def joined_channel():
        return (before.channel is not after.channel and after.channel is not None)
    
    if hala_bel_khamis():
        if member != bot_client.user:
            if not is_deaf():
                if joined_channel() or was_deaf():
                    if key(member) not in returning_users:
                        await connect_and_play(after.channel, member)

    elif len(returning_users) != 0:
        with users_list_lock:
            returning_users.clear()


print(f'Discord API version: {discord.__version__}')
bot_client.run(os.environ['BOT_TOKEN'])
