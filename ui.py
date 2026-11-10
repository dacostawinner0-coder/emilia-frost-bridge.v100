GLACIER = 0xA9DDF2
LAVENDER = 0xC8B6F6
SUCCESS = 0x8BD3B3
ERROR = 0xF28B9B


def make_embed(title: str, description: str, color: int = GLACIER):
    import discord

    embed = discord.Embed(title=f"❄️ {title}", description=description, color=color)
    embed.set_footer(text="Emilia Frost • un serveur bien organisé, en douceur")
    return embed
