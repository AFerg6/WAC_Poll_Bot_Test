import asyncio
import datetime
import time
import discord
import random
import re
import requests
import sqlite3
import subprocess

from discord.ext import commands
from config import TOKEN


intents = discord.Intents.default()
intents.members = True  # SERVER MEMBERS INTENT
intents.presences = True  # PRESENCE INTENT
intents.message_content = True

# SQL databse objects
conn = sqlite3.connect('botdata.db')
cursor = conn.cursor()

# Set channel and user ids
REQUEST_CHANNEL_ID = 1382060973355171890  # The requests channel ID
POLL_CHANNEL_ID = 1382061036244570182  # The polls channel ID
USER_ROLE_ID = 1014624946758098975  # weeb roll id
OWNER_ID = 453186114916974612  # my user id

# Poll support variables
ANIME_CACHE: dict[int, dict] = {}  # message_id -> list of anime
custom_id_counter = -1

ANIME_NIGHT_DETAILS = ["Friday", "6-9pm", "SEB 2202"]

# List of emotes for voting
ORIGINAL_EMOTES = [
    "<a:02Dance:1016745011443929181>",
    "<a:02Pat:1016745038685945857>",
    "<a:02Poggers:1016745040346886194>",
    "<:02Stab:1016745043605864480>",
    "<:02askin:1016745010064015431>",
    "<:02eating:1016745013016801411>",
    "<:02fight:1016745036521680896>",
    "<:02gasm:1016745037947740251>",
    "<:02scary:1016745041760358450>",
    "<:02shocked:1016745042897027143>",
    "<:02wtf:1016745045048696842>",
    "<:ANlifted:1016745201517203456>",
    "<a:AWAWAWA:1016745143954575410>",
    "<a:AYAYABASS:1016745148031455305>",
    "<a:AYAYABASS1:1016745149151318087>",
    "<a:AYAYAHey:1016745150669656144>",
    "<a:AYAYAJAM:1016745152087339090>",
    "<a:AYAYALewd:1016745153865719918>",
    "<:AhegaoAyaka:1016745008998653972>",
    "<:Akenoo:1016745193711607828>",
    "<:Angry:1016721036353474560>",
    "<:AnyaSmug:1016745135406587924>",
    "<a:Aqua:1016745251995656212>",
    "<a:AquadTriggered:1016745139525390456>",
    "<:Astolfoblush:1016745140980830289>",
    "<:Astolfoshrug:1016745142599831582>",
    "<a:AwooHard:1016745145481318450>",
    "<:BabyPikaCry:1016745158731116714>",
    "<:Bakunotlikethis:1016745160035545098>",
    "<a:Beg:1016762008135290961>",
    "<:Blondshrug:1016762020118397049>",
    "<:BlueCry:1016762022207160441>",
    "<:Boardaf:1016762023591301201>",
    "<:Bulbasaur:1016762031858270288>",
    "<a:Chika:1016762049243656232>",
    "<a:ChikaThumps:1016762127282884659>",
    "<:ChitoseDiva:1016762128968978493>",
    "<a:Cry:1016780217722871909>",
    "<a:Cry2:1016780221367717999>",
    "<a:Food1:1016780681667411989>",
    "<a:Gurahappy:1016801314749022289>",
    "<a:Gurarara:1016801321644474478>",
    "<a:Hey:1016801334491623454>",
    "<a:bunnygirl:1016762033603096666>",
    "<a:heyy:1016801337175978034>",
    "<a:kleeexcited:1016780669029982228>",
    "<a:chikahappy:1016762052544581763>",
    "<a:madrage:1016801409716461648>",
    "<a:beating:1016745161742631013>",
    "<a:Eating:1016780370886279318>",
    "<:Disgusting:1016762121154994186>",
    "<a:madasuka:1016801406751080529>",
    "<:eating2:1016780374724071556>",
    "<a:Dead:1016762109838753913>",
    "<a:emoji317:1016780378817712198>",
    "<a:CuteTeddy:1016762096110805103>",
    "<a:GuraGaming:1016801311242596532>",
    "<a:desk:1016780413835935875>",
    "<a:akiwink:1016745196047843449>",
    "<a:animechair:1016745198828650517>",
]

# Make poll item table
cursor.execute('''
CREATE TABLE IF NOT EXISTS poll_items (
    anime_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL UNIQUE,
    cover_url TEXT,
    message_id INTEGER,
    emote_text TEXT
);
''')

# Make emote table
cursor.execute('''
CREATE TABLE IF NOT EXISTS reaction_emotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emote_text TEXT NOT NULL UNIQUE
)
''')

