import discord
from discord.ext import commands
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()
TOKEN = os.getenv("TOKEN")
MONGO_URI = os.getenv("MONGO_URI")  # Added this line to get MongoDB URI from env

# Enhanced intents configuration
intents = discord.Intents.all()  # Changed to .all() to ensure all required intents are enabled
intents.typing = False  # Disable unnecessary intents
intents.presences = False
intents.dm_typing = False
intents.dm_reactions = False

async def get_prefix(bot, message):
    if not message.guild:
        return "."
    # Make sure get_guild_config is defined or imported
    config = await get_guild_config(str(message.guild.id))
    return config.get("prefix", ".")

# Initialize bot with proper settings
bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    activity=discord.Activity(type=discord.ActivityType.watching, name="for commands"),
    status=discord.Status.online
)
bot.remove_command("help")

# Database connection with better error handling
async def connect_db():
    try:
        mongo_client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        await mongo_client.server_info()  # Test connection
        bot.mongo_client = mongo_client
        bot.db = mongo_client["aimbot"]
        print("✅ Connected to MongoDB.")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {type(e).__name__} - {e}")
        # Exit if database is critical for your bot
        # sys.exit(1)

# Enhanced on_ready event
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"✅ Connected to {len(bot.guilds)} guilds")
    
    # Sync slash commands with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            synced = await bot.tree.sync()
            print(f"🔁 Synced {len(synced)} slash commands (attempt {attempt + 1}/{max_retries})")
            break
        except Exception as e:
            print(f"❌ Sync failed (attempt {attempt + 1}): {type(e).__name__} - {e}")
            if attempt == max_retries - 1:
                print("⚠️ Could not sync slash commands")
            await asyncio.sleep(2)

    print("------")

# Improved cog loading with retries
async def load_cogs():
    print("🔍 Loading cogs...")
    if not os.path.exists("cogs"):
        os.makedirs("cogs")
        print("📁 Created 'cogs' folder.")

    retry_count = 2
    loaded_cogs = 0
    
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith('_'):
            cog_name = filename[:-3]
            for attempt in range(retry_count + 1):
                try:
                    await bot.load_extension(f"cogs.{cog_name}")
                    print(f"✅ Loaded: {filename}")
                    loaded_cogs += 1
                    break
                except Exception as e:
                    if attempt == retry_count:
                        print(f"❌ Failed to load {filename} after {retry_count} attempts: {type(e).__name__} - {e}")
                    else:
                        print(f"⚠️ Retrying {filename}... (attempt {attempt + 1})")
                        await asyncio.sleep(1)
    
    print(f"✅ Loaded {loaded_cogs} cogs successfully")

# Main function with proper cleanup
async def main():
    print("🚀 Starting bot...")
    keep_alive()
    
    # Connect to database first
    await connect_db()
    
    # Load cogs and start bot
    async with bot:
        await load_cogs()
        try:
            await bot.start(TOKEN)
        except discord.LoginFailure:
            print("❌ Invalid bot token")
        except KeyboardInterrupt:
            print("🛑 Bot stopped by user")
        except Exception as e:
            print(f"💥 Fatal error: {type(e).__name__} - {e}")
        finally:
            if hasattr(bot, 'mongo_client'):
                await bot.mongo_client.close()
                print("🛑 MongoDB connection closed.")
            print("🛑 Bot shutdown complete")

# Error handling for the main loop
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Process interrupted")
    except Exception as e:
        print(f"💥 Critical error in main loop: {type(e).__name__} - {e}")
