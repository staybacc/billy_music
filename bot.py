import discord
from discord.ext import commands
import yt_dlp as youtube_dl  # Use yt-dlp
import asyncio  # Import asyncio for handling event loops
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()  # You can specify dotenv_path if the file isn't in the root directory

# Fetch the Discord token from the .env file
TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
    raise ValueError("Discord token not found! Ensure it's set correctly in the .env file.")

# Intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Suppress noise from yt-dlp
youtube_dl.utils.bug_reports_message = lambda: ""

# YouTube download and ffmpeg configuration
ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Class for handling YouTube audio streams
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Event handler for bot being ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# Command to play music
@bot.command()
async def play(ctx, url):
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel!")
        return

    voice_channel = ctx.message.author.voice.channel
    if not ctx.voice_client:
        await voice_channel.connect()

    player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
    ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
    await ctx.send(f"Now playing: {player.title}")

# Command to stop the bot
@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

# Run the bot with your token
bot.run(TOKEN)