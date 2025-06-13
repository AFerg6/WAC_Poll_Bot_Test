import discord, requests
from discord.ext import commands, tasks

intents = discord.Intents.default()
intents.members = True  # SERVER MEMBERS INTENT
intents.presences = True  # PRESENCE INTENT
intents.message_content = True



TOKEN = 'MTM4MjA1OTY3NDI0OTA2ODU1NQ.GG6bGK.27R4DniYshwNJtFI3jBo7Jk7Y2jQGyL6VWz9Qg'
GUILD_ID = 1382059395545960521  # Your server's ID
REQUESTS_CHANNEL_ID = 1382060973355171890  # The requests channel ID
POLLS_CHANNEL_ID = 1382061036244570182  # The polls channel ID

#List of anime for polls
POLL_LIST = []
ANIME_CACHE: dict[int, dict] = {} # message_id -> list of anime
custom_id_counter = -1

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

EMOTES = ORIGINAL_EMOTES.copy()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    
@bot.command(name="createpoll")
async def create_poll(ctx):
    """Command to manually create polls from requests"""
    if ctx.channel.id != POLLS_CHANNEL_ID:
        await ctx.send("Wrong channel")
        return
    
    perms = ctx.author.guild_permissions  
    if not perms.kick_members:
        await ctx.send("You have insufficient perms")
        return

    global EMOTES
    global POLL_LIST
    global custom_id_counter

    EMOTES = ORIGINAL_EMOTES.copy()
    #sorts list alphabetically, resets custom id counter and clears message cache
    POLL_LIST.sort(key=lambda x: x[0].lower())
    custom_id_counter = -1
    ANIME_CACHE.clear()
    
    # Create polls using the extracted anime names
    for idx, anime in enumerate(POLL_LIST):
        if idx < len(EMOTES):
            emote = EMOTES[idx]
            sent_message = await ctx.send(f"{emote} {anime[0]}")
            await sent_message.add_reaction(emote)

    #clear poll list
    POLL_LIST = []
        
# ---------- EMBED BUILDER ----------
def make_anime_embed(media: dict) -> discord.Embed:
    """Builds a Discord embed from a single AniList Media dict."""
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
    embed.add_field(name="Type", value=media.get("format", "—"), inline=True)
    embed.add_field(name="Episodes", value=media.get("episodes", "—"), inline=True)
    embed.add_field(name="Status", value=media.get("status", "—").title(), inline=True)

    # Row 2
    season = media.get("season")
    yr = media.get("seasonYear")
    embed.add_field(
        name="Season", value=f"{season.title()} {yr}" if season and yr else "—", inline=True
    )
    score = media.get("averageScore")
    embed.add_field(name="Average Score", value=f"{score}%" if score else "N/A", inline=True)

    genres = media.get("genres", [])
    embed.add_field(name="Genres", value=", ".join(genres[:4]) if genres else "—", inline=True)

    # Description
    description = media.get("description", "No description available.").replace("<br>", "\n")
    embed.add_field(name="Description", value=description[:1024], inline=False)

    # Links
    anilist_link = media.get("siteUrl")
    link_text = f"[AniList]({anilist_link})"
    embed.add_field(name="Links", value=link_text, inline=False)

    return embed

# ---------- ANILSIT SEARCH  ----------
def search_anime(title: str):
    """Search AniList for <title>, return an Embed for the most-popular match (or an error string)."""
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
        return f"❌ AniList error ({r.status_code})."

    media = r.json().get("data", {}).get("Page", {}).get("media", [])
    if not media:
        return "No matching anime found."

    return media

# ---------- Poll Viewer ----------
@bot.command(name="viewpoll")
async def view_poll(ctx):
    """View all items in the poll List"""

    #lock out command to execs only
    perms = ctx.author.guild_permissions  
    if not perms.kick_members:
        await ctx.send("You have insufficient perms")
        return

    #Sends empty list msg if poll list is empty
    if POLL_LIST == []:
        await ctx.send("The poll list is empty")

    #prints all items in poll sorted alphabetically
    for anime in POLL_LIST:
        POLL_LIST.sort(key=lambda x: x[0].lower())
        await ctx.send(f"{anime[0]} ({anime[1]})")

