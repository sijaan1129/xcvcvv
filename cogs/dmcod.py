import discord
from discord.ext import commands
from discord import app_commands

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
        await interaction.response.send_message(f"{channel.mention} is now a DM broadcast channel. All messages here will be sent to all server members via DM.", ephemeral=True)

    @app_commands.command(name="remove-channel", description="Remove a channel from DM broadcasting")
    @app_commands.default_permissions(administrator=True)
    async def remove_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Removes a channel from DM broadcasting"""
        if channel.id not in self.broadcast_channels:
            await interaction.response.send_message(f"{channel.mention} is not a broadcast channel.", ephemeral=True)
            return
            
        self.broadcast_channels.remove(channel.id)
        await interaction.response.send_message(f"{channel.mention} is no longer a DM broadcast channel.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
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

        # Fetch all members (this ensures we have up-to-date member list)
        try:
            members = [member async for member in message.guild.fetch_members()]
        except:
            members = message.guild.members

        # Send DM to each member
        success = 0
        failed = 0
        processing_message = await message.channel.send("📤 Sending messages to all members...")

        for member in members:
            if member.bot or member == message.author:
                continue
                
            try:
                embed = discord.Embed(
                    description=message.content,
                    color=discord.Color.blue(),
                    timestamp=message.created_at
                )
                embed.set_author(
                    name=f"{message.author.display_name} (from {message.guild.name})", 
                    icon_url=message.author.display_avatar.url
                )
                
                # Add any attachments
                if message.attachments:
                    attachment = message.attachments[0]
                    if attachment.url.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'webp')):
                        embed.set_image(url=attachment.url)
                    else:
                        embed.add_field(name="Attachment", value=f"[{attachment.filename}]({attachment.url})", inline=False)
                
                await member.send(embed=embed)
                success += 1
            except discord.Forbidden:
                failed += 1  # User has DMs disabled
            except Exception as e:
                failed += 1
                print(f"Failed to send DM to {member}: {e}")

        # Update with results
        await processing_message.edit(content=f"✅ Messages sent successfully to {success} members. Failed to send to {failed} members.")

async def setup(bot):
    await bot.add_cog(DMBroadcast(bot))
