# TimberLegends Discord Bot (Command Prefix Version)
# Dependencies: discord.py, pymongo, requests

import discord
from discord.ext import commands
import pymongo
import requests
from datetime import datetime, timezone, timedelta
import asyncio
import random
import os

# ------------ CONFIGURATIONS ------------
BOT_PREFIX = "!"
TOKEN = "MTM4NzQzNjY4Mzg3NTcxNzEyMA.G-Elnm.oMzCi_0RpepNuRWC5bfQ9O314nTxLVQFloXRDY"  # Nicht im Code speichern!
MONGO_URI = "mongodb+srv://timberlegends:eDMHEs9SRQVZd8Y7@timber.xl1tt8c.mongodb.net/?retryWrites=true&w=majority&appName=timber"  # Mongo-Verbindung auch aus Umgebungsvariable!

DB_NAME = "timberlegends"
COLLECTION_USERS = "users"
COLLECTION_WITHDRAWALS = "withdrawals"
WAX_API_URL = "https://wax.api.atomicassets.io/atomicassets/v1/assets"

# Template ID Mapping
TEMPLATE_MAP = {
    # Saplings
    "894060": {"type": "sapling", "rarity": "common", "rate": 0.2},
    "100001": {"type": "sapling", "rarity": "uncommon", "rate": 20},
    "100002": {"type": "sapling", "rarity": "rare", "rate": 40},
    "100003": {"type": "sapling", "rarity": "epic", "rate": 80},
    "100004": {"type": "sapling", "rarity": "legendary", "rate": 160},
    "100005": {"type": "sapling", "rarity": "mythic", "rate": 320},

    # Trees
    "200000": {"type": "tree", "rarity": "common", "rate": 30},
    "200001": {"type": "tree", "rarity": "uncommon", "rate": 60},
    "200002": {"type": "tree", "rarity": "rare", "rate": 120},
    "200003": {"type": "tree", "rarity": "epic", "rate": 240},
    "200004": {"type": "tree", "rarity": "legendary", "rate": 480},
    "200005": {"type": "tree", "rarity": "mythic", "rate": 960},

    # Lumberjacks
    "894059": {"type": "lumberjack", "rarity": "common", "bonus": 0.10},
    "300001": {"type": "lumberjack", "rarity": "uncommon", "bonus": 0.20},
    "300002": {"type": "lumberjack", "rarity": "rare", "bonus": 0.30},
    "300003": {"type": "lumberjack", "rarity": "epic", "bonus": 0.40},
    "300004": {"type": "lumberjack", "rarity": "legendary", "bonus": 0.50},
    "300005": {"type": "lumberjack", "rarity": "mythic", "bonus": 0.60},

    # Tools
    "894061": {"type": "tool", "rarity": "common", "bonus": 0.10},
    "400001": {"type": "tool", "rarity": "uncommon", "bonus": 0.20},
    "400002": {"type": "tool", "rarity": "rare", "bonus": 0.30},
    "400003": {"type": "tool", "rarity": "epic", "bonus": 0.40},
    "400004": {"type": "tool", "rarity": "legendary", "bonus": 0.50},
    "400005": {"type": "tool", "rarity": "mythic", "bonus": 0.60},
}

BONUS_YIELD = {
    "common": 0.10,
    "uncommon": 0.20,
    "rare": 0.30,
    "epic": 0.40,
    "legendary": 0.50,
    "mythic": 0.60
}

# ------------ INIT BOT & DB ------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
users_col = db[COLLECTION_USERS]
withdrawals_col = db[COLLECTION_WITHDRAWALS]

