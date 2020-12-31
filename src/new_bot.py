import os
import discord
from datetime import datetime, timedelta
import threading
from asyncio import sleep

bot_client = discord.Client()
users_list_lock = threading.Lock()
playing_list_lock = threading.Lock()
returning_users = set()

"""
TODO list (as of 2020-10-10):
* Update API to 1.5.0
* Debug weird behavior when someone joins another channel on 1.5.0
* Implement logic when someone joins another channel (Right now it's just a message)
* Personalised DM per guild?
"""
"""
TODO Bugfixes on 1.1.0 (2020-10-16):
* Bot now checks latest sent DM
    in order to not khamis someone twice, since heroku resets it's dynos.
* This does mean that someone will not get belkhamised per guild,
    as the dms have no difference.
"""
    
def hala_bel_khamis(date=datetime.utcnow()):
    return date.weekday() in [3, 4, 5]  # If today is thu, fri or sat (0 is mon, 6 is sun)

def key(user):
    return hash(str(user) + str(user.guild) + str(datetime.utcnow().isocalendar()[:-1]))

async def dm_sent_this_weekend(user):
    print('... Checking if I sent {0} a message this weekend...'.format(user))
    start_of_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    print('..... Start of week is {0} .....'.format(start_of_week))

    if user.dm_channel is None:
        await user.create_dm()

    async for message in user.dm_channel.history(after=start_of_week, oldest_first=False):
        print('...Found a message sent this week! it was sent at {0} and says {1}...'.format(message.created_at, message.content))
        if message.author == bot_client.user and hala_bel_khamis(message.created_at):
            print('[!] I did send {0} a message this weekend...'.format(user))
            return True
    print('[+] I didn\'t send {0} a message this weekend...'.format(user))
    return False

async def have_a_nice_weekend(member):
    message = '{0}, Have a nice weekend! <3'.format(member.mention)
    await member.send(message)
    print('[+] Sent {0} to {1}'.format(message, member))
    return

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
        print('[+] Successfully disconnected from {0}\{1}'.format(voice_client.guild, voice_client.channel))

async def connect_and_play(channel, member):
    global bot_client
    
    try:
        print('... Trying to play for {0} at {1}\{2}'.format(member, channel.guild, channel))
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
            # while channel.guild.me is not None:
            #     await sleep(3)
            # await connect_and_play(channel, member)
            
    finally:
        # Check to prevent double messages to user from two threads 
        with users_list_lock:
            if key(member) not in returning_users:
                await have_a_nice_weekend(member)
                returning_users.add(key(member))
        print('... Left Connect&Play logic for {0}'.format(member))

@bot_client.event
async def on_ready():
    print(f'{bot_client.user} has connected to Discord!')

@bot_client.event
async def on_message(message):
    if type(message.channel) is discord.DMChannel:
        if message.author is not bot_client.user:
            print('[+] Recieved a DM from {0}:'.format(message.author))
            print('    \"{0}\"'.format(message.content))
    
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
        if not member.bot:
            if not is_deaf():
                if joined_channel() or was_deaf():
                    if key(member) not in returning_users:
                        if not await dm_sent_this_weekend(member):
                            await connect_and_play(after.channel, member)

    elif len(returning_users) != 0:
        print('[!] All in all, we had {0} users this week!'.format(len(returning_users)))
        print('[!] Clearing the users list...')
        with users_list_lock:
            returning_users.clear()


print(f'Discord API version: {discord.__version__}')
bot_client.run(os.environ['TOKEN'])

