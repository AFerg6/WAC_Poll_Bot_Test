import asyncio
import datetime
import time
import discord
import random
import re
import requests
import sqlite3
import subprocess
import os
import sys

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
MAX_CONCURRENT_POLL_FETCHES = 4
LIVE_WINNER_REFRESH_DELAY_SECONDS = 2.0
LIVE_WINNER_REFRESH_TASKS: dict[int, asyncio.Task] = {}


class GuildSettings:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        cursor.execute("SELECT setting, value FROM settings WHERE guild_id = ?", (self.guild_id,))  # noqa: E501
        self.settings = {setting: value for setting, value in cursor.fetchall()}  # noqa: E501

    def get(self, setting: str, default=None):
        """Get a setting value, return default if not found."""
        return self.settings.get(setting, default)

    def get_id(self, setting: str, default=None):
        """Get a setting value, return default if not found."""
        val = self.settings.get(setting, default)
        return int(val) if val is not None else default

    def set(self, setting: str, value):
        self.settings[setting] = value
        cursor.execute("""
            UPDATE settings
            SET value = ?
            WHERE guild_id = ? AND setting = ?
        """, (value, self.guild_id, setting))
        conn.commit()

    def add(self, setting: str, value):
        if setting not in self.settings:
            print("adding setting to dict")
            self.settings[setting] = value
            print(f"adding {setting} to db\n{self.guild_id, setting, value}")
            cursor.execute("""
                INSERT INTO settings (guild_id, setting, value)
                VALUES (?, ?, ?)
            """, (self.guild_id, setting, value))  # noqa: E501
            print(f"added {setting} to db\n{self.guild_id, setting, value}")
            conn.commit()

    def all_settings(self):
        return self.settings


