import discord
from discord.ext import commands
import yt_dlp
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -ar 48000 -ac 2',
}

queues = {}
current_volume = {}

def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]

def make_embed(title, description, color=0x9B59B6, thumbnail=None):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text='🎵 MusicBot — Fait avec ❤️')
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed

async def play_next(ctx):
    queue = get_queue(ctx.guild.id)
    if len(queue) > 0:
        url, title, thumbnail = queue.pop(0)
        volume = current_volume.get(ctx.guild.id, 0.5)
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(url, **ffmpeg_options),
            volume=volume
        )
        ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        embed = make_embed('🎵 En train de jouer', f'**{title}**', color=0x9B59B6, thumbnail=thumbnail)
        await ctx.send(embed=embed)
    else:
        embed = make_embed('✅ Terminé', 'La file d\'attente est vide !', color=0x2ECC71)
        await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f'✅ {bot.user} est connecté !')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name="!help_music"
    ))

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        embed = make_embed('✅ Connecté !', f'Connecté à **{ctx.author.voice.channel.name}** !', color=0x2ECC71)
        await ctx.send(embed=embed)
    else:
        embed = make_embed('❌ Erreur', 'Tu dois être dans un salon vocal !', color=0xE74C3C)
        await ctx.send(embed=embed)

@bot.command()
async def play(ctx, *, search):
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            embed = make_embed('❌ Erreur', 'Tu dois être dans un salon vocal !', color=0xE74C3C)
            await ctx.send(embed=embed)
            return

    async with ctx.typing():
        with yt_dlp.YoutubeDL(ytdl_options) as ydl:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)
            entry = info['entries'][0]
            url = entry['url']
            title = entry['title']
            thumbnail = entry.get('thumbnail', None)

    queue = get_queue(ctx.guild.id)

    if ctx.voice_client.is_playing():
        queue.append((url, title, thumbnail))
        embed = make_embed('➕ Ajouté à la file', f'**{title}**', color=0x3498DB, thumbnail=thumbnail)
        await ctx.send(embed=embed)
    else:
        volume = current_volume.get(ctx.guild.id, 0.5)
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(url, **ffmpeg_options),
            volume=volume
        )
        ctx.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        embed = make_embed('🎵 En train de jouer', f'**{title}**', color=0x9B59B6, thumbnail=thumbnail)
        await ctx.send(embed=embed)

@bot.command()
async def queue(ctx):
    q = get_queue(ctx.guild.id)
    if len(q) == 0:
        embed = make_embed('📭 File vide', 'Aucune musique dans la file !', color=0xE74C3C)
    else:
        description = '\n'.join([f'`{i+1}.` {title}' for i, (_, title, _) in enumerate(q)])
        embed = make_embed('📋 File d\'attente', description, color=0x3498DB)
    await ctx.send(embed=embed)

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        embed = make_embed('⏭️ Skippé', 'Passage à la musique suivante !', color=0xF39C12)
        await ctx.send(embed=embed)
    else:
        embed = make_embed('❌ Erreur', 'Aucune musique en cours !', color=0xE74C3C)
        await ctx.send(embed=embed)

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        embed = make_embed('⏸️ Pause', 'Musique mise en pause !', color=0xF39C12)
        await ctx.send(embed=embed)
    else:
        embed = make_embed('❌ Erreur', 'Aucune musique en cours !', color=0xE74C3C)
        await ctx.send(embed=embed)

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        embed = make_embed('▶️ Reprise', 'Musique reprise !', color=0x2ECC71)
        await ctx.send(embed=embed)
    else:
        embed = make_embed('❌ Erreur', 'Aucune musique en pause !', color=0xE74C3C)
        await ctx.send(embed=embed)

def load_premium():
    if os.path.exists('premium.json'):
        with open('premium.json', 'r') as f:
            return json.load(f)
    return {"premium_guilds": []}

def save_premium(data):
    with open('premium.json', 'w') as f:
        json.dump(data, f, indent=4)

def is_premium(guild_id):
    data = load_premium()
    return str(guild_id) in data['premium_guilds']

OWNER_ID = 909529762047881219

@bot.command()
async def volume(ctx, vol: int):
    if not is_premium(ctx.guild.id):
        embed = make_embed('👑 Premium requis', 'Cette commande est réservée aux serveurs premium !\nContacte le développeur pour obtenir le premium.', color=0xF39C12)
        await ctx.send(embed=embed)
        return
    if 0 <= vol <= 100:
        current_volume[ctx.guild.id] = vol / 100
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = vol / 100
        embed = make_embed('🔊 Volume', f'Volume réglé à **{vol}%** !', color=0x2ECC71)
        await ctx.send(embed=embed)
    else:
        embed = make_embed('❌ Erreur', 'Le volume doit être entre 0 et 100 !', color=0xE74C3C)
        await ctx.send(embed=embed)

@bot.command()
async def addpremium(ctx, guild_id: str):
    if ctx.author.id != OWNER_ID:
        await ctx.send('❌ Tu n\'as pas la permission !')
        return
    data = load_premium()
    if guild_id not in data['premium_guilds']:
        data['premium_guilds'].append(guild_id)
        save_premium(data)
        await ctx.send(f'✅ Serveur `{guild_id}` ajouté en premium !')
    else:
        await ctx.send('⚠️ Ce serveur est déjà premium !')

@bot.command()
async def removepremium(ctx, guild_id: str):
    if ctx.author.id != OWNER_ID:
        await ctx.send('❌ Tu n\'as pas la permission !')
        return
    data = load_premium()
    if guild_id in data['premium_guilds']:
        data['premium_guilds'].remove(guild_id)
        save_premium(data)
        await ctx.send(f'✅ Serveur `{guild_id}` retiré du premium !')
    else:
        await ctx.send('⚠️ Ce serveur n\'est pas premium !')

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        queues[ctx.guild.id] = []
        ctx.voice_client.stop()
        embed = make_embed('⏹️ Stop', 'Musique arrêtée et file vidée !', color=0xE74C3C)
        await ctx.send(embed=embed)

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        queues[ctx.guild.id] = []
        await ctx.voice_client.disconnect()
        embed = make_embed('👋 Au revoir', 'Bot déconnecté du salon vocal !', color=0x95A5A6)
        await ctx.send(embed=embed)

@bot.command()
async def help_music(ctx):
    premium = is_premium(ctx.guild.id)
    embed = discord.Embed(title='🎵 Commandes MusicBot', color=0x9B59B6)
    embed.add_field(name='▶️ Musique', value='`!play <chanson>` — Jouer une chanson\n`!skip` — Passer à la suivante\n`!pause` — Mettre en pause\n`!resume` — Reprendre', inline=False)
    embed.add_field(name='📋 File', value='`!queue` — Voir la file d\'attente\n`!stop` — Arrêter et vider la file', inline=False)
    embed.add_field(name='🔊 Autres', value='`!join` — Rejoindre le salon\n`!leave` — Quitter le salon', inline=False)
    if premium:
        embed.add_field(name='👑 Premium', value='`!volume <0-100>` — Régler le volume', inline=False)
        embed.set_footer(text='✨ Serveur Premium | 🎵 MusicBot')
    else:
        embed.add_field(name='👑 Premium', value='`!volume` — 🔒 Réservé aux serveurs premium', inline=False)
        embed.set_footer(text='🎵 MusicBot — Tape !premium pour en savoir plus')
    await ctx.send(embed=embed)

bot.run(TOKEN)