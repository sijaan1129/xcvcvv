import discord
from discord.ext import commands
import json
import os
import asyncio
from typing import Optional
from keep_alive import keep_alive

# Start the keep alive server
keep_alive()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='/', intents=intents)

# File to store channel configurations
CONFIG_FILE = 'bot_config.json'

def load_config():
    """Load bot configuration from file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    """Save bot configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# Load initial config
config = load_config()

@bot.event
async def on_ready():
    """Bot startup event"""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} servers')
    
    # Set bot status
    activity = discord.Activity(type=discord.ActivityType.watching, name="for broadcast messages | /set-channel")
    await bot.change_presence(activity=activity)

@bot.command(name="set-channel", description="Set the channel for broadcasting messages to all members")
async def set_channel(ctx, channel: discord.TextChannel):
    """Set the broadcast channel for a server"""
    
    # Check permissions
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You need administrator permissions to use this command!", delete_after=10)
        return
    
    guild_id = str(ctx.guild.id)
    
    # Update config
    if guild_id not in config:
        config[guild_id] = {}
    
    config[guild_id]['broadcast_channel'] = channel.id
    save_config(config)
    
    embed = discord.Embed(
        title="✅ Broadcast Channel Set!",
        description=f"Messages sent in {channel.mention} will now be broadcast to all server members via DM.",
        color=discord.Color.green()
    )
    embed.add_field(
        name="ℹ️ How it works:",
        value="• Send any message in the designated channel\n• Bot will DM that message to all server members\n• Only admins can change this setting\n• Use `/info` to check current settings",
        inline=False
    )
    embed.add_field(
        name="🔧 Additional Commands:",
        value="• `/info` - View bot configuration\n• `/test <message>` - Send test broadcast\n• `/remove-channel` - Remove broadcast channel",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name="remove-channel", description="Remove the current broadcast channel")
async def remove_channel(ctx):
    """Remove the broadcast channel setting"""
    
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ You need administrator permissions to use this command!", delete_after=10)
        return
    
    guild_id = str(ctx.guild.id)
    
    if guild_id not in config or 'broadcast_channel' not in config[guild_id]:
        await ctx.send("❌ No broadcast channel is currently set!", delete_after=10)
        return
    
    # Remove the broadcast channel
    del config[guild_id]['broadcast_channel']
    if not config[guild_id]:  # Remove empty guild config
        del config[guild_id]
    save_config(config)
    
    embed = discord.Embed(
        title="✅ Broadcast Channel Removed",
        description="No channel is set for broadcasting. Use `/set-channel` to configure a new one.",
        color=discord.Color.orange()
    )
    
    await ctx.send(embed=embed)

@bot.command(name="info", description="Show current bot configuration and stats")
async def info(ctx):
    """Display bot information and current settings"""
    guild_id = str(ctx.guild.id)
    
    embed = discord.Embed(
        title="🤖 DM Broadcast Bot Info",
        description="Instantly send messages to all server members via DM!",
        color=discord.Color.blue()
    )
    
    # Current broadcast channel
    if guild_id in config and 'broadcast_channel' in config[guild_id]:
        channel_id = config[guild_id]['broadcast_channel']
        channel = bot.get_channel(channel_id)
        if channel:
            embed.add_field(
                name="📢 Current Broadcast Channel",
                value=f"{channel.mention}",
                inline=False
            )
        else:
            embed.add_field(
                name="⚠️ Broadcast Channel",
                value="Channel not found (may have been deleted)",
                inline=False
            )
    else:
        embed.add_field(
            name="📢 Broadcast Channel",
            value="Not set - use `/set-channel` to configure",
            inline=False
        )
    
    # Server stats
    embed.add_field(
        name="📊 Server Stats",
        value=f"• Members: {ctx.guild.member_count}\n• Channels: {len(ctx.guild.channels)}",
        inline=True
    )
    
    # Bot stats
    embed.add_field(
        name="🤖 Bot Stats",
        value=f"• Servers: {len(bot.guilds)}\n• Latency: {round(bot.latency * 1000)}ms",
        inline=True
    )
    
    embed.add_field(
        name="🔧 Available Commands",
        value="• `/set-channel` - Set broadcast channel\n• `/remove-channel` - Remove broadcast channel\n• `/test` - Send test message\n• `/info` - Show this info",
        inline=False
    )
    
    embed.set_footer(text="Made with ❤️ for easy server communication")
    
    await ctx.send(embed=embed)

@bot.command(name="test", description="Send a test broadcast message (Admin only)")
async def test_broadcast(ctx, *, message: str = "🧪 This is a test broadcast message!"):
    """Test the broadcast functionality"""
    
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Only administrators can use this command!", delete_after=10)
        return
    
    guild_id = str(ctx.guild.id)
    
    if guild_id not in config or 'broadcast_channel' not in config[guild_id]:
        await ctx.send("❌ No broadcast channel set! Use `/set-channel` first.", delete_after=10)
        return
    
    await ctx.send("🧪 Sending test broadcast...")
    
    # Broadcast the test message
    success_count, fail_count = await broadcast_message(ctx.guild, message, ctx.author)
    
    embed = discord.Embed(
        title="🧪 Test Broadcast Complete",
        description=f"**Message:** {message}",
        color=discord.Color.green()
    )
    embed.add_field(
        name="📊 Results",
        value=f"✅ Successful: {success_count}\n❌ Failed: {fail_count}\n📊 Total: {success_count + fail_count}",
        inline=False
    )
    
    if fail_count > 0:
        embed.add_field(
            name="ℹ️ Failed deliveries",
            value="Some users may have DMs disabled or have left the server.",
            inline=False
        )
    
    await ctx.send(embed=embed, delete_after=60)

