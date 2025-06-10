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
   # if message.channel.id == REQUESTS_CHANNEL_ID and message.content.startswith('m.anime '):
    #    anime_name = message.content.split('m.anime ')[1]
     #   poll_channel = bot.get_channel(POLLS_CHANNEL_ID)
        # Assuming the number of requests doesn't exceed the number of emotes.
      #  emote = EMOTES.pop(0)  # Take the first emote and remove it from the list
       # sent_message = await poll_channel.send(f"{emote} {anime_name}")
        #await sent_message.add_reaction(emote)
    await bot.process_commands(message)
    


@bot.command(name="createpoll")
async def create_poll(ctx):
    """Command to manually create polls from requests"""
    if ctx.channel.id != POLLS_CHANNEL_ID:
        return

    global EMOTES
    EMOTES = ORIGINAL_EMOTES.copy()
    
    # Fetch the last # of messages from the requests channel
    request_channel = bot.get_channel(REQUESTS_CHANNEL_ID)
    messages = []
    async for message in request_channel.history(limit=1000):
        messages.append(message)


    # Extract anime names from messages that match the format "m.anime {anime name}"
    anime_requests = [msg.content.split('m.anime ')[1] for msg in messages if msg.content.startswith('m.anime ')]

    # Create polls using the extracted anime names
    for idx, anime_name in enumerate(anime_requests):
        if idx < len(EMOTES):
            emote = EMOTES[idx]
            sent_message = await ctx.send(f"{emote} {anime_name}")
            await sent_message.add_reaction(emote)
        


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

    # # Spacer to force description below fields
    # embed.add_field(name="\u200b", value="\u200b", inline=False)

    # Description
    description = media.get("description", "No description available.").replace("<br>", "\n")
    embed.add_field(name="Description", value=description[:1024], inline=False)

    # Links
    anilist_link = media.get("siteUrl")
    mal_link = None
    for link in media.get("externalLinks", []):
        if link.get("site", "").lower() == "myanimelist":
            mal_link = link.get("url")
            break

    link_text = f"[AniList]({anilist_link})"
    if mal_link:
        link_text += f" - [MyAnimeList]({mal_link})"

    embed.add_field(name="Links", value=link_text, inline=False)

    return embed

# ---------- SEARCH + EMBED ----------
def search_anime_embed(title: str):
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

    variables = {"search": title, "sort": ["POPULARITY_DESC"], "isAdult": False}

    r = requests.post(url, json={"query": query, "variables": variables})
    if r.status_code != 200:
        return f"❌ AniList error ({r.status_code})."

    media = r.json().get("data", {}).get("Page", {}).get("media", [])
    if not media:
        return "No matching anime found."

    
    return media[0]


# ---------- BOT COMMAND EXAMPLE ----------
@bot.command(name="anime")
# !anime <title>
# Command searches anilist for an anime under the given name and returns the top search result. 
async def anime(ctx, *, anime_name: str):
    if ctx.channel.id != REQUESTS_CHANNEL_ID:
        print("wrong channel")
        return
    """!anime <title> – show AniList info for the most-popular match"""
    anime_result = search_anime_embed(anime_name)

    if isinstance(anime_result, str):
        await ctx.send(anime_result)
        return

    result = make_anime_embed(anime_result)

    #filters dupes
    if any(entry[1] == anime_result["id"] for entry in POLL_LIST):
        await ctx.send("That has already been added to the poll list.")
        return

    poll_item = [anime_result["title"]["english"], anime_result["id"]]
    POLL_LIST.append(poll_item)
    print(POLL_LIST)

    if isinstance(result, discord.Embed):
        await ctx.send(embed=result)
    else:
        await ctx.send(result)

# ---------- Poll Viewer
@bot.command(name="viewpoll")
async def viewpoll(ctx):
    for anime in POLL_LIST:
        await ctx.send(anime[0])




bot.run(TOKEN)