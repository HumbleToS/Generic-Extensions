
from __future__ import annotations

import logging

import discord
from discord.ext import commands

EMBED_COLOR = discord.Color.blue()

# This list is subject to change by discord at any time. You should verify it's accurate on your own.
# Remove any ones you don't want to check for.
GUILD_FEATURES_DICT = {
    "ANIMATED_BANNER": "Animated Banner",
    "ANIMATED_ICON": "Animated Icon",
    "BANNER": "Custom Banner",
    "COMMERCE": "Commerce",
    "COMMUNITY": "Community Server",
    "DISCOVERABLE": "Discoverable",
    "FEATURABLE": "Featurable",
    "INVITE_SPLASH": "Invite Splash",
    "MARKETPLACES_CONNECTION_ROLES": "Market Places Connection Roles"   ,
    "MEMBER_VERIFICATION_GATE_ENABLED": "Verification Required",
    "MONETIZATION_ENABLED": "Monetization Enabled",
    "MORE_EMOJI": "More Emojis",
    "MORE_STICKER": "More Stickers",
    "NEWS": "News",
    "PARTNERED": "Partnered",
    "PRIVATE_THREADS": "Private Threads",
    "PREVIEW_ENABLED": "Preview Enabled",
    "ROLE_ICONS": "Roles Icons",
    "TICKETED_EVENTS_ENABLED": "Ticketed Events",
    "VANITY_URL": "Custom Invite Link",
    "VERIFIED": "Verified",
    "VIP_REGIONS": "VIP Regions",
    "WELCOME_SCREEN_ENABLED": "Welcome Screen Enabled",
    "ENABLED_DISCOVERABLE_BEFORE": "Has Been Discoverable",
    "AUTO_MODERATION": "Auto Mod",
    "MEMBER_PROFILES": "Member Profiles",
    "NEW_THREAD_PERMISSIONS": "New Thread Permissions",
    "THREE_DAY_THREAD_ARCHIVE": "Three Day Thread Archive",
    "SEVEN_DAY_THREAD_ARCHIVE": "Seven Day Thread Archive",
    "APPLICATION_COMMAND_PERMISSIONS_V2": "New Integrations Permissions",
    "GUILD_ONBOARDING_HAS_PROMPTS": "Onboarding Prompts"
}

GUILD_FEATURES_SET = set(GUILD_FEATURES_DICT.keys())

_logger = logging.getLogger(__name__)

class InformationCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def serverinfo(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        guild_features = set(guild.features)
        features_have = GUILD_FEATURES_SET & guild_features
        features_not_have = GUILD_FEATURES_SET - guild_features
        num_members = guild.member_count
        num_bots = sum(mem.bot for mem in guild.members)
        num_channels = len(guild.channels)
        num_text_channels = len(guild.text_channels)
        num_voice_channels = len(guild.voice_channels)
        emoji_limit = guild.emoji_limit
        num_emojis = len(guild.emojis)
        num_animated_emojis = sum(emoji.animated for emoji in guild.emojis)
        sticker_limit = guild.sticker_limit
        num_stickers = len(guild.stickers)
        num_roles = len(guild.roles)
        num_boosts = guild.premium_subscription_count

        embed = discord.Embed(title=guild.name, color=EMBED_COLOR)

        features_str = ""
        for item in features_have:
            features_str += f"\U00002705 {GUILD_FEATURES_DICT[item]}\n"
        for item in features_not_have:
            features_str += f"\U0000274c {GUILD_FEATURES_DICT[item]}\n"

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.set_footer(text="Created")
        embed.timestamp = guild.created_at

        fields = { # field_name: value
            "ID": (f"{guild.id}", True),
            "Owner": (f"{guild.owner.mention}", True),
            "Members": (f"{num_members:,} ({num_bots:,} Bots", False),
            f"Channel Count ({num_channels:,})": (f"Text: {num_text_channels:,}\nVoice: {num_voice_channels:,}", True),
            "Emojis": (f"{num_emojis:,}/{emoji_limit:,}\nAnimated Emojis: {num_animated_emojis:,}", True),
            "Stickers": (f"{num_stickers}/{sticker_limit}", False),
            "Role Count": (f"{num_roles:,}", True),
            "Boost Count": (f"{num_boosts:,}", True),
            "Features": (features_str, False)
        }

        for name, value in fields.items():
            embed.add_field(name=name, value=value[0], inline=value[1])

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def userinfo(self, ctx: commands.Context, user: discord.Member = None) -> None:
        user = user or ctx.author
        pass

    @commands.command()
    @commands.guild_only()
    async def roleinfo(self, ctx: commands.Context, role: discord.Role = None) -> None:
        pass

async def setup(bot: commands.Bot):
    _logger.info("Loading cog InformationCommands")
    await bot.add_cog(InformationCommands(bot))

async def teardown(_: commands.Bot):
    _logger.info("Unloading cog InformationCommands")