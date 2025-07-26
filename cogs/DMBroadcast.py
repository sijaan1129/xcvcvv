import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class DMBroadcast(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.broadcast_channels = set()
        self.active_broadcasts = set()
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 300, commands.BucketType.guild)

    async def send_dm(self, member, message):
        try:
            embed = discord.Embed(
                description=message.content,
                color=discord.Color.blue(),
                timestamp=message.created_at
            )
            embed.set_author(
                name=f"Broadcast from {message.guild.name}", 
                icon_url=message.guild.icon.url if message.guild.icon else None
            )
            
            if message.attachments:
                attachment = message.attachments[0]
                if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'webp')):
                    embed.set_image(url=attachment.url)
                else:
                    embed.add_field(
                        name="Attachment",
                        value=f"[{attachment.filename}]({attachment.url})",
                        inline=False
                    )
            
            await member.send(embed=embed)
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
            
        # Check cooldown
        bucket = self.cooldown.get_bucket(message)
        if bucket.update_rate_limit():
            await message.channel.send("⚠️ Broadcasts are on cooldown (5 minutes between broadcasts)")
            return
            
        self.active_broadcasts.add(message.channel.id)
        
        try:
            processing_msg = await message.channel.send("🔄 Starting DM broadcast to all members...")
            
            # Get all non-bot members
            members = [m for m in message.guild.members if not m.bot and m != message.author]
            
            success = 0
            failed = 0
            total = len(members)
            
            # Send DMs with rate limiting
            for i, member in enumerate(members, 1):
                if await self.send_dm(member, message):
                    success += 1
                else:
                    failed += 1
                
                # Update progress every 10 members
                if i % 10 == 0:
                    await processing_msg.edit(
                        content=f"📤 Progress: {i}/{total} members | ✅ {success} | ❌ {failed}"
                    )
                    await asyncio.sleep(1)  # Rate limit protection
            
            # Final result
            result_embed = discord.Embed(
                title="Broadcast Complete",
                description=f"Message sent to {success} members",
                color=discord.Color.green()
            )
            result_embed.add_field(name="Successful", value=str(success))
            result_embed.add_field(name="Failed", value=str(failed))
            
            if failed > 0:
                result_embed.color = discord.Color.orange()
                result_embed.description += f" (failed for {failed} members)"
            
            await processing_msg.edit(
                content=f"✅ Broadcast completed in {message.channel.mention}",
                embed=result_embed
            )
            
        except Exception as e:
            await message.channel.send(f"❌ Broadcast failed: {str(e)}")
        finally:
            self.active_broadcasts.remove(message.channel.id)

async def setup(bot):
    await bot.add_cog(DMBroadcast(bot))