# ------------ HELPER FUNCTIONS ------------
def get_nfts(wallet):
    params = {"owner": wallet, "collection_name": "timberlegend", "limit": 1000}
    try:
        r = requests.get(WAX_API_URL, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception:
        return []

def calculate_production(nfts):
    total = 0
    best_lumberjack_bonus = 0
    best_lumberjack_rarity = None
    best_tool_bonus = 0
    best_tool_rarity = None

    rarity_order = ["common", "uncommon", "rare", "epic", "legendary", "mythic"]

    for nft in nfts:
        template_id = str(nft.get("template", {}).get("template_id"))
        if template_id in TEMPLATE_MAP:
            data = TEMPLATE_MAP[template_id]
            if data["type"] in ["sapling", "tree"]:
                total += data["rate"]
                print(f"Added {data['rate']} TIMBER from {data['type']} (template {template_id})")
            elif data["type"] == "lumberjack":
                current_rarity = data["rarity"].strip().lower()
                if best_lumberjack_rarity is None or rarity_order.index(current_rarity) > rarity_order.index(best_lumberjack_rarity):
                    best_lumberjack_rarity = current_rarity
                    best_lumberjack_bonus = data["bonus"]
                print(f"Lumberjack found with rarity '{current_rarity}' and bonus {data['bonus']}")
            elif data["type"] == "tool":
                current_rarity = data["rarity"].strip().lower()
                if best_tool_rarity is None or rarity_order.index(current_rarity) > rarity_order.index(best_tool_rarity):
                    best_tool_rarity = current_rarity
                    best_tool_bonus = data["bonus"]
                print(f"Tool found with rarity '{current_rarity}' and bonus {data['bonus']}")

    print(f"Lumberjack rarity: '{best_lumberjack_rarity}'")
    print(f"Tool rarity: '{best_tool_rarity}'")
    print("Rarities equal?", best_lumberjack_rarity == best_tool_rarity)

    if best_lumberjack_rarity and best_tool_rarity and best_lumberjack_rarity == best_tool_rarity:
        print(f"Applying bonus of {best_lumberjack_bonus*100}% for matching rarity '{best_lumberjack_rarity}'")
        total += total * best_lumberjack_bonus

    print(f"Total production calculated: {total}")
    return total



# ------------ BOT EVENTS & COMMANDS ------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def register(ctx, wallet):
    users_col.update_one(
        {"_id": str(ctx.author.id)},
        {"$set": {"wallet": wallet, "timber": 0, "last_claim": None}},
        upsert=True
    )
    await ctx.send(f"Wallet `{wallet}` registered for {ctx.author.mention}.")

@bot.command()
async def claim(ctx):
    user_id = str(ctx.author.id)
    user = users_col.find_one({"_id": user_id})
    if not user:
        await ctx.send("You must register first using !register <wallet>.")
        return

    now = datetime.now(timezone.utc)
    last_claim = user.get("last_claim")
    if last_claim:
        if last_claim.tzinfo is None:
            last_claim = last_claim.replace(tzinfo=timezone.utc)
        if (now - last_claim).days < 1:
            await ctx.send("You already claimed your TIMBER today.")
            return

    wallet = user["wallet"]
    nfts = get_nfts(wallet)
    amount = calculate_production(nfts)  # float mit Nachkommastellen

    booster_multiplier = user.get("booster_multiplier", 1.0)
    booster_expiry = user.get("booster_expiry")

    if booster_expiry and booster_multiplier > 1.0:
        if booster_expiry.tzinfo is None:
            booster_expiry = booster_expiry.replace(tzinfo=timezone.utc)
        if booster_expiry > now:
            amount *= booster_multiplier
            # Booster nach Anwendung entfernen (einmalig)
            users_col.update_one({"_id": user_id}, {"$unset": {"booster_multiplier": "", "booster_expiry": ""}})
        else:
            users_col.update_one({"_id": user_id}, {"$unset": {"booster_multiplier": "", "booster_expiry": ""}})

    amount = round(amount, 2)  # 2 Dezimalstellen

    users_col.update_one(
        {"_id": user_id},
        {"$inc": {"timber": amount}, "$set": {"last_claim": now}}
    )

    await ctx.send(f"You claimed **{amount} TIMBER** today!")


@bot.command()
async def withdraw(ctx, amount: float):
    user_id = str(ctx.author.id)
    user_data = users_col.find_one({"_id": user_id})

    if not user_data:
        await ctx.send("You don't have a TIMBER account yet. Please register first.")
        return

    current_timber = user_data.get("timber", 0.0)
    if amount <= 0:
        await ctx.send("The withdrawal amount must be greater than 0.")
        return

    if current_timber < amount:
        await ctx.send(f"You don't have enough TIMBER. Current balance: {round(current_timber, 2)}")
        return

    users_col.update_one(
        {"_id": user_id},
        {"$inc": {"timber": -amount}}
    )
    await ctx.send(f"{round(amount, 2)} TIMBER has been marked for withdrawal.")

@bot.command()
@commands.has_permissions(administrator=True)
async def pending_withdrawals(ctx):
    pending = list(withdrawals_col.find())
    if not pending:
        await ctx.send("No pending withdrawals.")
        return
    message = "**Pending Withdrawals:**\n"
    for w in pending:
        timestamp = w["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        message += f"Wallet: `{w['wallet']}` | Amount: {w['amount']} | Date: {timestamp}\n"
    await ctx.send(message)

@bot.command()
async def leaderboard(ctx):
    top = list(users_col.find().sort("timber", -1).limit(25))
    msg = "**Top TIMBER Earners:**\n"
    for i, user in enumerate(top, 1):
        try:
            discord_user = await bot.fetch_user(int(user["_id"]))
            msg += f"{i}. {discord_user.name}: {user['timber']} TIMBER\n"
        except:
            continue
    await ctx.send(msg)

@bot.command()
async def farmstatus(ctx):
    user_id = str(ctx.author.id)
    user = users_col.find_one({"_id": user_id})
    if not user:
        await ctx.send("You must register first using !register <wallet>.")
        return

    wallet = user["wallet"]
    nfts = get_nfts(wallet)
    production = round(calculate_production(nfts), 2)  # 2 Dezimalstellen

    booster_multiplier = user.get("booster_multiplier", 1.0)
    booster_expiry = user.get("booster_expiry")
    now = datetime.now(timezone.utc)

    booster_info = "No booster active."
    if booster_expiry and booster_multiplier > 1.0:
        if booster_expiry.tzinfo is None:
            booster_expiry = booster_expiry.replace(tzinfo=timezone.utc)
        if booster_expiry > now:
            time_left = booster_expiry - now
            booster_info = (
                f"🔋 Booster active! +{int((booster_multiplier - 1) * 100)}% "
                f"for {str(time_left).split('.')[0]} left."
            )
        else:
            booster_info = "🔋 Booster expired."

    await ctx.send(
        f"🌲 Wallet: `{wallet}`\n"
        f"📈 Daily Production: **{production} TIMBER**\n"
        f"{booster_info}"
    )


@bot.command()
async def spin(ctx):
    user_id = str(ctx.author.id)
    user = users_col.find_one({"_id": user_id})
    if not user:
        await ctx.send("You have to register first with !register <wallet>.")
        return

    timber_balance = user.get("timber", 0)
    cost = 75
    if timber_balance < cost:
        await ctx.send(f"You need {cost} TIMBER to spin the wheel.")
        return

    # Neue Wahrscheinlichkeiten: Mehr Nieten, kleine Gewinne, 1 Booster
    outcomes = [
        ("nothing", None),
        ("nothing", None),
        ("25 TIMBER", 25),
        ("50 TIMBER", 50),
        ("10 TIMBER", 10),
        ("100 TIMBER", 100),
        ("nothing", None),
        ("DOUBLE YIELD (next claim only)", "x2_boost")
    ]
    result = random.choice(outcomes)
    reward_text, reward_value = result

    users_col.update_one({"_id": user_id}, {"$inc": {"timber": -cost}})

    if reward_value is None:
        await ctx.send("🎯 You got nothing. Better luck next time!")
    elif reward_value == "x2_boost":
        expiry = datetime.now(timezone.utc) + timedelta(days=1)
        users_col.update_one({"_id": user_id}, {
            "$set": {
                "booster_multiplier": 2.0,  # 100% boost = x2
                "booster_expiry": expiry
            }
        })
        await ctx.send(
            f"💥 You won a **100% Yield Boost** (x2) for your **next claim**! 🎉\n"
            f"Active until `{expiry.strftime('%Y-%m-%d %H:%M UTC')}`."
        )
    else:
        users_col.update_one({"_id": user_id}, {"$inc": {"timber": float(reward_value)}})
        await ctx.send(f"🎉 You won **{reward_value} TIMBER**!")
        
        

@bot.command()
async def inventory(ctx):
    user_id = str(ctx.author.id)
    user = users_col.find_one({"_id": user_id})
    if not user:
        await ctx.send("You are not registered yet. Use !register <wallet>.")
        return

    wallet = user["wallet"]
    timber = user.get("timber", 0)
    nfts = get_nfts(wallet)

    if not nfts:
        await ctx.send(f"Your wallet `{wallet}` does not seem to have any NFTs or there was an error.")
        return

    counts = {"sapling": 0, "tree": 0, "lumberjack": 0, "tool": 0}
    for nft in nfts:
        tid = nft.get("template", {}).get("template_id")
        if tid in TEMPLATE_MAP:
            nft_type = TEMPLATE_MAP[tid]["type"]
            counts[nft_type] += 1

    msg = (
        f"Inventory for `{wallet}`:\n"
        f"TIMBER: **{round(timber, 2)}**\n"
        f"Saplings: {counts['sapling']}\n"
        f"Trees: {counts['tree']}\n"
        f"Lumberjacks: {counts['lumberjack']}\n"
        f"Tools: {counts['tool']}\n"
    )
    await ctx.send(msg)



@bot.command(name="timberhelp")
async def timberhelp(ctx):
    help_text = (
        "**TimberLegends Bot Commands:**\n\n"
        "!register <wallet> → Link your WAX wallet.\n"
        "!claim → Daily TIMBER claim.\n"
        "!inventory → Show your TIMBER balance and NFTs.\n"
        "!withdraw <amount> → Request withdrawal.\n"
        "!leaderboard → Show top 25 players.\n"
        "!farmstatus → See your NFT farm stats.\n"
        "!spin → Gamble for boosts/TIMBER.\n"
        "!timberhelp → Show this help message.\n"
    )
    msg = await ctx.send(help_text)
    await asyncio.sleep(120)
    await msg.delete()
    try:
        await ctx.message.delete()
    except:
        pass

# ------------ RUN BOT ------------
if __name__ == "__main__":
    bot.run(TOKEN)




