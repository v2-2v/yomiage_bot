import discord
from discord.ext import commands
import os
import asyncio
import json
import requests

TOKEN = "ここにトークンを代入"
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


play_queues = {}

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!来いでくるよ"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        help_text = """
**📢 読み上げBot コマンド一覧**

`!来い` - ボイスチャンネルに接続  
`!帰れ` - ボイスチャンネルから切断  
`!ここを読む` - 今のテキストチャンネルを読み上げ対象に設定   
"""
        await ctx.send(help_text)
    
def add_settings(data):
    global settings
    already=False
    for ss in settings:
        if ss["guild_id"]==data["guild_id"]:
            ss["text_channel_id"]=data["text_channel_id"]
            already=True
    if not already:
        settings.append(data)
    with open("setting.json","w") as f:
        json.dump(settings, f, indent=2)

def load_settings():
    if os.path.exists("setting.json"):
        with open("setting.json", "r") as f:
            return json.load(f)
    return []

settings = load_settings()

@bot.command()
async def 来い(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
    else:
        await ctx.send(f"VC入れよ")
        

@bot.command()
async def 帰れ(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        
@bot.command()
async def ここを読む(ctx):
    guild_id = str(ctx.guild.id)
    add_settings({
        "guild_id":guild_id,
        "text_channel_id": ctx.channel.id
    })
    await ctx.send(f"このチャンネルを読み上げ対象に設定しました。この設定は保存されます")
    global setting
    setting = load_settings()

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author.bot:
        return
    if message.guild is None or message.guild.voice_client is None:
        return
    if message.content.startswith("!"):
        return

    guild_id = message.guild.id
    already=False
    for ss in settings:
        if ss["guild_id"]==str(guild_id):
            target=ss["text_channel_id"]
            already=True
    if not already:
        await message.channel.send("!ここを読む で読む対象を指定してください")
        return
    if message.channel.id != target:
        return
    if guild_id not in play_queues:
        play_queues[guild_id] = asyncio.Queue()
        bot.loop.create_task(audio_player(message.guild))

    await play_queues[guild_id].put(message.content)

async def audio_player(guild):
    guild_id = guild.id
    queue = play_queues[guild_id]

    while True:
        text = await queue.get()
        filename = f"mp3/{guild_id}.mp3"
    
        voicevox_tts(text,filename)

        vc = guild.voice_client
        if vc is not None:
            finished = asyncio.Event()

            def after_play(e):
                try:
                    os.remove(filename)
                except:
                    pass
                finished.set()

            vc.play(discord.FFmpegPCMAudio(filename), after=after_play)
            await finished.wait()
        else:
            break


def voicevox_tts(text: str, filename, speaker: int = 3):
    # 音声合成クエリを作成
    query = requests.post(
        "http://localhost:50021/audio_query",
        params={"text": text, "speaker": speaker}
    )
    query.raise_for_status()
    query_data = query.json()

    # 音声合成リクエスト
    synthesis = requests.post(
        "http://localhost:50021/synthesis",
        params={"speaker": speaker},
        json=query_data
    )
    synthesis.raise_for_status()

    # ファイルとして保存
    with open(filename, "wb") as f:
        f.write(synthesis.content)
    
bot.run(TOKEN)
