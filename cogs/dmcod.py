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
        # Ignore messages from bots and messages not in guilds
        if message.author.bot or not message.guild or message.channel.id not in self.broadcast_channels:
            return
            
        # Don't process commands
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return
            
        # Get all members in the guild
        members = message.guild.members
        
        # Send DM to each member
        for member in members:
            if member.bot or member == message.author:
                continue
                
            try:
                embed = discord.Embed(
                    description=message.content,
                    color=discord.Color.blue()
                )
                embed.set_author(name=f"{message.author.display_name} (from {message.guild.name})", 
                               icon_url=message.author.display_avatar.url)
                
                # Attach any attachments
                if message.attachments:
                    embed.set_image(url=message.attachments[0].url)
                    
                await member.send(embed=embed)
            except discord.Forbidden:
                # Can't send DM to this user
                pass
            except Exception as e:
                print(f"Failed to send DM to {member}: {e}")

async def setup(bot):
    await bot.add_cog(DMBroadcast(bot))