# Make settings table
cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
               setting TEXT UNIQUE,
               value
)
''')

# If emote table is empty fill it with predefined list
cursor.execute("SELECT COUNT(*) FROM reaction_emotes")
count = cursor.fetchone()[0]
if count == 0:
    print("generating new emote table")
    for emote in ORIGINAL_EMOTES:
        cursor.execute("INSERT INTO reaction_emotes (emote_text) VALUES (?)",
                       (emote,)
                       )
    print("initial emotes loaded to db")

# If settings is empty fill with predefined settings
cursor.execute("SELECT COUNT(*) FROM settings")
count = cursor.fetchone()[0]
if count == 0:
    print("generating default settings")
    cursor.execute(
        "INSERT INTO settings (setting, value) VALUES (?, ?)",
        ("REQUESTS_CHANNEL_ID", REQUEST_CHANNEL_ID)
        )
    cursor.execute(
        "INSERT INTO settings (setting, value) VALUES (?, ?)",
        ("POLLS_CHANNEL_ID", POLL_CHANNEL_ID)
        )
    cursor.execute(
        "INSERT INTO settings (setting, value) VALUES (?, ?)",
        ("USER_ROLE_ID", USER_ROLE_ID)
        )
    cursor.execute(
        "INSERT INTO settings (setting, value) VALUES (?, ?)",
        ("custom_id_counter", custom_id_counter)
    )
    cursor.execute(
        "INSERT INTO settings (setting, value) VALUES (?, ?)",
        ("ANIME_NIGHT_DATE", ANIME_NIGHT_DETAILS[0])
    )
    cursor.execute(
        "INSERT INTO settings (setting, value) VALUES (?, ?)",
        ("ANIME_NIGHT_TIME", ANIME_NIGHT_DETAILS[1])
    )
    cursor.execute(
        "INSERT INTO settings (setting, value) VALUES (?, ?)",
        ("ANIME_NIGHT_ROOM", ANIME_NIGHT_DETAILS[2])
    )

else:
    cursor.execute("SELECT setting, value FROM settings")
    settings_list = dict(cursor.fetchall())
    print("fetching settings")
    REQUEST_CHANNEL_ID = int(settings_list["REQUESTS_CHANNEL_ID"])
    POLL_CHANNEL_ID = int(settings_list["POLLS_CHANNEL_ID"])
    USER_ROLE_ID = int(settings_list["USER_ROLE_ID"])
    custom_id_counter = int(settings_list["custom_id_counter"])
    ANIME_NIGHT_DETAILS = [
        settings_list["ANIME_NIGHT_DATE"],
        settings_list["ANIME_NIGHT_TIME"],
        settings_list["ANIME_NIGHT_ROOM"]
        ]


# Update table with writen data
conn.commit()


# command decorator to check if the user is the owner(me)
def is_owner():
    def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)


def not_user(user_id):
    def predicate(ctx):
        return ctx.author.id != user_id
    return commands.check(predicate)


bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    try:
        owner = await bot.fetch_user(OWNER_ID)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await owner.send(f"Bot restarted at `{now}`.")
    except Exception as e:
        print(f"Failed to send DM: {e}")


@bot.event
async def on_message(message):
    await bot.process_commands(message)


# ------- ADD ITEM TO POLL DB
async def add_poll_item(ctx, title: str, anime_id: int, cover_url: str = ""):
    try:
        cursor.execute(
            "INSERT INTO poll_items (anime_id, title, cover_url) "
            "VALUES (?, ?, ?)",
            (anime_id, title, cover_url)
        )
        conn.commit()

        if ctx:
            await ctx.send(f"Added **{title}** to the poll list.")
    except sqlite3.IntegrityError:
        if ctx:
            await ctx.send(f"**{title}** is already in the poll list.")


# ------- ADD EMOTE TO DB
def add_emote_item(emote: str):
    cursor.execute("INSERT INTO reaction_emotes (emote_text) VALUES (?)",
                   (emote,)
                   )
    conn.commit()


# ------- REMOVE EMOTE FROM DB
def remove_emote_item(emote: str):
    cursor.execute("DELETE FROM reaction_emotes WHERE emote_text = ?",
                   (emote,)
                   )
    conn.commit()


# ------- FRETRIEVE EMOTES FROM DB
def get_emote_items():
    cursor.execute("SELECT emote_text FROM reaction_emotes ORDER BY id ASC")
    emotes = [row[0] for row in cursor.fetchall()]
    return emotes


# ------- REMOVE ANIME FROM POLL DB
def remove_poll_item_from_db(anime_id: int):
    cursor.execute("SELECT title FROM poll_items WHERE anime_id = ?",
                   (anime_id,)
                   )
    result = cursor.fetchone()

    if result is None:
        return None  # No match found

    anime_name = result[0]
    cursor.execute("DELETE FROM poll_items WHERE anime_id = ?",
                   (anime_id,))
    conn.commit()
    return anime_name


# ------- POLL GENERATOR
async def create_poll_in_channel(channel: int):
    global custom_id_counter

    # Get items used in the poll
    cursor.execute("SELECT title FROM poll_items")
    poll_list = cursor.fetchall()
    titles = [row[0] for row in poll_list]

    # Grab emojis from the database
    emotes = get_emote_items()

    # Reset custom id counter
    custom_id_counter = -1
    cursor.execute("""UPDATE settings SET value = ? WHERE setting = ? """,
                   (custom_id_counter,
                    "custom_id_counter")
                   )
    conn.commit()

    # Clear local embed cache to free up space
    ANIME_CACHE.clear()

    # Create polls using the extracted anime names
    for idx, title in enumerate(titles):
        if idx < len(emotes):
            emote = emotes[idx]
            sent_message = await channel.send(f"{emote} {title}")
            await sent_message.add_reaction(emote)
            cursor.execute("""
        UPDATE poll_items
        SET emote_text = ?, message_id = ?
        WHERE title = ?
    """, (emote, sent_message.id, title))
            conn.commit()


# ---------- EMBED BUILDER ----------
def make_anime_embed(media: dict) -> discord.Embed:
    """Builds a Discord embed from a single AniList Media dict."""
    # I'm not going to even pretend I know what's happening here
    title = (
        media.get("title", {}).get("english")
        or media.get("title", {}).get("romaji")
        or media.get("title", {}).get("native")
        or "Unknown Title"
    )

    embed = discord.Embed(
        title=f"**{title}**",
        color=discord.Color.blue(),
    )

    # Small cover image
    cover = media.get("coverImage", {}).get("medium")
    if cover:
        embed.set_thumbnail(url=cover)

    # Row 1
    embed.add_field(
        name="Type",
        value=media.get("format", "—"),
        inline=True
        )
    embed.add_field(
        name="Episodes",
        value=media.get("episodes", "—"),
        inline=True
        )
    embed.add_field(
        name="Status",
        value=media.get("status", "—").title(),
        inline=True
    )

    # Row 2
    season = media.get("season")
    yr = media.get("seasonYear")
    embed.add_field(
        name="Season",
        value=f"{season.title()} {yr}" if season and yr else "—", inline=True
    )
    score = media.get("averageScore")
    embed.add_field(
        name="Average Score",
        value=f"{score}%" if score else "N/A",
        inline=True
    )

    genres = media.get("genres", [])
    embed.add_field(
        name="Genres",
        value=(
            ", ".join(genres[:4])
            if genres
            else "—"
            ),
        inline=True
    )

    # Description
    description = media.get(
        "description",
        "No description available."
        ).replace("<br>", "\n")
    embed.add_field(name="Description", value=description[:1024], inline=False)

    # Links
    anilist_link = media.get("siteUrl")
    link_text = f"[AniList]({anilist_link})"
    embed.add_field(name="Links", value=link_text, inline=False)

    return embed


# ---------- ANILSIT SEARCH  ----------
def search_anime(title: str):
    # Actual witchcraft
    """
    Search AniList for <title>, return an Embed for the most-popular match(or an error string).
    If no results found, return a string prompting for a custom title.
    """  # noqa: E501
    url = "https://graphql.anilist.co"
    query = '''
