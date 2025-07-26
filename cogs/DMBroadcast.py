import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class DMBroadcast(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.broadcast_channels = set()
        self.active_broadcasts = set()
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 10, commands.BucketType.guild)  # 10 second cooldown

    async def send_message(self, member, message):
        try:
            # Send exactly what was received (embed or regular message)
            if message.embeds:
                await member.send(embed=message.embeds[0])
            else:
                content = f"**From {message.guild.name}:**\n{message.content}"
                if message.attachments:
                    files = [await attachment.to_file() for attachment in message.attachments]
                    await member.send(content=content, files=files)
                else:
                    await member.send(content=content)
            return True
        except discord.Forbidden:
            return False
        except Exception as e:
            print(f"Error sending to {member}: {e}")
            return False

    @app_commands.command(name="set-channel", description="Set a channel for DM broadcasting")
    @app_commands.default_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if channel.id in self.broadcast_channels:
            await interaction.response.send_message("This channel is already set for broadcasting", ephemeral=True)
            return
            
        self.broadcast_channels.add(channel.id)
        await interaction.response.send_message(
            f"✅ {channel.mention} is now a broadcast channel. All messages here will be DM'd to server members.",
            ephemeral=True
        )

    @app_commands.command(name="remove-channel", description="Remove a channel from DM broadcasting")
    @app_commands.default_permissions(administrator=True)
    async def remove_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if channel.id not in self.broadcast_channels:
            await interaction.response.send_message("This channel isn't set for broadcasting", ephemeral=True)
            return
            
        self.broadcast_channels.remove(channel.id)
        await interaction.response.send_message(
            f"❌ {channel.mention} is no longer a broadcast channel.",
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        # Critical checks
        if (message.author.bot or 
            not message.guild or 
            message.channel.id not in self.broadcast_channels or
            message.channel.id in self.active_broadcasts):
            return
            
        # Check 10-second cooldown
        bucket = self.cooldown.get_bucket(message)
        if bucket.update_rate_limit():
            await message.channel.send("⚠️ Please wait 10 seconds between broadcasts", delete_after=5)
            return
            
        self.active_broadcasts.add(message.channel.id)
        
        try:
            processing_msg = await message.channel.send("🔄 Starting DM broadcast to all members...")
            
            # Get ALL members including the sender
            members = [m for m in message.guild.members if not m.bot]
            
            success = 0
            failed = 0
            total = len(members)
            
            # Send DMs with rate limiting
            for i, member in enumerate(members, 1):
                if await self.send_message(member, message):
                    success += 1
                else:
                    failed += 1
                
                # Update progress every 10 members
                if i % 10 == 0:
                    await processing_msg.edit(
                        content=f"📤 Progress: {i}/{total} members | ✅ {success} | ❌ {failed}"
                    )
                    await asyncio.sleep(0.5)  # Small delay to prevent rate limits
            
            # Final result
            result_msg = f"✅ Broadcast complete! Sent to {success} members"
            if failed > 0:
                result_msg += f" (failed for {failed} members)"
            
            await processing_msg.edit(content=result_msg)
            
        except Exception as e:
            await message.channel.send(f"❌ Broadcast failed: {str(e)}")
        finally:
            self.active_broadcasts.remove(message.channel.id)

async def setup(bot):
    await bot.add_cog(DMBroadcast(bot))
