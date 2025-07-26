import discord
from discord.ext import commands
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from keep_alive import keep_alive

from utils.mongo import get_guild_config 
from utils import mongo 
from cogs.verification import VerifyButtonView 

load_dotenv()
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True

async def get_prefix(bot, message):
    if not message.guild:
        return "."
    config = await get_guild_config(str(message.guild.id))
    return config.get("prefix", ".")

bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.remove_command("help")

try:
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    bot.mongo_client = mongo_client
    bot.db = mongo_client["nexusec"]
    print("✅ Connected to MongoDB.")
except Exception as e:
    print(f"❌ MongoDB connection failed: {type(e).__name__} - {e}")

# On ready
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="/help | NexuSec"))
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

    try:
        bot.add_view(VerifyButtonView())  # ✅ Persistent view
        print("✅ Added persistent VerifyButtonView.")
    except Exception as e:
        print(f"❌ Failed to add view: {type(e).__name__} - {e}")

    synced = await bot.tree.sync()
    print(f"🔁 Synced {len(synced)} slash commands.")
    print("------")

async def load_cogs():
    print("🔍 Loading cogs...")
    if not os.path.exists("cogs"):
        os.makedirs("cogs")
        print("📁 Created 'cogs' folder.")

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Loaded: {filename}")
            except Exception as e:
                print(f"❌ Failed to load {filename}: {type(e).__name__} - {e}. Please ensure 'cogs/{filename}' exists and is error-free.")
    print("✅ All cogs loaded.")

async def main():
    print("🚀 Starting NexuSec...")
    keep_alive()
    async with bot:
        await load_cogs()
        try:
            await bot.start(TOKEN)
        finally:
            await bot.close()
            mongo_client.close()
            print("🛑 MongoDB connection closed.")

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("🛑 Bot manually stopped.")
except Exception as e:
    print(f"💥 Unhandled exception: {type(e).__name__} - {e}")
