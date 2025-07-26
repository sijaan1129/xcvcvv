import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class DMBroadcast(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.broadcast_channels = set()

    async def send_dm(self, member, message):
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
        if message.author.bot or not message.guild:
            return
            
        if message.channel.id not in self.broadcast_channels:
            return
            
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        processing_msg = await message.channel.send("⏳ Starting DM broadcast to all members...")

        success = 0
        failed = 0
        members = [m for m in message.guild.members if not m.bot and m != message.author]

        batch_size = 10
        delay = 1.2  # seconds between batches

        for i in range(0, len(members), batch_size):
            batch = members[i:i + batch_size]
            tasks = [self.send_dm(member, message) for member in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if result is True:
                    success += 1
                else:
                    failed += 1
            
            await processing_msg.edit(
                content=f"⏳ Progress: {success+failed}/{len(members)} members processed "
                       f"({success} succeeded, {failed} failed)"
            )
            await asyncio.sleep(delay)

        result_embed = discord.Embed(
            title="Broadcast Complete",
            description=f"Message sent to {success} members successfully.",
            color=discord.Color.green() if success > 0 else discord.Color.red()
        )
        result_embed.add_field(name="Successful", value=str(success))
        result_embed.add_field(name="Failed", value=str(failed))
        
        await processing_msg.edit(
            content=f"✅ DM broadcast completed!",
            embed=result_embed
        )

async def setup(bot):
    await bot.add_cog(DMBroadcast(bot))