#------ ANIME SEARCH
@bot.command(name="anime")
async def anime(ctx, *, anime_name: str):
    """Searches for an anime from anilist and shows the top 5. If in the set request channe adds to the poll list otherwise shows anime details"""
    global custom_id_counter

    result = search_anime(anime_name)

    if isinstance(result, str):
        await ctx.send(f"No results found for **{anime_name}**.")
        await ctx.send("React with ✅ within 30 seconds to add it manually to the poll list.")

        confirm_msg = await ctx.send("Do you want to add it as a custom entry?")
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

        custom_title = anime_name.strip()
        POLL_LIST.append([custom_title, custom_id_counter])
        await ctx.send(f"✅ Added custom anime **{custom_title}** to the poll list.")
        custom_id_counter -= 1
        return

    # Build embed with top results
    first = result[0]
    cover_url = first.get("coverImage", {}).get("medium") or first.get("coverImage", {}).get("large")

    embed = discord.Embed(
        title=f'Top results for “{anime_name}”',
        description="React with a number to select, or ❌ to cancel.",
        color=discord.Color.blue(),
    )
    if cover_url:
        embed.set_thumbnail(url=cover_url)

    # Build the list line with numbered options, only up to 5 results
    nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    display_titles = []

    # First line: first three titles
    line1 = []
    for i, anime in enumerate(result[:3]):
        title = anime["title"].get("english") or anime["title"].get("romaji") or "Unknown"
        line1.append(f"{nums[i]}  {title}")
    line1_str = "     ".join(line1)  # 5 spaces for horizontal spacing

    # Second line: last two titles (if present)
    line2 = []
    for i, anime in enumerate(result[3:5], start=3):
        title = anime["title"].get("english") or anime["title"].get("romaji") or "Unknown"
        line2.append(f"{nums[i]}  {title}")
    line2_str = "     ".join(line2) if line2 else ""

    # Combine with vertical spacing between lines
    formatted_display = f"{line1_str}\n\n{line2_str}" if line2_str else line1_str



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
    # ignore bot reactions
    if user.bot:
        return

    #save message to cache to keep interactivity active
    payload = ANIME_CACHE.get(reaction.message.id)
    if not payload:
        return  # reaction isn't for an anime message

    # only command author may react
    if user.id != payload["user_id"]:
        await reaction.message.channel.send(
            f"{user.mention} only the command author can make a selection."
        )
        await reaction.remove(user)
        return

    emoji = str(reaction.emoji)
    nums  = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

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

    #doesnt add item to poll list if not in set request channel
    if reaction.message.channel.id == REQUESTS_CHANNEL_ID: 
        # duplicate check
        if any(entry[1] == anime_id for entry in POLL_LIST):
            await reaction.message.channel.send(
                f" **{title_en}** is already in the poll list."
            )
        else:
            POLL_LIST.append([title_en, anime_id])
            await reaction.message.channel.send(
                f"Added **{title_en}** to the poll list!"
            )
            embed = make_anime_embed(chosen)
            await reaction.message.channel.send(embed=embed)
    else:
        embed = make_anime_embed(chosen)
        await reaction.message.channel.send(embed=embed)


    # clean up
    del ANIME_CACHE[reaction.message.id]
    await reaction.message.clear_reactions()

#-------- CUSTOM ID GENERATION HANDLER -------
def next_negative_id() -> int:
    """Return the next available negative ID (-1, -2, …) not yet used."""
    used = {entry[1] for entry in POLL_LIST if isinstance(entry[1], int) and entry[1] < 0}
    n = -1
    while n in used:
        n -= 1
    return n

#-------- REMOVE ITEM FROM POLL --------
@bot.command(name="remove")
async def remove(ctx, anime_id: str):
    """Remove an item from the poll list using the anime id"""
    global POLL_LIST

    perms = ctx.author.guild_permissions  
    if not perms.kick_members:
        return

    try:
        anime_id_int = int(anime_id)

        # find the first matching entry (returns None if not found)
        removed = next((e for e in POLL_LIST if e[1] == anime_id_int), None)

        # no anime found for id
        if removed is None:
            await ctx.send("❌ No anime with that ID is in the poll list.")
            return

        # rebuild list without the removed entry
        POLL_LIST = [e for e in POLL_LIST if e[1] != anime_id_int]

        await ctx.send(f"✅ **{removed[0]}** has been removed from the poll list.")

    except ValueError:
        await ctx.send("❌ Invalid ID. Please enter a numeric ID.")


@bot.command(name="setpollchannel")
async def set_poll_channel(ctx):

    global POLLS_CHANNEL_ID

    perms = ctx.author.guild_permissions  
    if not perms.administrator:
        await ctx.send("Insufficient perms")
        return
    
    POLLS_CHANNEL_ID = ctx.message.channel.id

    await ctx.send(f"Poll channel set to <#{POLLS_CHANNEL_ID}>")

@bot.command(name="setrequestchannel")
async def set_request_channel(ctx):

    global REQUESTS_CHANNEL_ID

    perms = ctx.author.guild_permissions  
    if not perms.administrator:
        await ctx.send("Insufficient perms")
        return
    
    REQUESTS_CHANNEL_ID = ctx.message.channel.id

    await ctx.send(f"Request channel set to <#{REQUESTS_CHANNEL_ID}>")

@bot.command(name="viewchannels")
async def view_channels(ctx):
    await ctx.send(f"Poll channel: <#{POLLS_CHANNEL_ID}>\nRequets channel: <#{REQUESTS_CHANNEL_ID}>")

bot.run(TOKEN)