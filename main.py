import discord
from discord.ext import commands
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(
    command_prefix=".",
    intents=intents,
    chunk_guilds_at_startup=True
)

async def connect_db():
    try:
        mongo_client = AsyncIOMotorClient(MONGO_URI)
        await mongo_client.server_info()
        bot.mongo_client = mongo_client
        bot.db = mongo_client["aimbot"]
        print("✅ Connected to MongoDB.")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {type(e).__name__} - {e}")

@bot.event
async def on_ready():
    print(f"\n✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"✅ Connected to {len(bot.guilds)} guild(s)")
    print(f"✅ Serving {len(bot.users)} user(s)\n")
    
    try:
        synced = await bot.tree.sync()
        print(f"🔁 Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Command sync failed: {type(e).__name__} - {e}")

    await bot.change_presence(activity=discord.Game(name="/help"))

async def load_cogs():
    print("\n🔍 Loading cogs...")
    if not os.path.exists("cogs"):
        os.makedirs("cogs")
        print("📁 Created 'cogs' directory")

    loaded = 0
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith('_'):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Loaded: {filename}")
                loaded += 1
            except Exception as e:
                print(f"❌ Failed to load {filename}: {type(e).__name__} - {e}")
    
    print(f"\n✅ Successfully loaded {loaded} cog(s)")

async def main():
    print("\n🚀 Starting bot...")
    keep_alive()
    
    await connect_db()
    
    async with bot:
        await load_cogs()
        try:
            await bot.start(TOKEN)
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
        except Exception as e:
            print(f"\n💥 Fatal error: {type(e).__name__} - {e}")
        finally:
            if hasattr(bot, 'mongo_client'):
                await bot.mongo_client.close()
                print("🛑 Closed MongoDB connection")
            print("🛑 Bot shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted")
    except Exception as e:
        print(f"\n💥 Critical error: {type(e).__name__} - {e}")