query ($search: String, $sort: [MediaSort], $isAdult: Boolean) {
  Page(perPage: 5) {
    media(search: $search, type: ANIME, sort: $sort, isAdult: $isAdult) {
      id
      title {
        romaji
        english
      }
      description(asHtml: false)
      coverImage {
        large
        medium
      }
      averageScore
      genres
      format
      episodes
      status
      season
      seasonYear
      siteUrl
      externalLinks {
        site
        url
      }
    }
  }
}
'''

    variables = {"search": title, "isAdult": False}

    r = requests.post(url, json={"query": query, "variables": variables})
    if r.status_code != 200:
        return f"AniList error ({r.status_code})."

    media = r.json().get("data", {}).get("Page", {}).get("media", [])
    if not media:
        return "No matching anime found."

    return media


# ---------- ANILIST SEARCH BY ID
# Unused but left for potential future use
def search_anime_by_id(anime_id: int):
    # Witchcraft p2
    """Search AniList by ID, return a single Media dict or an error string."""
    url = "https://graphql.anilist.co"
    query = '''
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    title {
      romaji
      english
    }
    description(asHtml: false)
    coverImage {
      large
      medium
    }
    averageScore
    genres
    format
    episodes
    status
    season
    seasonYear
    siteUrl
    externalLinks {
      site
      url
    }
  }
}
'''

    variables = {"id": anime_id}

    r = requests.post(url, json={"query": query, "variables": variables})
    if r.status_code != 200:
        return f"❌ AniList error ({r.status_code})."

    media = r.json().get("data", {}).get("Media")
    if not media:
        return "No anime found for ID."

    return media


# ------ ANIME SEARCH
@bot.command(name="anime", brief="Find and anime")
async def anime(ctx, *, anime_name: str):
    """
    Searches for an anime from anilist and shows the top 5. If in the set request channel adds to the poll list. Otherwise shows anime details.
    """  # noqa: E501
    global custom_id_counter

    result = search_anime(anime_name)

    # If no result found prompt for a custom title
    if isinstance(result, str):
        await ctx.send(f"No results found for **{anime_name}**.")
        await ctx.send(
            "React with ✅ within 30 seconds to add it manually to the poll list."   # noqa: E501
            )

        confirm_msg = await ctx.send("Do you want to add it as a custom entry?")   # noqa: E501
        await confirm_msg.add_reaction("✅")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) == "✅"
                and reaction.message.id == confirm_msg.id
            )

        try:
            await bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("⏳ Timed out. Custom entry not added.")
            return

        # Add anime with custom title and new id num to db
        custom_title = anime_name.strip()
        await add_poll_item(ctx, custom_title, custom_id_counter)
        custom_id_counter -= 1
        cursor.execute(
            """UPDATE settings SET value = ? WHERE setting = ? """,
            (custom_id_counter, "custom_id_counter")
            )
        conn.commit()
        return

    # Build embed with top results
    first = result[0]
    cover_url = (
        first.get("coverImage", {}).get("medium")
        or first.get("coverImage", {}).get("large")
        )
    embed = discord.Embed(
        title=f'Top results for “{anime_name}”',
        description="React with a number to select, or ❌ to cancel.",
        color=discord.Color.blue(),
    )
    if cover_url:
        embed.set_thumbnail(url=cover_url)

    # Build the list line with numbered options, only up to 5 results
    nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    # First line: first three titles
    line1 = []
    for i, anime in enumerate(result[:3]):
        title = (
            anime["title"].get("english")
            or anime["title"].get("romaji")
            or "Unknown"
            )
        line1.append(f"{nums[i]}  {title}")
    line1_str = "     ".join(line1)  # 5 spaces for horizontal spacing

    # Second line: last two titles (if present)
    line2 = []
    for i, anime in enumerate(result[3:5], start=3):
        title = (
            anime["title"].get("english")
            or anime["title"].get("romaji")
            or "Unknown"
        )
        line2.append(f"{nums[i]}  {title}")
    line2_str = "     ".join(line2) if line2 else ""

    # Combine lines with a newline
    field_value = line1_str
    if line2_str:
        field_value += "\n" + line2_str

    embed.add_field(name="\u200b", value=field_value, inline=False)

    msg = await ctx.send(embed=embed)

    # Add reactions for selection + cancel
    for i in range(min(5, len(result))):
        await msg.add_reaction(nums[i])
    await msg.add_reaction("❌")

    # Cache the search results for reaction handling
    ANIME_CACHE[msg.id] = {
        "animes": result[:5],
        "user_id": ctx.author.id,
    }


# ----- REACTION HANDLER  (SELECTION / CANCEL) -------
@bot.event
async def on_reaction_add(reaction, user):
    # Ignore bot reactions
    if user.bot:
        return

    # Save message to cache to keep interactivity active
    payload = ANIME_CACHE.get(reaction.message.id)
    if not payload:
        return  # Reaction isn't for an anime message

    # Only command author may react
    if user.id != payload["user_id"]:
        await reaction.message.channel.send(
            f"{user.mention} only the command author can make a selection."
        )
        await reaction.remove(user)
        return

    emoji = str(reaction.emoji)
    nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    # ---------- CANCEL ----------
    if emoji == "❌":
        del ANIME_CACHE[reaction.message.id]
        await reaction.message.channel.send("Selection cancelled.")
        await reaction.message.clear_reactions()
        return

    # ---------- NUMBER PICK ----------
    if emoji not in nums:
        return  # some other emoji

    index = nums.index(emoji)
    animes = payload["animes"]
    if index >= len(animes):
        return  # should never happen

    chosen = animes[index]  # dict for the anime
    anime_id = chosen["id"]
    title_en = chosen["title"].get("english") or chosen["title"].get("romaji")

    # Doesnt add item to poll list if not in set request channel
    if reaction.message.channel.id == REQUEST_CHANNEL_ID:
        cover_url = (
            chosen.get("coverImage", {}).get("large")
            or chosen.get("coverImage", {}).get("medium")
            or None
            )
        await add_poll_item(
            reaction.message.channel,
            title_en,
            anime_id,
            cover_url
            )
        embed = make_anime_embed(chosen)
        await reaction.message.channel.send(embed=embed)
    else:
        embed = make_anime_embed(chosen)
        await reaction.message.channel.send(embed=embed)

    # Clean up
    del ANIME_CACHE[reaction.message.id]
    await reaction.message.clear_reactions()


# -------- CUSTOM ID GENERATION HANDLER -------
def next_negative_id() -> int:
    """Return the next available negative ID (-1, -2, …) not yet used."""
    cursor.execute("SELECT anime_id FROM poll_items")
    poll_list = cursor.fetchall()

    # Uses the first available custom id number
    used = {
        entry[0] for entry in poll_list
        if isinstance(entry[0], int) and entry[0] < 0
    }
    n = -1
    while n in used:
        n -= 1
    return n


# ------- PURGE CHANNEL
async def clear_channel(ctx):
    # Checks if msg is pinned
    def not_pinned(msg):
        return not msg.pinned

    deleted = 0
    # Deletes all messages not pinned
    while True:
        purged = await ctx.channel.purge(limit=100, check=not_pinned)
        deleted += len(purged)
        if len(purged) < 100:
            break

    await ctx.send(f"Cleared {deleted} messages.", delete_after=5)


# ---------- GET EMOJI ID
def extract_emoji_id(emote_str):
    # Regex to match custom emoji format and extract ID
    match = re.match(r"<a?:\w+:(\d+)>", emote_str)
    if match:
        return int(match.group(1))
    return None


# --------- VALIDATE EMOTE CAN BE USED BY THE BOT
async def validate_emote(ctx, emote: str):
    emoji_id = extract_emoji_id(emote)
    if not emoji_id:
        await ctx.send("Invalid emote format. Please use a custom Discord emoji.")  # noqa: E501
        return False

    emoji = bot.get_emoji(emoji_id)
    if emoji is None:
        await ctx.send("Emoji not found or not from a server the bot is in.")
        return False

    return True


# ---------- GET MAX ANIME ID
def get_max_anime_id():
    query = '''
    query ($isAdult: Boolean) {
      Page(perPage: 1) {
        media(type: ANIME, sort: ID_DESC, isAdult: $isAdult) {
          id
        }
      }
    }
    '''
    url = 'https://graphql.anilist.co'
    response = requests.post(url, json={'query': query, 'variables': {"isAdult": False}})   # noqa: E501
    data = response.json()

    return data['data']['Page']['media'][0]['id']


# group for commands regarding polls
class polls_group(commands.Cog, name='Polls'):
    def __init__(self, bot):
        self.bot = bot

    # ------- MANUAL POLL GENERATION TRIGGER
    @commands.command(name="createpoll", brief="Make a poll")
    @commands.has_permissions(kick_members=True)
    async def create_poll(self, ctx):
        """Manually create a poll from the stored requests"""

        # only works in set poll channel
        if ctx.channel.id != POLL_CHANNEL_ID:
            await ctx.send("Wrong channel")
            return

        await create_poll_in_channel(ctx.channel)

    # ---------- Poll Viewer ----------
    @commands.command(name="viewpoll", brief="See poll items")
    @commands.has_permissions(kick_members=True)
    async def view_poll(self, ctx):
        """View all the titles and ids of the animes in the request list"""
        # Sends empty list msg if poll list is empty

        # Get all poll items
        cursor.execute("SELECT title, anime_id FROM poll_items ORDER BY title ASC")   # noqa: E501
        poll_list = cursor.fetchall()

        if poll_list == []:
            await ctx.send("The poll list is empty")
            return

        # Prints all items in poll sorted alphabetically
        for title, anime_id in poll_list:
            await ctx.send(f"{title} ({anime_id})")
        await ctx.send("End of poll")

    # ------- CLOSES POLL CHANNEL AND POSTS RESULTS
    @commands.command(name="closepoll", brief="End the current poll")
    @commands.has_permissions(kick_members=True)
    async def close_poll(self, ctx):
        """Hides the poll channel from general user role, tally up votes and display the winners"""  # noqa: E501
        role = ctx.guild.get_role(USER_ROLE_ID)
        request_channel = ctx.guild.get_channel(REQUEST_CHANNEL_ID)
        poll_channel = ctx.guild.get_channel(POLL_CHANNEL_ID)

        await ctx.send("Closing polls...")

        # Get all poll items
        cursor.execute(
            "SELECT title, cover_url, message_id, emote_text FROM poll_items"
        )
        poll_list = cursor.fetchall()

        # Tries to hide both channels
        try:
            await request_channel.set_permissions(role, view_channel=False)
            await poll_channel.set_permissions(role, view_channel=False)
        except discord.Forbidden:
            await ctx.send("I don't have permission to change channel permissions.")  # noqa: E501
        except Exception as e:
            await ctx.send(f"Failed to set channel permissions: {e}")

        # Dummy winners for easy initial comparison
        first = [["dummy", 0, ""]]
        second = [["dummy2", 0, ""]]

        # channel = ctx.channel

        # Iterates through all items in poll_messages
        for title, cover_url, message_id, emote in poll_list:
            try:
                message = await poll_channel.fetch_message(message_id)
            except discord.NotFound:
                continue  # Skip if message was deleted

            # Counts number of votes on a message
            for reaction in message.reactions:
                # Checks for initially used emoji to filter fake votes
                if str(reaction.emoji) == emote:
                    count = reaction.count
                    # Removes bot "vote"
                    if reaction.me:
                        count -= 1

                    # Winner logic
                    if count > first[0][1]:
                        second = first
                        first = [[title, count, cover_url]]
                    elif count == first[0][1]:
                        first.append([title, count, cover_url])
                    elif count > second[0][1]:
                        second = [[title, count, cover_url]]
                    elif count == second[0][1]:
                        second.append([title, count, cover_url])

        # Output results
        result_msg = "**Poll Results**\n\n**Top Votes:**\n"
        for entry in first:
            if entry[0] != "dummy":
                result_msg += f"{entry[0]} ({entry[1]} votes)\n{entry[2]}\n"

        if (len(first) == 1):
            result_msg += "\n**Second Place:**\n"
            for entry in second:
                if entry[0] != "dummy2":
                    result_msg += (
                        f"{entry[0]} ({entry[1]} votes)\n"
                        f"{entry[2]}\n"
                    )

        # Announce winners
        await ctx.send(result_msg)

        # Clear poll list
        cursor.execute("DELETE FROM poll_items")
        conn.commit()

    # ------- OPENS REQUEST CHANNEL FOR REQUESTS
    @commands.command(name="openrequests", brief="Open requests for users")
    @commands.has_permissions(kick_members=True)
    async def open_requests(self, ctx, *, theme: str = ""):
        """Clears the poll and request channel, hides poll channel and shows the request channel for general users"""  # noqa: E501
        role = ctx.guild.get_role(USER_ROLE_ID)
        request_channel = ctx.guild.get_channel(REQUEST_CHANNEL_ID)
        poll_channel = ctx.guild.get_channel(POLL_CHANNEL_ID)

    # Checks for set role and request channel
        if role is None:
            await ctx.send("Role not found.")
            return
        if request_channel is None or poll_channel is None:
            await ctx.send("One or more channels not found.")
            return

        await ctx.send("Opening Requests...")

        # Purge both channels
        await request_channel.purge(limit=None)
        await poll_channel.purge(limit=None)

        # Set channel name to current theme
        channel_name = f"🎬丨「requests」{theme}"

        # Tries to change name and perms
        try:
            await request_channel.edit(name=channel_name)
        except discord.Forbidden:
            await ctx.send("I don't have permission to rename that channel.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to rename the channel: {e}")

        try:
            await request_channel.set_permissions(role, view_channel=True)
            await poll_channel.set_permissions(role, view_channel=False)
        except discord.Forbidden:
            await ctx.send("I don't have permission to change channel permissions.")  # noqa: E501
        except Exception as e:
            await ctx.send(f"Failed to set channel permissions: {e}")

        await ctx.send("Requests are now open", delete_after=5)

    # ------- OPENS POLL CHANNEL AND MAKES POLL
    @commands.command(name="openpoll", brief="Open polls for users")
    @commands.has_permissions(kick_members=True)
    async def open_poll(self, ctx):
        """Hides request channel, shows polls channel and generates a poll"""
        role = ctx.guild.get_role(USER_ROLE_ID)
        request_channel = ctx.guild.get_channel(REQUEST_CHANNEL_ID)
        poll_channel = ctx.guild.get_channel(POLL_CHANNEL_ID)

        # Check for channel and user role
        if role is None:
            await ctx.send("Role not found.")
            return
        if request_channel is None or poll_channel is None:
            await ctx.send("One or more channels not found.")
            return

        # Tries to change channel perms
        try:
            await request_channel.set_permissions(role, view_channel=False)
            await poll_channel.set_permissions(role, view_channel=True)
        except discord.Forbidden:
            await ctx.send("I don't have permission to change channel permissions.")  # noqa: E501
        except Exception as e:
            await ctx.send(f"Failed to set channel permissions: {e}")

        # Makes poll in poll channel
        await create_poll_in_channel(poll_channel)
        await ctx.send("Polls are now open!")

    # -------- REMOVE ITEM FROM POLL --------
    @commands.command(name="remove", brief="Remove poll item")
    @commands.has_permissions(kick_members=True)
    async def remove_poll_item(self, ctx, anime_id: str):
        """Remove an item from the poll db using the anime anilist id number"""
        try:
            # Convert input to int
            anime_id_int = int(anime_id)

            # Remove item and get name
            anime_name = remove_poll_item_from_db(anime_id_int)

            # Anime not in db
            if anime_name is None:
                await ctx.send("No anime with that ID is in the poll list.")
                return

            await ctx.send(f"**{anime_name}** has been removed from the poll list.")  # noqa: E501

        # ID num not given
        except ValueError:
            await ctx.send("Invalid ID. Please enter a numeric ID.")

    # ------- SET CHANNEL POLLS ARE MADE IN
    @commands.command(name="setpollchannel", brief="Change the poll channel")
    @commands.has_permissions(administrator=True)
    async def set_poll_channel(self, ctx):
        """Sets the poll channel to the channel the command is sent in and saves it to settings db"""  # noqa: E501
        global POLL_CHANNEL_ID

        POLL_CHANNEL_ID = ctx.message.channel.id
        cursor.execute("""
            UPDATE settings
            SET value = ?
            WHERE setting = ?
        """, (POLL_CHANNEL_ID, "POLLS_CHANNEL_ID"))
        conn.commit()
        await ctx.send(f"Poll channel set to <#{POLL_CHANNEL_ID}>")

    # ------- SET CHANNEL REQUESTS ARE MADE IN
    @commands.command(name="setrequestchannel", brief="Change the request channel")  # noqa: E501
    @commands.has_permissions(administrator=True)
    async def set_request_channel(self, ctx):
        """Sets the request channel to the channel the command is sent in and saves it to settings db"""  # noqa: E501
        global REQUEST_CHANNEL_ID

        REQUEST_CHANNEL_ID = ctx.message.channel.id
        cursor.execute("""
            UPDATE settings
            SET value = ?
            WHERE setting = ?
        """, (REQUEST_CHANNEL_ID, "REQUESTS_CHANNEL_ID"))
        conn.commit()
        await ctx.send(f"Request channel set to <#{REQUEST_CHANNEL_ID}>")

    # ------- SHOWS REQUEST AND POLL CHANNELS
    @commands.command(name="viewchannels", brief="View poll/request channels")
    @commands.has_permissions(kick_members=True)
    async def view_channels(self, ctx):
        """Displays the channels used for the polls and requests"""
        await ctx.send(f"Poll channel: <#{POLL_CHANNEL_ID}>\nRequest channel: <#{REQUEST_CHANNEL_ID}>")  # noqa: E501

    # ------- SETS USER PERMS FOR POLL CHANNELS
    @commands.command(name="setuserrole", brief="Change the user role")
    @commands.has_permissions(administrator=True)
    async def set_user_role(self, ctx, *, role_name: str):
        """Change the user role that gets modified for viewing the polls and adding requests"""  # noqa: E501
        global USER_ROLE_ID
        # Searches for role from given input
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role is None:
            await ctx.send(f"Role `{role_name}` not found.")
            return

        # If found store id
        USER_ROLE_ID = role.id
        await ctx.send(f"User role set to `{role.name}` with ID `{USER_ROLE_ID}`.")  # noqa: E501
        cursor.execute("""
            UPDATE settings
            SET value = ?
            WHERE setting = ?
        """, (USER_ROLE_ID, "USER_ROLE_ID"))
        conn.commit()

    # --------- AUTO POPULATE POLL LIST
    @commands.command(name="randompoll", brief="Auto populate poll list")
    @is_owner()
    async def random_poll(self, ctx, num_items: int = 5):
        """Automatically populates the poll list with random anime from AniList"""  # noqa: E501

        await ctx.send(f"Populating poll list with {num_items} random anime...")  # noqa: E501

        start_time = time.perf_counter()

        rand_ids = []

        max_id = get_max_anime_id()
        print(f"Max anime ID from AniList: {max_id}")

        for i in range(num_items):
            rand_anime_id = random.randint(1, max_id)

            print(f"Generated random ID: {rand_anime_id}")
            # Ensure unique IDs
            while rand_anime_id in rand_ids:
                rand_anime_id = random.randint(1, max_id)
                print("Found duplicate ID, generating a new one...")

            rand_ids.append(rand_anime_id)

        for anime_id in rand_ids:
            # Search for anime by ID
            rand_anime = search_anime_by_id(anime_id)
            while rand_anime is None or isinstance(rand_anime, str):
                print("No anime found, trying again...")
                # Ensure unique IDs
                while True:
                    print("Generating new ID...")
                    anime_id = random.randint(1, max_id)

                    if anime_id not in rand_ids:
                        break

                rand_anime = search_anime_by_id(anime_id)

            # If valid anime found, add to poll list
            if isinstance(rand_anime, dict):
                title = (
                    rand_anime["title"].get("english")
                    or rand_anime["title"].get("romaji")
                    or "Unknown"
                )
                print(title)
                await add_poll_item(
                    None,
                    title,
                    rand_anime["id"],
                    rand_anime.get("coverImage", {}).get("medium", "")
                )

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        await ctx.send(f"Poll list populated with {num_items} random anime in {elapsed_time:.2f} seconds.")  # noqa: E501


# groups regarding emote manipulation
class emote_group(commands.Cog, name='Emotes'):
    def __init__(self, bot):
        self.bot = bot

    # ------- VIEW EMOTE LIST
    @commands.command(name="viewemotes", brief="View emote list")
    @commands.has_permissions(kick_members=True)
    async def view_emotes(self, ctx):
        """Displays a full list of the emotes used for poll votes"""
        emotes = get_emote_items()

        # Send emotes in groups of 10 per message
        chunk_size = 10
        for i in range(0, len(emotes), chunk_size):
            chunk = emotes[i:i + chunk_size]
            await ctx.send(" ".join(chunk))

    # --------- REMOVE EMOTE FROM POLL LIST
    @commands.command(name="removeemote", brief="Remove emote from db")
    @commands.has_permissions(kick_members=True)
    async def remove_emote(self, ctx, emote: str):
        """Remove an emote from the list of emotes used for poll reactions"""

        try:
            remove_emote_item(emote)
            await ctx.send(f"Emoji {emote} removed from the database.")
        except Exception as e:
            await ctx.send(f"Emoji {emote} not found in the database.")
            print(f"Error removing emoji: {e}")

    # -------- ADD EMOTE TO POLL EMOTE LIST
    @commands.command(name="addemote", brief="Add emote to db")
    @commands.has_permissions(kick_members=True)
    async def add_emote(self, ctx, emote: str):
        """Add an emote to the list of emotes used for poll reactions"""

        # If emote valid add to db
        if await validate_emote(self, ctx, emote):
            try:
                add_emote_item(emote)
                await ctx.send(f"Emoji {emote} added to the emoji list!")
            except Exception as e:
                await ctx.send(f"Failed to add emoji: {e}")


# #updates the bot on command hopefully
@bot.command(name="updatebot", brief="Update bot from git page")
@is_owner()
async def update_bot(ctx):
    await ctx.send("Starting update...")

    # Run 'git pull'
    result = subprocess.run(["git", "pull"], capture_output=True, text=True)
    await ctx.send(f"Git pull output:\n```\n{result.stdout}\n```")

    # Check if git pull was successful
    if result.returncode != 0:
        await ctx.send(f"Git pull failed: {result.stderr}")
        return
    await ctx.send("Update successful, installing requirements...")

    # Run 'pip install -r requirements.txt'
    result_pip = subprocess.run([
        "pip",
        "install",
        "-r",
        "requirements.txt"],
        capture_output=True, text=True)
    await ctx.send(f"Pip install output:\n```\n{result_pip.stdout}\n```")

    # Restart the bot
    await ctx.send("Restarting bot now...")
    await bot.close()  # cleanly close the bot to allow restart


@bot.command(name="hi", brief="hi")
async def hi(ctx):
    await ctx.send("hi")


@bot.command(name="banuser", brief="\"ban\" a user")
@not_user(290968290711306251)
async def ban_user(ctx, user: discord.Member):
    await ctx.send(f"{user.mention} has been banned")


# Anime night group command
@bot.group(name="animenight", brief="See when anime nights are hosted")
async def anime_night(ctx):
    """Displays the details of the """
    if ctx.invoked_subcommand is None:
        date, time, room = ANIME_NIGHT_DETAILS[:3]  # :3
        await ctx.send(f"Our anime nights are hosted every {date} from {time} in {room}")  # noqa: E501


# Subgroup: set
@anime_night.group(name="set", brief="Set details of anime night")
@commands.has_permissions(kick_members=True)
async def set_anime_night_detail(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Use the subcommands: `date`, `time`, or `room`.")


# Subcommand: set date
@set_anime_night_detail.command(name="date", brief="Change anime night date")
@commands.has_permissions(kick_members=True)
async def anime_night_set_date(ctx, *, date: str):
    global ANIME_NIGHT_DETAILS
    ANIME_NIGHT_DETAILS[0] = date
    await ctx.send(f"Anime night date set to {date}")
    cursor.execute("""
            UPDATE settings
            SET value = ?
            WHERE setting = ?
        """, (ANIME_NIGHT_DETAILS[0], "ANIME_NIGHT_DATE"))
    conn.commit()


# Subcommand: set time
@set_anime_night_detail.command(name="time", brief="Change anime night time")
@commands.has_permissions(kick_members=True)
async def anime_night_set_time(ctx, *, time: str):
    global ANIME_NIGHT_DETAILS
    ANIME_NIGHT_DETAILS[1] = time
    await ctx.send(f"Anime night time set to {time}")
    cursor.execute("""
            UPDATE settings
            SET value = ?
            WHERE setting = ?
        """, (ANIME_NIGHT_DETAILS[1], "ANIME_NIGHT_TIME"))
    conn.commit()


# Subcommand: set room
@set_anime_night_detail.command(name="room", brief="Change anime night room")
@commands.has_permissions(kick_members=True)
async def anime_night_set_room(ctx, *, room: str):
    global ANIME_NIGHT_DETAILS
    ANIME_NIGHT_DETAILS[2] = room
    await ctx.send(f"Anime night room set to {room}")
    cursor.execute("""
            UPDATE settings
            SET value = ?
            WHERE setting = ?
        """, (ANIME_NIGHT_DETAILS[2], "ANIME_NIGHT_ROOM"))
    conn.commit()


@bot.command(name="viewdatabase", brief="Sends the database file")
@is_owner()
async def view_database(ctx):
    print("Sending database file...")
    try:
        await ctx.send("Here's the database file:", file=discord.File("botdata.db"))  # noqa: E501
    except Exception as e:
        print(f"Error sending database file: {e}")
        await ctx.send("Error sending database file.")


@bot.command(name="uploaddatabase", brief="Upload a new database file")
@is_owner()
async def upload_database(ctx):
    """Upload a new database file to replace the current one."""
    if not ctx.message.attachments:
        await ctx.send("Please attach a database file to upload.")
        return

    attachment = ctx.message.attachments[0]
    if not attachment.filename.endswith(".db"):
        await ctx.send("Please upload a valid .db file.")
        return

    try:
        # Download the file
        await attachment.save("botdata.db")
        await ctx.send("Database file uploaded successfully. Restarting bot...")   # noqa: E501

        # Restart the bot
        await bot.close()  # cleanly close the bot to allow restart
    except Exception as e:
        print(f"Error uploading database file: {e}")
        await ctx.send("Failed to upload the database file.")


async def main():
    await bot.add_cog(polls_group(bot))
    await bot.add_cog(emote_group(bot))
    await bot.start(TOKEN)

asyncio.run(main())