# Cache for guild settings
guild_settings_cache: dict[int, GuildSettings] = {}


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
    guild_id INTEGER NOT NULL,
    anime_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    cover_url TEXT,
    message_id INTEGER,
    emote_text TEXT,
    PRIMARY KEY (guild_id, anime_id),
    UNIQUE (guild_id, title)
);
''')

# Make emote table
cursor.execute('''
CREATE TABLE IF NOT EXISTS reaction_emotes (
    emote_text TEXT NOT NULL UNIQUE
)
''')

# Make emote guilds table
cursor.execute('''
CREATE TABLE IF NOT EXISTS emote_guilds (
    emote_text TEXT NOT NULL,
    guild_id INTEGER NOT NULL,
    PRIMARY KEY (emote_text, guild_id),
    FOREIGN KEY (emote_text) REFERENCES reaction_emotes(emote_text)
)
''')

# Make settings table
cursor.execute('''
CREATE TABLE IF NOT EXISTS settings (
               guild_id INTEGER NOT NULL,
               setting TEXT NOT NULL,
               value TEXT NOT NULL
)
''')


# load guild objects from the database
cursor.execute("SELECT DISTINCT guild_id FROM settings")
guild_ids = [row[0] for row in cursor.fetchall()]
for guild in guild_ids:
    guild_settings_cache[guild] = GuildSettings(guild)

# Update table with writen data
conn.commit()


# Command decorator to check if the user is the owner(me)
def is_owner():
    def predicate(ctx):
        return ctx.author.id == OWNER_ID
    return commands.check(predicate)


# Command decorator to disable a command for a specific person
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
async def add_poll_item(ctx, title: str, anime_id: int, cover_url: str = "", visible: bool = False):  # noqa: E501
    try:
        cursor.execute(
            "INSERT INTO poll_items (guild_id, anime_id, title, cover_url) "
            "VALUES (?, ?, ?, ?)",
            (ctx.guild.id, anime_id, title, cover_url)
        )
        conn.commit()

        if visible:
            await ctx.send(f"Added **{title}** to the poll list.")
    except sqlite3.IntegrityError:
        if visible:
            await ctx.send(f"**{title}** is already in the poll list.")


# ------- ADD EMOTE TO DB
def add_emote_item(emote: str, guild_id: int):
    cursor.execute("INSERT OR IGNORE INTO reaction_emotes (emote_text) VALUES (?)", (emote,))  # noqa: E501
    cursor.execute("INSERT INTO emote_guilds (emote_text, guild_id) VALUES (?, ?)", (emote, guild_id))  # noqa: E501
    conn.commit()


# ------- REMOVE EMOTE FROM DB
def remove_emote_item(emote: str, guild_id: int):
    cursor.execute("DELETE FROM emote_guilds WHERE emote_text = ? AND guild_id = ?", (emote, guild_id))  # noqa: E501
    conn.commit()


# ------- RETRIEVE EMOTES FROM DB
def get_emote_items(guild_id: int):
    cursor.execute(
        "SELECT emote_text FROM emote_guilds WHERE guild_id = ? ORDER BY emote_text ASC",  # noqa: E501
        (guild_id,)
    )
    emotes = [row[0] for row in cursor.fetchall()]
    return emotes


# ------- REMOVE ANIME FROM POLL DB
def remove_poll_item_from_db(ctx, anime_id: int):
    cursor.execute("SELECT title FROM poll_items WHERE anime_id = ? AND guild_id = ?",  # noqa: E501
                   (anime_id, ctx.guild.id)
                   )
    result = cursor.fetchone()

    if result is None:
        return None  # No match found

    anime_name = result[0]
    cursor.execute("DELETE FROM poll_items WHERE anime_id = ? AND guild_id = ?",  # noqa: E501
                   (anime_id, ctx.guild.id)
                   )
    conn.commit()
    return anime_name


# ------- POLL GENERATOR
async def create_poll_in_channel(channel: discord.TextChannel):
    # Get items used in the poll
    cursor.execute("SELECT title FROM poll_items WHERE guild_id = ?", (channel.guild.id,))  # noqa: E501
    poll_list = cursor.fetchall()
    titles = [row[0] for row in poll_list]

    if len(titles) == 0:
        await channel.send("There are no items to make the poll")
        return

    # Grab emojis from the database
    emotes = get_emote_items(channel.guild.id)

    # Clear local embed cache to free up space

    # Iterate over keys to remove in a list
    keys_to_delete = [msg_id for msg_id, data in ANIME_CACHE.items() if data.get("guild_id") == channel.guild.id]  # noqa: E501

    for key in keys_to_delete:
        del ANIME_CACHE[key]

    if len(emotes) < len(titles):
        await channel.send(
            f"Warning: only {len(emotes)} emotes are configured for "
            f"{len(titles)} poll items. Extra items were skipped."
        )

    pair_count = min(len(titles), len(emotes))
    created = 0

    # Keep this sequential: sqlite cursor usage is shared and not concurrency-safe. # noqa: E501
    for idx in range(pair_count):
        title = titles[idx]
        emote = emotes[idx]

        sent_message = await channel.send(f"{emote} {title}")

        # Resolve custom emojis explicitly so add_reaction works reliably.
        reaction_target = emote
        emoji_id = extract_emoji_id(emote)
        if emoji_id:
            resolved = channel.guild.get_emoji(emoji_id) or bot.get_emoji(emoji_id)  # noqa: E501
            if resolved is not None:
                reaction_target = resolved

        try:
            await sent_message.add_reaction(reaction_target)
        except Exception as e:
            print(f"Failed to add reaction {emote} for '{title}': {e}")

        cursor.execute(
            """
            UPDATE poll_items
            SET emote_text = ?, message_id = ?
            WHERE title = ? AND guild_id = ?
            """,
            (emote, sent_message.id, title, channel.guild.id)
        )
        created += 1

    conn.commit()
    await channel.send(f"Polls are now open! ({created} items)")


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
    # global custom_id_counter
    # server_settings = guild_settings_cache.get(ctx.guild.id)
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
        await add_poll_item(ctx, custom_title, next_negative_id(ctx), "", visible=True)  # noqa: E501
        # server_settings.set("custom_id_counter", next_negative_id)  # noqa: E501
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
        "guild_id": ctx.guild.id
    }


# ----- REACTION HANDLER  (SELECTION / CANCEL) -------
@bot.event
async def on_reaction_add(reaction, user):
    guild = reaction.message.guild
    if guild is None:
        return
    server_settings = guild_settings_cache.get(guild.id)

    # Ignore bot reactions
    if user.bot:
        return

    # Save message to cache to keep interactivity active
    payload = ANIME_CACHE.get(reaction.message.id)
    if payload:
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
        if reaction.message.channel.id == server_settings.get_id("REQUESTS_CHANNEL_ID"):  # noqa: E501
            cover_url = (
                chosen.get("coverImage", {}).get("large")
                or chosen.get("coverImage", {}).get("medium")
                or None
                )
            await add_poll_item(
                reaction.message.channel,
                title_en,
                anime_id,
                cover_url,
                visible=True
                )
            embed = make_anime_embed(chosen)
            await reaction.message.channel.send(embed=embed)
        else:
            embed = make_anime_embed(chosen)
            await reaction.message.channel.send(embed=embed)

        if check_blocked_roles(user):
            await reaction.message.channel.send(
                f"{user.mention} you are blocked from using adding to the polls."
            )
            del ANIME_CACHE[reaction.message.id]
            await reaction.message.clear_reactions()
            return

        # Clean up
        del ANIME_CACHE[reaction.message.id]
        await reaction.message.clear_reactions()
        return

    # Poll vote reactions: refresh live winner text when poll items are changed.
    if server_settings is None:
        return
    if reaction.message.channel.id != server_settings.get_id("POLL_CHANNEL_ID"):
        return

    poll_row = cursor.execute(
        "SELECT 1 FROM poll_items WHERE guild_id = ? AND message_id = ?",
        (guild.id, reaction.message.id)
    ).fetchone()
    if poll_row:
        schedule_live_winner_refresh(guild)


@bot.event
async def on_reaction_remove(reaction, user):
    guild = reaction.message.guild
    if guild is None or user.bot:
        return

    server_settings = guild_settings_cache.get(guild.id)
    if server_settings is None:
        return
    if reaction.message.channel.id != server_settings.get_id("POLL_CHANNEL_ID"):
        return

    poll_row = cursor.execute(
        "SELECT 1 FROM poll_items WHERE guild_id = ? AND message_id = ?",
        (guild.id, reaction.message.id)
    ).fetchone()
    if poll_row:
        schedule_live_winner_refresh(guild)


# -------- CUSTOM ID GENERATION HANDLER -------
def next_negative_id(ctx) -> int:
    """Return the next available negative ID (-1, -2, …) not yet used."""
    cursor.execute("SELECT anime_id FROM poll_items WHERE guild_id = ?", (ctx.guild.id,))  # noqa: E501
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

    # Checks for valid format
    if not emoji_id:
        await ctx.send("Invalid emote format. Please use a custom Discord emoji.")  # noqa: E501
        return False

    # Checks if the emoji is from a server the bot is in
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


def get_poll_items(ctx):
    cursor.execute("""
    SELECT anime_id, title, cover_url, message_id, emote_text
    FROM poll_items
    WHERE guild_id = ?
    ORDER BY title ASC
""", (ctx.guild.id,))  # noqa: E501
    return cursor.fetchall()


def get_poll_items_by_guild_id(guild_id: int):
    cursor.execute("""
    SELECT anime_id, title, cover_url, message_id, emote_text
    FROM poll_items
    WHERE guild_id = ?
    ORDER BY title ASC
""", (guild_id,))
    return cursor.fetchall()


def save_server_setting(server_settings: GuildSettings, key: str, value):
    """Upsert a setting in cache + DB."""
    if key in server_settings.all_settings():
        server_settings.set(key, value)
    else:
        server_settings.add(key, value)


async def get_poll_vote_result(
    poll_channel: discord.TextChannel,
    title: str,
    cover_url: str,
    message_id: int,
    emote: str,
    fetch_limiter: asyncio.Semaphore,
):
    message = None
    async with fetch_limiter:
        for attempt in range(3):
            try:
                message = await poll_channel.fetch_message(message_id)
                break
            except discord.NotFound:
                return None
            except discord.HTTPException as e:
                if e.status == 429:
                    retry_after = getattr(e, "retry_after", 1.5)
                    try:
                        retry_after = float(retry_after)
                    except (TypeError, ValueError):
                        retry_after = 1.5
                    wait_for = min(max(retry_after, 0.5), 5.0)
                    print(
                        f"Rate limited while fetching {message_id}, "
                        f"retrying in {wait_for:.2f}s (attempt {attempt + 1}/3)"
                    )
                    await asyncio.sleep(wait_for)
                    continue
                print(f"HTTP error processing message {message_id}: {e}")
                return None
            except Exception as e:
                print(f"Error processing message {message_id}: {e}")
                return None

    if message is None:
        print(f"Skipping message {message_id}: unable to fetch after retries.")
        return None

    count = 0
    # Cache blocked users for this guild
    guild = poll_channel.guild
    blocked_roles = cursor.execute(
        "SELECT value FROM settings WHERE guild_id = ? AND setting = ?",
        (guild.id, "blocked_roles")
    ).fetchall()
    blocked_role_ids = {
        int(role_id_str) for (role_id_str,) in blocked_roles if str(role_id_str).isdigit()
    }

    def is_blocked(member):
        # Allow users with manage_messages or higher perms to bypass block
        if member.guild_permissions.manage_messages or member.guild_permissions.administrator:  # noqa: E501
            return False
        return any(role.id in blocked_role_ids for role in member.roles)

    # Find the target reaction
    target_reaction = None
    for reaction in message.reactions:
        if str(reaction.emoji) == emote:
            target_reaction = reaction
            break

    if target_reaction is not None:
        users = []
        try:
            # Fetch all users for the reaction concurrently in batches
            users = [user async for user in target_reaction.users()]
        except Exception as e:
            print(f"Error fetching users for reaction: {e}")

        # Prepare member fetches concurrently
        async def get_member_safe(user):
            if user.bot:
                return None
            member = guild.get_member(user.id)
            return (user, member)

        member_results = await asyncio.gather(*(get_member_safe(user) for user in users))  # noqa: E501
        for user, member in member_results:
            if member is None:
                continue
            if is_blocked(member):
                continue
            count += 1

    return [title, count, cover_url]


async def get_poll_winners(poll_channel: discord.TextChannel, poll_list):
    first = [["dummy", 0, ""]]
    second = [["dummy2", 0, ""]]

    fetch_limiter = asyncio.Semaphore(MAX_CONCURRENT_POLL_FETCHES)
    tasks = [
        get_poll_vote_result(
            poll_channel,
            title,
            cover_url,
            message_id,
            emote,
            fetch_limiter,
        )
        for _anime_id, title, cover_url, message_id, emote in poll_list
        if message_id is not None
    ]

    vote_results = [
        result for result in await asyncio.gather(*tasks) if result is not None
    ]

    if not vote_results:
        return first, second

    top_vote_count = max(result[1] for result in vote_results)
    first = [result for result in vote_results if result[1] == top_vote_count]

    remaining_results = [
        result for result in vote_results if result[1] < top_vote_count
    ]
    if remaining_results:
        second_vote_count = max(result[1] for result in remaining_results)
        second = [
            result for result in remaining_results if result[1] == second_vote_count  # noqa: E501
        ]

    return first, second


def build_poll_results_message(first, second, include_cover_urls: bool = True):
    result_msg = "**Poll Results**\n\n**Top Votes:**\n"
    for entry in first:
        if entry[0] != "dummy":
            result_msg += f"{entry[0]} ({entry[1]} votes)\n"
            if include_cover_urls and entry[2]:
                result_msg += f"{entry[2]}\n"

    if len(first) == 1:
        result_msg += "\n**Second Place:**\n"
        for entry in second:
            if entry[0] != "dummy2":
                result_msg += f"{entry[0]} ({entry[1]} votes)\n"
                if include_cover_urls and entry[2]:
                    result_msg += f"{entry[2]}\n"

    return result_msg


async def refresh_live_winner_message_for_guild(guild: discord.Guild):
    """Refresh the configured live-winner message for a guild, if it exists."""
    server_settings = guild_settings_cache.get(guild.id)
    if server_settings is None:
        return

    live_msg_id = server_settings.get_id("LIVE_WINNER_MESSAGE_ID", 0)
    if not live_msg_id:
        return

    poll_channel = guild.get_channel(server_settings.get_id("POLL_CHANNEL_ID"))
    if poll_channel is None:
        return

    poll_list = get_poll_items_by_guild_id(guild.id)
    first, second = await get_poll_winners(poll_channel, poll_list)
    result_msg = build_poll_results_message(first, second, include_cover_urls=False)
    result_msg += f"\nLast updated: <t:{int(time.time())}:R>"

    try:
        live_msg = await poll_channel.fetch_message(live_msg_id)
    except discord.NotFound:
        # Live winner message was deleted; disable auto-updates until recreated.
        save_server_setting(server_settings, "LIVE_WINNER_MESSAGE_ID", 0)
        return
    except Exception as e:
        print(f"Failed to fetch live winner message: {e}")
        return

    try:
        await live_msg.edit(content=result_msg)
    except Exception as e:
        print(f"Failed to update live winner message: {e}")


def schedule_live_winner_refresh(guild: discord.Guild):
    """Debounce refreshes so rapid vote events trigger one update."""
    existing_task = LIVE_WINNER_REFRESH_TASKS.get(guild.id)
    if existing_task and not existing_task.done():
        existing_task.cancel()

    async def delayed_refresh():
        try:
            await asyncio.sleep(LIVE_WINNER_REFRESH_DELAY_SECONDS)
            await refresh_live_winner_message_for_guild(guild)
        except asyncio.CancelledError:
            return
        except Exception as e:
            print(f"Live winner refresh failed for guild {guild.id}: {e}")
        finally:
            current_task = asyncio.current_task()
            if LIVE_WINNER_REFRESH_TASKS.get(guild.id) is current_task:
                LIVE_WINNER_REFRESH_TASKS.pop(guild.id, None)

    LIVE_WINNER_REFRESH_TASKS[guild.id] = asyncio.create_task(delayed_refresh())


async def disable_live_winner_for_guild(guild: discord.Guild, delete_message: bool = True):
    """Disable live winner updates and optionally delete the tracked message."""
    server_settings = guild_settings_cache.get(guild.id)
    if server_settings is None:
        return

    pending_task = LIVE_WINNER_REFRESH_TASKS.pop(guild.id, None)
    if pending_task and not pending_task.done():
        pending_task.cancel()

    live_msg_id = server_settings.get_id("LIVE_WINNER_MESSAGE_ID", 0)
    if not live_msg_id:
        return

    if delete_message:
        poll_channel = guild.get_channel(server_settings.get_id("POLL_CHANNEL_ID"))
        if poll_channel is not None:
            try:
                live_msg = await poll_channel.fetch_message(live_msg_id)
                await live_msg.delete()
            except discord.NotFound:
                pass
            except Exception as e:
                print(f"Failed to delete live winner message: {e}")

    save_server_setting(server_settings, "LIVE_WINNER_MESSAGE_ID", 0)


# group for commands regarding polls
class polls_group(commands.Cog, name='Polls'):
    def __init__(self, bot):
        self.bot = bot

    # ------- MANUAL POLL GENERATION TRIGGER
    @commands.command(name="createpoll", brief="Make a poll")
    @commands.has_permissions(kick_members=True)
    async def create_poll(self, ctx):
        """Manually create a poll from the stored requests"""
        server_settings = guild_settings_cache.get(ctx.guild.id)

        poll_channel_id = ctx.guild.get_channel(server_settings.get_id("POLL_CHANNEL_ID"))  # noqa: E501

        # only works in set poll channel
        if ctx.channel.id != poll_channel_id:
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
        poll_list = get_poll_items(ctx)
        print(f"Poll list: {poll_list}")  # Debugging line

        if poll_list == []:
            await ctx.send("The poll list is empty")
            return

        # Prints all items in poll sorted alphabetically
        for anime_id, title, *_ in poll_list:
            print(f"{title} ({anime_id})")  # Debugging line
            await ctx.send(f"{title} ({anime_id})")
        await ctx.send("End of poll")

    # ------- CLOSES POLL CHANNEL AND POSTS RESULTS
    @commands.command(name="closepoll", brief="End the current poll")
    @commands.has_permissions(kick_members=True)
    async def close_poll(self, ctx):
        """Hides the poll channel from general user role, tally up votes and display the winners"""  # noqa: E501
        server_settings = guild_settings_cache.get(ctx.guild.id)
        role = ctx.guild.get_role(server_settings.get_id("USER_ROLE_ID"))  # noqa: E501
        request_channel = ctx.guild.get_channel(server_settings.get_id("REQUESTS_CHANNEL_ID"))  # noqa: E501
        poll_channel = ctx.guild.get_channel(server_settings.get_id("POLL_CHANNEL_ID"))  # noqa: E501

        await ctx.send("Closing polls...")

        # Get all poll items
        poll_list = get_poll_items(ctx)
        print(f"Poll list: {poll_list}")  # Debugging line
        # Tries to hide both channels
        try:
            await request_channel.set_permissions(role, view_channel=False)
            await poll_channel.set_permissions(role, view_channel=False)
        except discord.Forbidden:
            await ctx.send("I don't have permission to change channel permissions.")  # noqa: E501
        except Exception as e:
            await ctx.send(f"Failed to set channel permissions: {e}")

        await ctx.send("Collecting results...")
        first, second = await get_poll_winners(poll_channel, poll_list)
        result_msg = build_poll_results_message(first, second)

        # Announce winners
        await ctx.send(result_msg)

        # Disable and clean up any active live-winner message for this poll cycle.
        await disable_live_winner_for_guild(ctx.guild, delete_message=True)

        # Clear poll list
        cursor.execute("DELETE FROM poll_items WHERE guild_id = ?", (ctx.guild.id,))  # noqa: E501
        conn.commit()

    # ------ SHOWS CURRENT WINNING POLL ITEM WITHOUT CLOSING POLL
    @commands.command(name="currentpoll", brief="Show current winning poll item")  # noqa: E501
    async def current_poll_winner(self, ctx):
        server_settings = guild_settings_cache.get(ctx.guild.id)
        poll_channel = ctx.guild.get_channel(server_settings.get_id("POLL_CHANNEL_ID"))  # noqa: E501

        if poll_channel is None:
            await ctx.send("Poll channel not found.")
            return

        poll_list = get_poll_items(ctx)
        print(f"Poll list: {poll_list}")

        await ctx.send("Collecting results...")
        first, second = await get_poll_winners(poll_channel, poll_list)
        result_msg = build_poll_results_message(
            first,
            second,
            include_cover_urls=False
        )

        await ctx.send(result_msg)

    # ------- OPENS REQUEST CHANNEL FOR REQUESTS
    @commands.command(name="openrequests", brief="Open requests for users")
    @commands.has_permissions(kick_members=True)
    async def open_requests(self, ctx, *, theme: str = ""):
        """Clears the poll and request channel, hides poll channel and shows the request channel for general users"""  # noqa: E501
        server_settings = guild_settings_cache.get(ctx.guild.id)
        role = ctx.guild.get_role(server_settings.get_id("USER_ROLE_ID"))
        request_channel = ctx.guild.get_channel(server_settings.get_id("REQUESTS_CHANNEL_ID"))  # noqa: E501
        poll_channel = ctx.guild.get_channel(server_settings.get_id("POLL_CHANNEL_ID"))  # noqa: E501

        # Checks for set role and request channel
        if role is None:
            await ctx.send("Role not found.")
            return
        if request_channel is None or poll_channel is None:
            await ctx.send("One or more channels not found.")
            return

        await ctx.send("Opening Requests...")

        # Set permissions first
        try:
            await request_channel.set_permissions(role, view_channel=True)
            await poll_channel.set_permissions(role, view_channel=False)
        except discord.Forbidden:
            await ctx.send("I don't have permission to change channel permissions.")  # noqa: E501
            return
        except Exception as e:
            await ctx.send(f"Failed to set channel permissions: {e}")
            return

        # Purge both channels after permissions are set
        await request_channel.purge(limit=None)
        await poll_channel.purge(limit=None)

        # Poll messages were wiped; clear tracked live-winner state too.
        await disable_live_winner_for_guild(ctx.guild, delete_message=False)

        # Set channel name to current theme
        channel_name = f"🎬丨「requests」{theme}"

        # Tries to change name
        try:
            await request_channel.edit(name=channel_name)
        except discord.Forbidden:
            await ctx.send("I don't have permission to rename that channel.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to rename the channel: {e}")

        await ctx.send("Requests are now open", delete_after=5)

    # ------- OPENS POLL CHANNEL AND MAKES POLL
    @commands.command(name="openpoll", brief="Open polls for users", aliases=["openpolls"])  # noqa: E501
    @commands.has_permissions(kick_members=True)
    async def open_poll(self, ctx):
        """Hides request channel, shows polls channel and generates a poll"""
        server_settings = guild_settings_cache.get(ctx.guild.id)
        role = ctx.guild.get_role(server_settings.get_id("USER_ROLE_ID"))
        request_channel = ctx.guild.get_channel(server_settings.get_id("REQUESTS_CHANNEL_ID"))  # noqa: E501
        poll_channel = ctx.guild.get_channel(server_settings.get_id("POLL_CHANNEL_ID"))  # noqa: E501

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

    # -------- REMOVE ITEM FROM POLL --------
    @commands.command(name="remove", brief="Remove poll item")
    @commands.has_permissions(kick_members=True)
    async def remove_poll_item(self, ctx, anime_id: str):
        """Remove an item from the poll db using the anime anilist id number"""
        try:
            # Convert input to int
            anime_id_int = int(anime_id)

            # Remove item and get name
            anime_name = remove_poll_item_from_db(ctx, anime_id_int)

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
        server_settings = guild_settings_cache.get(ctx.guild.id)

        server_settings.set("POLL_CHANNEL_ID", ctx.channel.id)
        await ctx.send(f"Poll channel set to <#{ctx.channel.id}>")

    # ------- SET CHANNEL REQUESTS ARE MADE IN
    @commands.command(name="setrequestchannel", brief="Change the request channel")  # noqa: E501
    @commands.has_permissions(administrator=True)
    async def set_request_channel(self, ctx):
        """Sets the request channel to the channel the command is sent in and saves it to settings db"""  # noqa: E501
        server_settings = guild_settings_cache.get(ctx.guild.id)

        server_settings.set("REQUESTS_CHANNEL_ID", ctx.channel.id)
        await ctx.send(f"Request channel set to <#{ctx.channel.id}>")

    # ------- SHOWS REQUEST AND POLL CHANNELS
    @commands.command(name="viewchannels", brief="View poll/request channels")
    @commands.has_permissions(kick_members=True)
    async def view_channels(self, ctx):
        """Displays the channels used for the polls and requests"""
        server_settings = guild_settings_cache.get(ctx.guild.id)
        role = ctx.guild.get_role(server_settings.get_id("USER_ROLE_ID"))  # noqa: E501
        await ctx.send(f"Poll channel: <#{server_settings.get_id('POLL_CHANNEL_ID')}>\nRequest channel: <#{server_settings.get_id('REQUESTS_CHANNEL_ID')}>\nUser role: {role.name if role else 'none'}")  # noqa: E501

    # ------- SETS USER PERMS FOR POLL CHANNELS
    @commands.command(name="setuserrole", brief="Change the user role")
    @commands.has_permissions(administrator=True)
    async def set_user_role(self, ctx, *, role_name: str):
        """Change the user role that gets modified for viewing the polls and adding requests"""  # noqa: E501
        server_settings = guild_settings_cache.get(ctx.guild.id)
        # Searches for role from given input
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role is None:
            await ctx.send(f"Role `{role_name}` not found.")
            return

        # If found store id
        server_settings.set("USER_ROLE_ID", role.id)
        await ctx.send(f"User role set to `{role.name}` with ID `{role.id}`.")  # noqa: E501

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
                    ctx,
                    title,
                    rand_anime["id"],
                    rand_anime.get("coverImage", {}).get("medium", "")
                )

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        await ctx.send(f"Poll list populated with {num_items} random anime in {elapsed_time:.2f} seconds.")  # noqa: E501

    @commands.command(name="livewinner", brief="Shows the live poll winners")
    @commands.has_permissions(kick_members=True)
    async def live_winner(self, ctx):
        """Creates a message that shows the current winners of the poll for a server and updates as votes come in"""  # noqa: E501
        status_message = await ctx.send("Setting up live winner message...")
        server_settings = guild_settings_cache.get(ctx.guild.id)
        poll_channel = ctx.guild.get_channel(server_settings.get_id("POLL_CHANNEL_ID"))  # noqa: E501
        if poll_channel is None:
            await status_message.edit(content="Poll channel not found.")
            return

        existing_live_id = server_settings.get_id("LIVE_WINNER_MESSAGE_ID", 0)
        if existing_live_id:
            try:
                await poll_channel.fetch_message(existing_live_id)
                await status_message.edit(content="Live winner message already exists and is active.")
                return
            except discord.NotFound:
                # Stale setting; a new live message will be created below.
                save_server_setting(server_settings, "LIVE_WINNER_MESSAGE_ID", 0)
            except Exception as e:
                await status_message.edit(content=f"Failed to fetch previous live winner message: {e}")
                return

        live_message = await poll_channel.send(
            "Preparing live poll winner results..."
        )
        save_server_setting(server_settings, "LIVE_WINNER_MESSAGE_ID", live_message.id)
        await status_message.edit(content=f"Live winner message created in <#{poll_channel.id}> and is now active.")
        schedule_live_winner_refresh(ctx.guild)
        




# groups regarding emote manipulation
class emote_group(commands.Cog, name='Emotes'):
    def __init__(self, bot):
        self.bot = bot

    # ------- VIEW EMOTE LIST
    @commands.command(name="viewemotes", brief="View emote list")
    @commands.has_permissions(kick_members=True)
    async def view_emotes(self, ctx):
        """Displays a full list of the emotes used for poll votes"""
        emotes = get_emote_items(ctx.guild.id)

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

        if not await validate_emote(ctx, emote):
            return

        try:
            remove_emote_item(emote, ctx.guild.id)
            await ctx.send(f"Emoji {emote} removed from the database.")
        except Exception as e:
            await ctx.send(f"Emoji {emote} not found in the database.")
            print(f"Error removing emoji: {e}")

    # -------- ADD EMOTE TO POLL EMOTE LIST
    @commands.command(name="addemote", brief="Add emote to db")
    @commands.has_permissions(kick_members=True)
    async def add_emote(self, ctx, emote: str):
        """Add an emote to the list of emotes used for poll reactions"""

        if not await validate_emote(ctx, emote):
            return
        try:
            add_emote_item(emote, ctx.guild.id)
            await ctx.send(f"Emoji {emote} added to the database for this server")  # noqa: E501

        # Dupe catching for server emote list
        except sqlite3.IntegrityError as e:
            print(f"Failed to insert: {e}")

    # ------ REMOVE UNAVAILABLE EMOTES FROM SERVER LIST
    @commands.command(name="cleanupemotes", brief="Remove unavailable emotes")
    @commands.has_permissions(kick_members=True)
    async def cleanup_emotes(self, ctx):
        """Removes emotes from this server's emote DB list if they no longer exist or are unavailable."""  # noqa: E501
        guild_id = ctx.guild.id
        emotes = get_emote_items(guild_id)

        if not emotes:
            await ctx.send("No emotes are configured for this server.")
            return

        removed = []
        for emote in emotes:
            emoji_id = extract_emoji_id(emote)
            if not emoji_id:
                removed.append(emote)
                continue

            emoji = self.bot.get_emoji(emoji_id) or ctx.guild.get_emoji(emoji_id)  # noqa: E501
            if emoji is None or not getattr(emoji, "available", True):
                removed.append(emote)

        if not removed:
            await ctx.send("All configured emotes are currently available.")
            return

        # Remove stale emotes from poll emote list and clear any stale references in poll items.
        for emote in removed:
            cursor.execute(
                "DELETE FROM emote_guilds WHERE emote_text = ? AND guild_id = ?",  # noqa: E501
                (emote, guild_id)
            )
            cursor.execute(
                "UPDATE poll_items SET emote_text = NULL WHERE guild_id = ? AND emote_text = ?",  # noqa: E501
                (guild_id, emote)
            )
        conn.commit()

        preview = ", ".join(removed[:10])
        suffix = "..." if len(removed) > 10 else ""
        await ctx.send(
            f"Removed {len(removed)} unavailable emote(s) from this server list:\n{preview}{suffix}"  # noqa: E501
        )


# #updates the bot on command hopefully
@bot.command(name="updatebot", brief="Update bot from git page")
@is_owner()
async def update_bot(ctx):
    async def send_output_block(label: str, text: str, max_chars: int = 1800):
        """Send command output safely without tripping Discord message limits."""  # noqa: E501
        clean = (text or "").strip()
        if not clean:
            await ctx.send(f"{label}: `(no output)`")
            return

        if len(clean) > max_chars:
            clean = clean[:max_chars] + "\n...(truncated)"
        await ctx.send(f"{label}:\n```\n{clean}\n```")

    await ctx.send("Starting update...")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    bot_script = os.path.join(current_dir, "animepoll.py")

    # Run 'git pull' in a thread to avoid blocking event loop
    result = await asyncio.to_thread(
        subprocess.run,
        ["git", "pull"],
        capture_output=True,
        text=True,
        cwd=current_dir,
    )
    await send_output_block("Git pull output", result.stdout)

    print(result.stdout)

    if(result.stdout.strip() == "Already up to date."):
        await ctx.send("Update Complete") # No updates
        return

    # Check if git pull was successful
    if result.returncode != 0:
        await ctx.send(f"Git pull failed: {result.stderr}")
        return
    requirements_changed = "requirements.txt" in (result.stdout or "")
    if requirements_changed:
        await ctx.send("Update successful, installing requirements...")

        # Run pip in non-interactive mode so it cannot block waiting for input.
        try:
            result_pip = await asyncio.to_thread(
                subprocess.run,
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    "requirements.txt",
                    "--no-input",
                    "--disable-pip-version-check",
                    "--retries",
                    "1",
                    "--timeout",
                    "30",
                ],
                capture_output=True,
                text=True,
                cwd=current_dir,
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            await ctx.send("Pip install timed out after 10 minutes. Bot was not restarted.")
            return

        pip_output = result_pip.stdout or result_pip.stderr
        await send_output_block("Pip install output", pip_output)

        if result_pip.returncode != 0:
            await send_output_block("Pip install failed", result_pip.stderr)
            return
    else:
        await ctx.send("Update successful. requirements.txt unchanged, skipping pip install.")

    # Restart by replacing the current process; more reliable than Popen + sys.exit.
    await ctx.send("Restarting bot now...")
    await asyncio.sleep(1)

    conn.commit()
    conn.close()

    try:
        os.execv(sys.executable, [sys.executable, bot_script])
    except Exception as e:
        await ctx.send(f"Failed to restart bot: {e}")
        print(f"Failed to restart bot: {e}")
        return


@bot.command(name="initializeserver", brief="Initialize the bot in a server")
@commands.has_permissions(administrator=True)
async def initialize_server(ctx):
    """Initializes the bot in a server by setting up the necessary settings"""
    global guild_settings_cache

    await ctx.send("Bot initialized with default settings.")
    guild_settings_cache[ctx.guild.id] = GuildSettings(ctx.guild.id)
    settings_list = guild_settings_cache[ctx.guild.id]

    # Setting default values
    await ctx.send("Adding default settings")
    settings_list.add("REQUESTS_CHANNEL_ID", REQUEST_CHANNEL_ID)
    settings_list.add("POLL_CHANNEL_ID", POLL_CHANNEL_ID)
    settings_list.add("USER_ROLE_ID", USER_ROLE_ID)
    settings_list.add("ANIME_NIGHT_DATE", "date")
    settings_list.add("ANIME_NIGHT_TIME", "time")
    settings_list.add("ANIME_NIGHT_ROOM", "room")
    await ctx.send("Default settings added")

    await ctx.send("Adding default emotes")
    try:
        for emote in ORIGINAL_EMOTES:
            add_emote_item(emote, ctx.guild.id)
        await ctx.send("Added default emotes")
    except Exception as e:
        await ctx.send(f"Error adding default emotes: {e}")

    await ctx.send("Server initialization complete.")
    # await ctx.send("Please configure the poll channel, request channel, and user role using the respective commands.")  # noqa: E501


@bot.command(name="hi", brief="hi")
async def hi(ctx):
    await ctx.send("hi")


@bot.group(name="banuser", brief="\"ban\" a user")
@not_user(290968290711306251)
async def ban_user(ctx, user: discord.Member):
    """Joke command to ban a user"""
    guild_settings = guild_settings_cache.get(ctx.guild.id)

    # Gets ban count from settings. if none returns zero
    ban_count = guild_settings.get_id("BAN_COUNT", 0) + 1
    if ban_count > 1:
        guild_settings.set("BAN_COUNT", ban_count)
    else:
        guild_settings.add("BAN_COUNT", ban_count)

    await ctx.send(f"{user.mention} has been banned")


@bot.command(name="bancount", brief="Get the server ban count")
async def ban_user_count(ctx):
    guild_settings = guild_settings_cache.get(ctx.guild.id)
    ban_count = guild_settings.get("BAN_COUNT", 0)
    await ctx.send(f"The server ban count is: {ban_count}")


# Anime night group command
@bot.group(name="animenight", brief="See when anime nights are hosted")
async def anime_night(ctx):
    """Displays the details of the """
    if ctx.invoked_subcommand is None:
        server_settings = guild_settings_cache.get(ctx.guild.id)
        ANIME_NIGHT_DETAILS = [
            server_settings.get("ANIME_NIGHT_DATE", "date"),
            server_settings.get("ANIME_NIGHT_TIME", "time"),
            server_settings.get("ANIME_NIGHT_ROOM", "room")
        ]
        date, time, room = ANIME_NIGHT_DETAILS
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
    server_settings = guild_settings_cache.get(ctx.guild.id)
    await ctx.send(f"Anime night date set to {date}")
    server_settings.set("ANIME_NIGHT_DATE", date)


# Subcommand: set time
@set_anime_night_detail.command(name="time", brief="Change anime night time")
@commands.has_permissions(kick_members=True)
async def anime_night_set_time(ctx, *, time: str):
    server_settings = guild_settings_cache.get(ctx.guild.id)
    await ctx.send(f"Anime night time set to {time}")
    server_settings.set("ANIME_NIGHT_TIME", time)


# Subcommand: set room
@set_anime_night_detail.command(name="room", brief="Change anime night room")
@commands.has_permissions(kick_members=True)
async def anime_night_set_room(ctx, *, room: str):
    server_settings = guild_settings_cache.get(ctx.guild.id)
    await ctx.send(f"Anime night room set to {room}")
    server_settings.set("ANIME_NIGHT_ROOM", room)


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


@bot.command(name="cleardb", brief="Deletes all DB data")
@is_owner()
async def clear_db(ctx):
    """Clears all data from the database. Used for changing database when updating"""   # noqa: E501
    try:

        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence';")   # noqa: E501
        tables = cursor.fetchall()

        for table_name in tables:
            table = table_name[0]
            # cursor.execute(f"DELETE FROM {table}")  # Clear table
            # Alternatively, to drop tables completely:
            cursor.execute(f"DROP TABLE {table}")

        conn.commit()
        conn.close()
        await ctx.send("All tables have been cleared successfully!")
    except Exception as e:
        await ctx.send(f"Error clearing database: {e}")


@bot.command(name="serversettings", brief="View server settings")
@is_owner()
async def view_server_settings(ctx):
    """View the settings for a specific server by its guild ID."""
    try:
        guild_id = ctx.guild.id  # Use the current guild ID
        server_settings = guild_settings_cache.get(guild_id)
        if not server_settings:
            await ctx.send(f"No settings found for guild ID {guild_id}.")
            return

        settings = server_settings.all_settings()
        if not settings:
            await ctx.send(f"No settings found for guild ID {guild_id}.")
            return

        settings_msg = f"**Settings for Guild ID {guild_id}:**\n"
        for key, value in settings.items():
            settings_msg += f"- {key}: {value}\n"

        await ctx.send(settings_msg)
    except Exception as e:
        print(f"Error retrieving server settings: {e}")
        await ctx.send("Error retrieving server settings.")


@bot.command(name="blockrole", brief="Block a role from voting in polls/requests")
@commands.has_permissions(administrator=True)
async def block_role(ctx, *, role_name: str):
    """Add a role to a block list that prevents users with that role from voting in polls or adding requests(server mods excluded)"""  # noqa: E501
    try:
        guild_id = ctx.guild.id
        blocked_roles = cursor.execute("SELECT * FROM settings WHERE guild_id = ? AND setting = ?", (guild_id, "blocked_roles")).fetchall()  # noqa: E501
        blocked_role_ids = {int(row[2]) for row in blocked_roles}
        # Case-insensitive role name search
        role = discord.utils.get(ctx.guild.roles, name=lambda n: n.lower() == role_name.lower())

        if role is None:
            await ctx.send(f"Role `{role_name}` not found. Please check the role name and try again.")
            return
        if int(role.id) in blocked_role_ids:
            await ctx.send(f"Role `{role_name}` is already blocked from voting in polls and adding requests.")
            return
        try:
            cursor.execute("INSERT INTO settings (guild_id, setting, value) VALUES (?, ?, ?)", (guild_id, "blocked_roles", str(int(role.id))))  # noqa: E501
            conn.commit()
            await ctx.send(f"Role `{role.name}` has been blocked from voting in polls and adding requests.")  # noqa: E501
        except Exception as e:
            await ctx.send(f"Failed to block role `{role_name}` due to a database error.")
            print(f"Error blocking role in DB: {e}")
    except Exception as e:
        print(f"Error blocking role: {e}")
        await ctx.send("An error occurred while trying to block the role.")

@bot.command(name="unblockrole", brief="Unblock a role from voting in polls/requests")
@commands.has_permissions(administrator=True)
async def unblock_role(ctx, *, role_name: str):
    """Remove a role from the block list that prevents users with that role from voting in polls or adding requests(server mods excluded)"""  # noqa: E501
    try:
        guild_id = ctx.guild.id
        # Case-insensitive role name search
        role = discord.utils.get(ctx.guild.roles, name=lambda n: n.lower() == role_name.lower())

        if role is None:
            await ctx.send(f"Role `{role_name}` not found. Please check the role name and try again.")
            return

        try:
            result = cursor.execute("DELETE FROM settings WHERE guild_id = ? AND setting = ? AND value = ?", (guild_id, "blocked_roles", str(int(role.id))))  # noqa: E501
            conn.commit()
            if result.rowcount == 0:
                await ctx.send(f"Role `{role_name}` was not blocked, so nothing was changed.")
            else:
                await ctx.send(f"Role `{role.name}` has been unblocked and can now vote in polls and add requests.")  # noqa: E501
        except Exception as e:
            await ctx.send(f"Failed to unblock role `{role_name}` due to a database error.")
            print(f"Error unblocking role in DB: {e}")
    except Exception as e:
        print(f"Error unblocking role: {e}")
        await ctx.send("An error occurred while trying to unblock the role.")    


def check_blocked_roles(member: discord.Member):
    # Allow users with manage_messages or higher perms to bypass block
    if member.guild_permissions.manage_messages or member.guild_permissions.administrator:
        return False
    guild_id = member.guild.id
    blocked_roles = cursor.execute("SELECT * FROM settings WHERE guild_id = ? AND setting = ?", (guild_id, "blocked_roles")).fetchall()  # noqa: E501
    blocked_role_ids = {int(row[2]) for row in blocked_roles}
    return any(int(role.id) in blocked_role_ids for role in member.roles)

async def main():
    await bot.add_cog(polls_group(bot))
    await bot.add_cog(emote_group(bot))
    await bot.start(TOKEN)

asyncio.run(main())
