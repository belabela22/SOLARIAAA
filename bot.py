import discord
from discord import app_commands
from discord.ext import commands
import datetime
import aiohttp
from flask import Flask
import threading
import os

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Database to store promotion history
promotion_db = {}  # Format: {roblox_username: List[promotion_entries]}

async def get_roblox_avatar(roblox_username: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.roblox.com/users/get-by-username?username={roblox_username}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    user_id = data.get("Id")
                    if user_id:
                        async with session.get(f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=420x420&format=Png&isCircular=false") as thumb_resp:
                            if thumb_resp.status == 200:
                                thumb_data = await thumb_resp.json()
                                return thumb_data["data"][0]["imageUrl"]
    except Exception as e:
        print(f"Error fetching Roblox avatar: {e}")
    return None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.tree.command(name="promote", description="Promote a Roblox user")
@app_commands.describe(
    roblox_username="The Roblox username of the user to promote",
    old_rank="The user's current rank",
    new_rank="The new rank after promotion"
)
async def promote(interaction: discord.Interaction, roblox_username: str, old_rank: str, new_rank: str):
    await interaction.response.defer()
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    promoter = interaction.user.name
    promotion_entry = {
        "old_rank": old_rank,
        "new_rank": new_rank,
        "date": current_date,
        "promoter": promoter
    }
    if roblox_username not in promotion_db:
        promotion_db[roblox_username] = []
    promotion_db[roblox_username].append(promotion_entry)
    avatar_url = await get_roblox_avatar(roblox_username)
    embed = discord.Embed(title=f"🎉Promotion for {roblox_username}", color=discord.Color.green())
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    embed.add_field(name="Previous Rank", value=old_rank, inline=True)
    embed.add_field(name="New Rank", value=new_rank, inline=True)
    embed.add_field(name="Promoted By", value=promoter, inline=False)
    embed.add_field(name="Date", value=current_date, inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="promotions", description="View promotion history for a Roblox user")
@app_commands.describe(
    roblox_username="The Roblox username to check promotion history for"
)
async def promotions(interaction: discord.Interaction, roblox_username: str):
    await interaction.response.defer()
    avatar_url = await get_roblox_avatar(roblox_username)
    if roblox_username not in promotion_db or not promotion_db[roblox_username]:
        embed = discord.Embed(title=f"No promotions found for {roblox_username}", color=discord.Color.red())
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        await interaction.followup.send(embed=embed)
        return
    user_promotions = promotion_db[roblox_username]
    embed = discord.Embed(title=f"📜Promotion History for {roblox_username}", description=f"Total promotions: {len(user_promotions)}", color=discord.Color.blue())
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    for i, promo in enumerate(reversed(user_promotions[-5:])):
        embed.add_field(
            name=f"Promotion #{len(user_promotions) - i}",
            value=f"**From:** {promo['old_rank']}\n**To:** {promo['new_rank']}\n**By:** {promo['promoter']}\n**On:** {promo['date']}",
            inline=False
        )
    if len(user_promotions) > 5:
        embed.set_footer(text=f"Showing latest 5 of {len(user_promotions)} promotions")
    await interaction.followup.send(embed=embed)
    # Flask app to bind a port and keep Render happy
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web).start()

import os
bot.run(os.getenv("DISCORD_TOKEN"))
