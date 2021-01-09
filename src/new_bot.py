import os
import discord
from datetime import datetime, timedelta
import threading
import logging
import sys
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
"""
Changelist 1.2.0 (2020-12-31):
* Added logging to debug people not getting hamised on thursday morning
* New feature: Seasonal greetings!
"""
BELKHAMIS_DAYS = [3, 4, 5]  # If today is thu, fri or sat (0 is mon, 6 is sun)


def hala_bel_khamis(date=datetime.utcnow()):
    return date.weekday() in BELKHAMIS_DAYS


def key(user):
    return hash(str(user) + str(user.guild) + str(datetime.utcnow().isocalendar()[:-1]))


async def dm_sent_this_weekend(user):
    logging.debug("Checking if I sent {0} a message this weekend".format(user))
    start_of_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    logging.debug("Start of week is {0}".format(start_of_week))

    if user.dm_channel is None:
        await user.create_dm()

    async for message in user.dm_channel.history(
        after=start_of_week, oldest_first=False
    ):
        logging.debug(
            "Found a message sent this week! it was sent at {0} and says {1}".format(
                message.created_at, message.content
            )
        )
        if message.author == bot_client.user and hala_bel_khamis(message.created_at):
            logging.info("I did send {0} a message this weekend".format(user))
            return True
    logging.info("{0} did not get a message this weekend!".format(user))
    return False


async def have_a_nice_weekend(member):
    message = "{0}, Have a nice weekend! <3".format(member.mention)
    return message


def _is_a_between_b_c(a, b, c):
    return b < a < c or c < a < b


def get_seasonal_messages():
    messages = []
    now = datetime.utcnow()
    next_belkhamis_week = now + timedelta(days=7 - now.weekday() + BELKHAMIS_DAYS[0])
    this_belkhamis_week = next_belkhamis_week - timedelta(days=7)

    # Case 1: Happy new year!
    new_years_eve = datetime(year=now.year + 1, month=1, day=1)
    if _is_a_between_b_c(new_years_eve, this_belkhamis_week, next_belkhamis_week):
        messages.append("And a happy new year 🥳")

    # Case 2: Christmas
    christmas = datetime(year=now.year, month=12, day=25)
    if _is_a_between_b_c(christmas, this_belkhamis_week, next_belkhamis_week):
        messages.append("And a merry christmas! 🎄❄️")

    # Case 3: Summer break
    summer_break_start = datetime(year=now.year, month=7, day=1)
    if _is_a_between_b_c(summer_break_start, this_belkhamis_week, next_belkhamis_week):
        messages.append("And enjoy this summer break!!")

    # Case 4: John birthday
    john_bday = datetime(year=now.year, month=7, day=19)
    if _is_a_between_b_c(john_bday, this_belkhamis_week, next_belkhamis_week):
        messages.append("And happy birthday Blocky!")

    # Case 5: My birthday
    matt_bday = datetime(year=now.year, month=10, day=6)
    if _is_a_between_b_c(matt_bday, this_belkhamis_week, next_belkhamis_week):
        messages.append("And happy birthday Matt!")

    return messages


async def send_message(member, message):
    await member.send(message)
    logging.critical("Sent {0} to {1}".format(message, member))
    return


async def play(voice_client):
    try:
        voice_client.play(
            source=discord.FFmpegOpusAudio(
                source="./resources/encoded.opus", bitrate=48
            ),
        )
        logging.debug(
            "Started playing at {0}\\{1}...".format(
                voice_client.guild, voice_client.channel
            )
        )
        while voice_client.is_playing():
            await sleep(3)
        logging.debug(
            "Finished playing at {0}\\{1}".format(
                voice_client.guild, voice_client.channel
            )
        )

    finally:
        await voice_client.disconnect(force=True)
        logging.debug(
            "Successfully disconnected from {0}\\{1}".format(
                voice_client.guild, voice_client.channel
            )
        )


async def connect_and_play(channel, member):
    global bot_client
    should_send_message = False
    try:
        logging.info(
            "Trying to play for {0} at {1}\\{2}".format(member, channel.guild, channel)
        )
        voice_client = await channel.connect()
        await play(voice_client)
        should_send_message = True

    except discord.errors.ClientException:
        # We either can't connect because we are already playing on this channel or on this guild

        if bot_client.user in channel.members:
            logging.error(
                "I'm already playing in the channel where {0} is - sending messages after song".format(
                    member
                )
            )

            while bot_client.user in channel.members:
                await sleep(3)
            logging.debug("Seems like I finished playing where {0} is".format(member))
            if member in channel.members:
                logging.debug(
                    "{0} is still in {1} after I finished playing :)".format(
                        member, channel
                    )
                )
                should_send_message = True

        else:
            logging.error(
                "I'm already playing in the guild where {0} is - moving to {1} after song".format(
                    member, channel
                )
            )
            while channel.guild.me.voice is not None:
                await sleep(3)
            logging.debug("Seems like I finished playing in the other channel")
            if member in channel.members:
                logging.info("{0} is still connected, Belkhamising".format(member))
                await connect_and_play(channel, member)

    finally:
        # Check to prevent double messages to user from two threads
        if should_send_message:
            logging.debug("I should send {0} messages".format(member))
            if not await dm_sent_this_weekend(member):
                messages = [await have_a_nice_weekend(member)]
                messages += get_seasonal_messages()
                logging.debug("Messages for {0} are: {1}".format(member, messages))
                for message in messages:
                    await send_message(member, message)
                    await sleep(2)
        logging.debug("Left Connect&Play logic for {0}".format(member))


@bot_client.event
async def on_ready():
    logging.critical(f"{bot_client.user} has connected to Discord!")


@bot_client.event
async def on_message(message):
    if type(message.channel) is discord.DMChannel:
        if message.author is not bot_client.user:
            logging.critical("Received a DM from {0}:".format(message.author))
            logging.info('    "{0}"'.format(message.content))


@bot_client.event
async def on_voice_state_update(member, before, after):
    global bot_client

    def is_deaf():
        return after.deaf or after.self_deaf

    def was_deaf():
        return before.deaf or before.self_deaf

    def joined_channel():
        return before.channel is not after.channel and after.channel is not None

    if not member.bot:
        logging.warning("{0} has connected to {1}".format(member, member.guild))
        if hala_bel_khamis():
            if not is_deaf():
                if joined_channel() or was_deaf():
                    if not await dm_sent_this_weekend(member):
                        logging.warning(
                            "All checks successful for {0}, Belkhamising".format(member)
                        )
                        await connect_and_play(after.channel, member)


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.critical("Discord API version: {0}".format(discord.__version__))
bot_client.run(os.environ["TOKEN"])
