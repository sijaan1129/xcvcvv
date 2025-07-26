import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class DMBroadcast(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.broadcast_channels = set()

    @app_commands.command(name="set-channel", description="Set a channel for DM broadcasting")
    @app_commands.default_permissions(administrator=True)
    async def set_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Sets a channel for DM broadcasting"""
        if channel.id in self.broadcast_channels:
            await interaction.response.send_message(f"{channel.mention} is already a broadcast channel.", ephemeral=True)
            return
            
        self.broadcast_channels.add(channel.id)
        await interaction.response.send_message(
            f"{channel.mention} is now a DM broadcast channel. All messages here will be sent to all server members via DM.",
            ephemeral=True
        )

    @app_commands.command(name="remove-channel", description="Remove a channel from DM broadcasting")
    @app_commands.default_permissions(administrator=True)
    async def remove_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Removes a channel from DM broadcasting"""
        if channel.id not in self.broadcast_channels:
            await interaction.response.send_message(f"{channel.mention} is not a broadcast channel.", ephemeral=True)
            return
            
        self.broadcast_channels.remove(channel.id)
        await interaction.response.send_message(
            f"{channel.mention} is no longer a DM broadcast channel.",
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore if message is from a bot or not in a guild
        if message.author.bot or not message.guild:
            return
            
        # Check if message is in a broadcast channel
        if message.channel.id not in self.broadcast_channels:
            return
            
        # Don't process commands
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        # Get all members in the guild
        try:
            members = message.guild.members
        except Exception as e:
            print(f"Error getting members: {e}")
            return

        # Send initial processing message
        processing_msg = await message.channel.send("⏳ Starting to send DMs to all members...")

        success = 0
        failed = 0
        failed_users = []

        for member in members:
            # Skip bots and the message author
            if member.bot or member == message.author:
                continue
                
            try:
                # Create embed
                embed = discord.Embed(
                    description=message.content,
                    color=discord.Color.blue(),
                    timestamp=message.created_at
                )
                embed.set_author(
                    name=f"{message.author.display_name} (from {message.guild.name})", 
                    icon_url=message.author.display_avatar.url
                )
                
                # Handle attachments
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'webp')):
                            embed.set_image(url=attachment.url)
                        else:
                            embed.add_field(
                                name="Attachment",
                                value=f"[{attachment.filename}]({attachment.url})",
                                inline=False
                            )
                
                # Send DM
                await member.send(embed=embed)
                success += 1
                
                # Update status every 10 successful sends
                if success % 10 == 0:
                    await processing_msg.edit(content=f"⏳ Sent to {success} members so far...")
                
            except discord.Forbidden:
                failed += 1
                failed_users.append(str(member))
            except Exception as e:
                failed += 1
                failed_users.append(str(member))
                print(f"Error sending to {member}: {e}")

        # Create result embed
        result_embed = discord.Embed(
            title="DM Broadcast Results",
            color=discord.Color.green() if success > 0 else discord.Color.red()
        )
        result_embed.add_field(name="Successful", value=str(success), inline=True)
        result_embed.add_field(name="Failed", value=str(failed), inline=True)
        
        if failed > 0:
            failed_list = "\n".join(failed_users[:10])  # Show first 10 failed users
            if len(failed_users) > 10:
                failed_list += f"\n...and {len(failed_users)-10} more"
            result_embed.add_field(
                name="Failed Users",
                value=failed_list,
                inline=False
            )
        
        await processing_msg.edit(
            content=f"✅ DM broadcast completed!",
            embed=result_embed
        )

async def setup(bot):
    await bot.add_cog(DMBroadcast(bot))