async def broadcast_message(guild, message_content, author):
    """Broadcast a message to all members in the guild"""
    success_count = 0
    fail_count = 0
    
    # Create embed for the broadcast message
    embed = discord.Embed(
        title="📢 Server Broadcast",
        description=message_content,
        color=discord.Color.blue()
    )
    embed.set_author(
        name=f"From: {author.display_name}",
        icon_url=author.avatar.url if author.avatar else None
    )
    embed.set_footer(
        text=f"Sent from: {guild.name}",
        icon_url=guild.icon.url if guild.icon else None
    )
    embed.timestamp = discord.utils.utcnow()
    
    # Send to all members
    for member in guild.members:
        if member.bot:  # Skip bots
            continue
            
        try:
            await member.send(embed=embed)
            success_count += 1
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.15)
        except discord.Forbidden:
            # User has DMs disabled
            fail_count += 1
        except discord.HTTPException:
            # Other error (user not found, etc.)
            fail_count += 1
        except Exception as e:
            print(f"Error sending DM to {member}: {e}")
            fail_count += 1
    
    return success_count, fail_count

@bot.event
async def on_message(message):
    """Handle messages in broadcast channels"""
    
    # Ignore bot messages
    if message.author.bot:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Check if this is a broadcast channel
    guild_id = str(message.guild.id)
    
    if guild_id not in config or 'broadcast_channel' not in config[guild_id]:
        return
    
    broadcast_channel_id = config[guild_id]['broadcast_channel']
    
    if message.channel.id != broadcast_channel_id:
        return
    
    # This is a broadcast message!
    print(f"Broadcasting message from {message.author} in {message.guild.name}")
    
    # Add reaction to show it's being processed
    await message.add_reaction("📡")
    
    try:
        success_count, fail_count = await broadcast_message(
            message.guild, 
            message.content, 
            message.author
        )
        
        # Update reaction to show completion
        await message.remove_reaction("📡", bot.user)
        await message.add_reaction("✅")
        
        # Send summary to the broadcast channel
        summary_embed = discord.Embed(
            title="📊 Broadcast Complete!",
            color=discord.Color.green()
        )
        summary_embed.add_field(
            name="📈 Delivery Results",
            value=f"✅ **Delivered:** {success_count}\n❌ **Failed:** {fail_count}\n📊 **Total Members:** {success_count + fail_count}",
            inline=True
        )
        
        if fail_count > 0:
            success_rate = round((success_count / (success_count + fail_count)) * 100, 1)
            summary_embed.add_field(
                name="📊 Success Rate",
                value=f"{success_rate}%",
                inline=True
            )
        
        summary_embed.set_footer(text="Failed deliveries are usually due to disabled DMs")
        
        await message.reply(embed=summary_embed, delete_after=60)
        
    except Exception as e:
        print(f"Error in broadcast: {e}")
        await message.remove_reaction("📡", bot.user)
        await message.add_reaction("❌")
        
        error_embed = discord.Embed(
            title="❌ Broadcast Failed",
            description="An error occurred while sending the broadcast.",
            color=discord.Color.red()
        )
        await message.reply(embed=error_embed, delete_after=30)

@bot.event
async def on_guild_join(guild):
    """When bot joins a new server"""
    print(f"Joined new server: {guild.name} ({guild.id})")
    
    # Try to find a general channel to send welcome message
    channel = None
    for ch in guild.text_channels:
        if ch.permissions_for(guild.me).send_messages:
            channel = ch
            break
    
    if channel:
        embed = discord.Embed(
            title="👋 Thanks for adding me!",
            description="I'm a DM Broadcast Bot that can send messages to all server members instantly!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="🚀 Quick Setup",
            value="1. Use `/set-channel #channel` to set your broadcast channel\n2. Send any message in that channel\n3. I'll DM it to all server members!",
            inline=False
        )
        embed.add_field(
            name="📋 Commands",
            value="• `/set-channel` - Set broadcast channel\n• `/info` - View configuration\n• `/test` - Send test message",
            inline=False
        )
        embed.set_footer(text="Need help? Use /info for more details!")
        
        try:
            await channel.send(embed=embed)
        except:
            pass

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    
    print(f"Command error: {error}")
    
    embed = discord.Embed(
        title="❌ Error",
        description="An error occurred while processing your command.",
        color=discord.Color.red()
    )
    
    try:
        await ctx.send(embed=embed, delete_after=30)
    except:
        pass

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set!")
        print("Please set your Discord bot token in the environment variables.")
        exit(1)
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("Error: Invalid Discord token!")
    except Exception as e:
        print(f"Error starting bot: {e}")
