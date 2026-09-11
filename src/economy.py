import json
import discord
import copy
import datetime
import botManager
import heapq
import secrets
import random
from discord import app_commands

econf = "data/economy.json"

econ = {}

def readEconomy():
    global econ
    with open(econf, "r", encoding="utf-8") as file:
        econ = json.load(file)

    for key in econ:
        if "cangamble" not in econ[key]:
            econ[key]["cangamble"] = True
        print(key)
    
def updateEconomy():
    data = json.dumps(econ)
    with open(econf, "w", encoding="utf-8") as file:
        file.write(data)

def transfer(acc1, acc2, amount):
    global econ

    if econ[acc1]["bal"] >= amount:
        econ[acc1]["bal"] -= amount
        econ[acc2]["bal"] += amount
        return True
    else:
        return False

async def notifypayment(recipient: discord.User, name: str, amount: int):
    embed = discord.Embed(
        title=f"{name} has payed you ${amount:,}",
        color=discord.Color.green(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    await recipient.send(embed=embed)

def evaluateBJhand(hand: list):
    # get initial amount
    acecount = 0
    value = 0
    for card in hand:
        card = card.replace("♥️","")
        card = card.replace("♣️","")
        card = card.replace("♦️","")
        card = card.replace("♠️","")
        isletter = False
        numval = 0
        try:
            numval = int(card)
        except ValueError:
            match card:
                case "A":
                    acecount+=1
                    numval=11
                case "K":
                    numval=10
                case "Q":
                    numval=10
                case "J":
                    numval=10
                case _:
                    return 22
        value+=numval

    if value > 21 and acecount > 0:
        value -= acecount*10
    return value


def blackjackTest(amount: int):
    cardpool = [
        "A♥️","2♥️","3♥️","4♥️","5♥️","6♥️","7♥️","8♥️","9♥️","10♥️","K♥️","Q♥️","J♥️", #hearts
        "A♣️","2♣️","3♣️","4♣️","5♣️","6♣️","7♣️","8♣️","9♣️","10♣️","K♣️","Q♣️","J♣️", #clubs
        "A♦️","2♦️","3♦️","4♦️","5♦️","6♦️","7♦️","8♦️","9♦️","10♦️","K♦️","Q♦️","J♦️", #diamonds
        "A♠️","2♠️","3♠️","4♠️","5♠️","6♠️","7♠️","8♠️","9♠️","10♠️","K♠️","Q♠️","J♠️" #spades
    ]

    dealer_hand = []
    player_hand = []

    # draw cards
    di = secrets.SystemRandom().randint(0, len(cardpool)-1)
    dealer_hand.append(cardpool[di])
    cardpool.pop(di)
    di = secrets.SystemRandom().randint(0, len(cardpool)-1)
    dealer_hand.append(cardpool[di])
    cardpool.pop(di)
    pi = secrets.SystemRandom().randint(0, len(cardpool)-1)
    player_hand.append(cardpool[pi])
    cardpool.pop(pi)
    pi = secrets.SystemRandom().randint(0, len(cardpool)-1)
    player_hand.append(cardpool[pi])
    cardpool.pop(pi)

    pv = evaluateBJhand(player_hand)
    dv = evaluateBJhand(dealer_hand)

    if pv == 21:
        while True:
            if dv == 18:
                break
            elif dv > 21:
                dealer_lose = True
                break
            elif dv == 21:
                break
            di = secrets.SystemRandom().randint(0, len(cardpool)-1)
            dealer_hand.append(cardpool[di])
            cardpool.pop(di)
            dv = evaluateBJhand(dealer_hand)
        print("You win!")
        dp = f"DEALER: {" ".join(dealer_hand)} ({dv})"
        pp = f"YOU: {" ".join(player_hand)} ({pv})"
        print(dp)
        print(pp)
        return

    has_busted = False
    while has_busted == False:
        dv = evaluateBJhand(dealer_hand)
        pdv = evaluateBJhand([dealer_hand[0]])
        pv = evaluateBJhand(player_hand)

        if dv == 21:
            print("You lose!")
            dp = f"DEALER: {" ".join(dealer_hand)} ({dv})"
            pp = f"YOU: {" ".join(player_hand)} ({pv})"
            print(dp)
            print(pp)
            return

        if pv > 21:
            has_busted = True
            print("You lose!")
            dp = f"DEALER: {" ".join(dealer_hand)} ({dv})"
            pp = f"YOU: {" ".join(player_hand)} ({pv})"
            print(dp)
            print(pp)
            return

        dp = f"DEALER: {dealer_hand[0]} ? ({pdv})"
        pp = f"YOU: {" ".join(player_hand)} ({pv})"
        print(dp)
        print(pp)

        decision = str(input("Hit or stand? (h/s) "))
        if decision == "h":
            pi = secrets.SystemRandom().randint(0, len(cardpool)-1)
            player_hand.append(cardpool[pi])
            cardpool.pop(pi)
        elif decision == "s" and dv < pv:
            dealer_lose = False
            while True:
                if dv == 18:
                    break
                elif dv > 21:
                    dealer_lose = True
                    break
                elif dv == 21:
                    break
                di = secrets.SystemRandom().randint(0, len(cardpool)-1)
                dealer_hand.append(cardpool[di])
                cardpool.pop(di)
                dv = evaluateBJhand(dealer_hand)
            print("You win!")
            dp = f"DEALER: {" ".join(dealer_hand)} ({dv})"
            pp = f"YOU: {" ".join(player_hand)} ({pv})"
            print(dp)
            print(pp)
            return
        else:
            print("You lose!")
            dp = f"DEALER: {" ".join(dealer_hand)} ({dv})"
            pp = f"YOU: {" ".join(player_hand)} ({pv})"
            print(dp)
            print(pp)
            return

@botManager.bot.tree.command(name="setgamble", description="Toggle whether or not a user can gamble")
@app_commands.checks.has_permissions(ban_members=True)
async def setgamble(intr: discord.Interaction, user: discord.User, cangamble: bool):
    id = user.id
    id = str(id)
    if id in econ:
        econ[id]["cangamble"] = cangamble

    await intr.response.send_message(f"Set cangamble for {user.name} to {cangamble}", ephemeral=botManager.hideRespones)

@botManager.bot.tree.command(name="userinfo", description="Get the admin panel of a user")
@app_commands.checks.has_permissions(administrator=True)
async def userinfo(intr: discord.Interaction, user: discord.User):
    id = str(user.id)
    entry = econ[id]
    embed = discord.Embed(
	title=f"User Info for {user.name}",
	description=f"ID: {id}\nBalance: ${entry["bal"]:,}\nPIN: ||{entry["pin"]}||\nCan gamble: {entry["cangamble"]}",
	color=discord.Color.green()
    )

    await intr.response.send_message(embed=embed, ephemeral=botManager.hideRespones)

@botManager.bot.tree.command(name="slots", description="Play slot machine")
async def slots(intr: discord.Interaction, amount: int):
    id = str(intr.user.id)

    emojibank = ["7️⃣", "♠️", "❤️", "⭐️", "🔔", "🍒"]
    
    matches = [
        ["7️⃣","7️⃣","7️⃣"],
        ["♠️","♠️","♠️"],
        ["❤️","❤️","❤️"],
        ["⭐️","⭐️","⭐️"],
        ["🔔","🔔","🔔"],
        ["🍒","🍒","🍒"]
    ]

    payouts = [
        15,
        15,
        10,
        7,
        5,
        5
    ]

    slot1 = random.randint(0, 5)
    slot2 = random.randint(0, 5)
    slot3 = random.randint(0, 5)

    resEmbed = discord.Embed(
        title="Slots Result",
        description=f"Spinning...\n\nYou got [{emojibank[slot1]}|{emojibank[slot2]}|{emojibank[slot3]}]\n\n",
        color=discord.Color.green()
    )

    logEmbed = discord.Embed(
        title=f"{intr.user.display_name} hit the slots",
        description=f"They got [{emojibank[slot1]}|{emojibank[slot2]}|{emojibank[slot3]}]\n\n",
        color=discord.Color.green()
    )

    final = [slot1, slot2, slot3]

    won = False

    i = 0
    for entry in matches:
        if final == matches[i]:
            mult = payouts[i]
            resEmbed.description+=f"You won ${mult*amount:,}!"
            logEmbed.description+=f"They won ${mult*amount:,}!"
            transfer("government", str(intr.user.id), mult*amount)

            won = True
        i+=1
    
    if won == False:
        logEmbed.color = discord.Color.red()
        resEmbed.color = discord.Color.red()
        resEmbed.description+=f"You lost ${amount:,}..."
        logEmbed.description+=f"They lost ${amount:,}..."
        transfer(str(intr.user.id), "government", amount)

    chan = botManager.bot.get_channel(botManager.serverData["channels"]["gambling"])
    await chan.send(embed=logEmbed)
    await intr.response.send_message(embed=resEmbed, ephemeral=botManager.hideRespones)

@botManager.bot.tree.command(name="govfine", description="Fine a user")
async def govfine(intr: discord.Interaction, user: discord.User, amount: int):
    role = intr.guild.get_role(botManager.senator_role)
    if role not in intr.user.roles:
        await intr.response.send_message("You are not a Senator.", ephemeral=botManager.hideRespones)
        return
    
    embed = discord.Embed(
        title="You have been fined by the Government!",
        description=f"Amount: ${amount:,}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    transfer(str(user.id), "government", amount)

    await user.send(embed=embed)
    await intr.response.send_message("Success!")

@botManager.bot.tree.command(name="govpay", description="Pay another user a set amount of money from the government")
async def govpay(intr: discord.Interaction, recipient: discord.User, amount: int):
    await botManager.bot.altLog(f"[govpay] {intr.user.id}")
    role = intr.guild.get_role(botManager.senator_role)
    if role not in intr.user.roles:
        await intr.response.send_message("You are not a Senator.", ephemeral=botManager.hideRespones)
        await botManager.bot.altLog("[govpay] Denied")
        return
    
    if str(recipient.id) in econ:
        res = transfer("government", str(recipient.id), amount)
        if res == True:
            await intr.response.send_message("Success!", ephemeral=botManager.hideRespones)
            await notifypayment(recipient, "The Government", amount)
        else:
            await intr.response.send_message("Failure! Insufficient funds.", ephemeral=botManager.hideRespones)
    else:
        await intr.response.send_message("Recipient does not have an account.", ephemeral=botManager.hideRespones)

@botManager.bot.tree.command(name="pay", description="Pay another user a set amount of money")
async def pay(intr: discord.Interaction, recipient: discord.User, amount: int, pin: str):
    id = intr.user.id
    otherID = recipient.id
    id = str(id)
    otherID = str(otherID)
    if id in econ:
        if otherID in econ:
            if econ[id]["pin"] == pin:
                status = transfer(id, otherID, amount)
                if status == True:
                    await intr.response.send_message("Success!", ephemeral=botManager.hideRespones)
                    await notifypayment(recipient, intr.user.name, amount)
                else:
                    await intr.response.send_message("Failure! Insufficient funds.", ephemeral=botManager.hideRespones)
        else:
            await intr.response.send_message("Recipient does not have an account.", ephemeral=botManager.hideRespones)
    else:
        await intr.response.send_message("You do not have an account. Use /register", ephemeral=botManager.hideRespones)

@botManager.bot.tree.command(name="roll", description="Wager some money")
async def roll(intr: discord.Interaction, amount: int, pin: str):
    id = str(intr.user.id)
    if id not in econ:
        await intr.response.send_message("You do not have an account.")
        return
    if econ[id]["bal"] < amount:
        await intr.response.send_message("Insufficient funds.")
        return
    if econ[id]["cangamble"] == False:
        await intr.response.send_message("You are not allowed to gamble.")
        return
    if econ[id]["pin"] != pin:
        await intr.response.send_message("Incorrect pin", ephemeral=botManager.hideRespones)
        return

    chance = random.randint(0, 100)

    resEmbed = discord.Embed(
        title="Roll Result",
        description=f"Rolling...\n\nYou got a {chance}\n\n",
        color=discord.Color.green()
    )

    logEmbed = discord.Embed(
        title=f"{intr.user.display_name} rolled the dice",
        description=f"They got a {chance}\n\n",
        color=discord.Color.green()
    )

    if chance < 50:
        resEmbed.description+=f"You win!\n+${amount:,}"
        logEmbed.description+=f"They win!\n+${amount:,}"
        transfer("government", id, amount)
    else:
        resEmbed.description+=f"You lose ${amount:,}..."
        logEmbed.description+=f"They lost ${amount:,}..."
        transfer(id, "government", amount)
    await intr.response.send_message(embed=resEmbed, ephemeral=botManager.hideRespones)

    # log roll
    chan = botManager.bot.get_channel(botManager.serverData["channels"]["gambling"])
    await chan.send(embed=logEmbed)

@botManager.bot.tree.command(name="baltop", description="See the top 10 balances")
async def baltop(intr: discord.Interaction):
    embed = discord.Embed(
        title="Top 10 balances",
        color=discord.Color.green(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        description=""
    )

    top = heapq.nlargest(10, econ.items(), key=lambda item: item[1]["bal"])
    i = 1
    for key, data in top:
        bal = econ[key]["bal"]
        if key == "government":
            embed.description = embed.description + f"{i}. {key} (${bal:,})\n"
        else:
            user = await botManager.bot.fetch_user(int(key))
            embed.description = embed.description + f"{i}. {user.display_name} (${bal:,})\n"
        i+=1
    await intr.response.send_message(embed=embed)

@botManager.bot.tree.command(name="balance", description="Get your current balance")
async def balance(intr: discord.Interaction, user: discord.User):
    id = user.id
    id = str(id)
    if id in econ:
        embed = discord.Embed(
            title="Balance Report",
            description=f"This user has ${econ[id]["bal"]:,}!",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        await intr.response.send_message(embed=embed, ephemeral=botManager.hideRespones)
    else:
        await intr.response.send_message("The targeted user does not have an account. Use /register", ephemeral=botManager.hideRespones)

@botManager.bot.tree.command(name="register", description="Register an account with our bank")
async def registerAccount(intr: discord.Interaction, pin: str):
    global econ

    await botManager.bot.altLog(f"[registercommand] Ran by {intr.user.id}")

    id = intr.user.id
    id = str(id)
    if id in econ:
        await intr.response.send_message("You already have an account! Forgot your pin? DM cammy.", ephemeral=botManager.hideRespones)
        await botManager.bot.altLog(f"[registercommand] Denied")
        return
    await botManager.bot.altLog(f"[registercommand] Approved")

    newAcc = {
        "bal":100,
        "pin":pin,
        "cangamble":True
    }

    econ[id] = copy.deepcopy(newAcc)

    await intr.response.send_message("Succesfully registered your account", ephemeral=botManager.hideRespones)
