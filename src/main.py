from discord import app_commands
import discord
import datetime
import time
import re
import requests
import economy
import botManager
import signal
import sys
import json
import heapq
import admin
from discord.ext import commands, tasks
from bs4 import BeautifulSoup

electionf = "data/elections.json"
votingf = "data/voting.json"
serverf = "data/server.json"
keyf = "data/.env"
adminf = "data/admin.json"

if(len(sys.argv) > 1):
    if(sys.argv[1] == "debug" or sys.argv[1] == "d"):
        electionf = "debug/elections.json"
        votingf = "debug/voting.json"
        serverf = "debug/server.json"
        keyf = "debug/.env"
        adminf = "debug/admin.json"
        economy.econf = "debug/economy.json"
        botManager.hideRespones = False

async def log(message: str):
    guild = botManager.bot.get_guild(botManager.serverData["guild_id"])
    logc = guild.get_channel(botManager.serverData["channels"]["logs"])

    await logc.send(f"(<t:{int(time.time())}:f>) {message}")

async def notify_senator(embed: discord.Embed):
    guild = botManager.bot.get_guild(botManager.serverData["guild_id"])

    role = guild.get_role(botManager.serverData["roles"]["senator"])

    embed.description+="\n\nREMINDER: YOU MUST VOTE WITHIN THE SERVER IN #SENATE, YOU CAN NOT VOTE HERE"

    for member in role.members:
        await log(f"[notify_senator] Notified {member.display_name} ({member.name})")
        await member.send(embed=embed)

async def getdocstitle(url: str):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        return "Invalid Google Docs URL"
    
    doc_id = match.group(1)
    view_url = f"https://docs.google.com/document/d/{doc_id}/view"

    try:
        response = requests.get(view_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            raw_title = soup.title.string if soup.title else ""
            clean = re.sub(r"\s*-\s*Google\s+Docs$", "", raw_title, flags=re.IGNORECASE)

            return clean.strip()
        else:
            await log(f"[getdocstitle] Could not extract docs title, response code: {response.code}")
            return ""
    except Exception as e:
        await log(f"[getdocstitle] Could not extract docs title: {str(e)}")
        return ""

@tasks.loop(minutes=1.0)
async def checkExpiration():
    for id, data in botManager.electionData.items():
        if data["expired"] == False and (datetime.datetime.now().timestamp() - data["timestamp"] >= (data["duration"] * 3600)):
            # reply to the message saying it's now expired
            embed = discord.Embed(
                title=f"The proposal of {data["type"]} has ENDED",
                description=f"ID: {id}\n\nResults:\n",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            results = ""
            if data["reactionary"] == True:
                results+=f"AYE: {data["aye"]}\n"
                results+=f"NAY: {data["nay"]}\n"
                results+=f"ABS: {data["abs"]}\n"
                # determine outcome
                if data["aye"] >= data["neededAye"]:
                    results+="The movement has PASSED"
                else:
                    results+="The movement has FAILED"
            else:
                people = data["userPolls"]
                top = heapq.nlargest(9, people.items(), key=lambda item: item[1])
                i = 1
                for key, votes in top:
                    if key == "government":
                        embed.description = embed.description + f"{i}. {key} | {votes} ({(votes/data["totalUsers"])*100}%)\n"
                    else:
                        user = await botManager.bot.fetch_user(int(key))
                        embed.description = embed.description + f"{i}. {user.display_name} {votes}\n"
                    i+=1
            embed.description+=results
            data["expired"] = True

            log = botManager.bot.get_channel(botManager.serverData["channels"]["logs"])
            sen = botManager.bot.get_channel(botManager.serverData["channels"]["senate"])
            await log.send(embed=embed)
            if data["type"] != "a test":
                await sen.send(embed=embed)

@botManager.bot.tree.command(name="testdocstitle", description="Tests the docs title extraction")
async def testdocstitle(intr: discord.Interaction, url: str):
    await log(f"[testdocstitle] {intr.user.display_name} ({intr.user.name}) ran this command")
    role = intr.guild.get_role(botManager.serverData["roles"]["senator"])
    if role not in intr.user.roles:
        await intr.response.send_message("You are not a Senator.", ephemeral=botManager.hideRespones)
        await log("[testdocstitle] Denied")
        return
    await log("[testdocstitle] Approved")
    title = await getdocstitle(url)
    await log(f"[testdocstitle] Result: {title}")
    await intr.response.send_message("Check bot logs", ephemeral=botManager.hideRespones)

@botManager.bot.tree.command(name="testnotify", description="Tests the notify_senator command")
async def testnotify(intr: discord.Interaction):
    await log(f"[testnotify] {intr.user.display_name} ({intr.user.name}) ran this command")
    role = intr.guild.get_role(botManager.serverData["roles"]["senator"])
    if role not in intr.user.roles:
        await intr.response.send_message("You are not a Senator.", ephemeral=botManager.hideRespones)
        await log("[testnotify] Denied")
        return
    
    await log("[testnotify] Approved")
    
    embed = discord.Embed(
        title="This is a test DM",
        description="If you are receiving this, the test has succeeded.",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    await notify_senator(embed)

    await intr.response.send_message("Please check bot logs for results.", ephemeral=botManager.hideRespones)

@botManager.bot.tree.command(name="generalvote", description="Starts a general vote")
async def generalvote(intr: discord.Interaction, description: str, notify: bool):
    await log(f"[generalvote] {intr.user.display_name} ({intr.user.name}) ran this command")
    role = intr.guild.get_role(botManager.serverData["roles"]["senator"])
    if role not in intr.user.roles:
        await intr.response.send_message("You are not a Senator.", ephemeral=botManager.hideRespones)
        await log("[generalvote] Denied")
        return
    await log("[generalvote] Approved")

    embed = discord.Embed(
        title="A GENERAL VOTE has been started",
        description=description,
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.description+=f"\n\nVOTING\n👍 - AYE\n✋ - ABSTAIN (No vote)\n👎 - NAY\n\nAs a Senator, it is your duty to do what is right for Hippokratia"

    embed.set_footer(
        text=f"Initiated by {intr.user.display_name}",
        icon_url=intr.user.display_avatar.url
    )

    await intr.response.send_message("Created!", ephemeral=botManager.hideRespones)

    senChan = botManager.bot.get_channel(botManager.electionData["channels"]["senate"])
    if senChan:
        msg = await senChan.send(embed=embed)
        if notify:
            await senChan.send(f"<@&{botManager.serverData["roles"]["senator"]}>")
            await notify_senator(embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("✋")
        await msg.add_reaction("👎")
        registerElection(msg.id, "a general vote", True, 4)
    else:
        print("Could not fetch senate channel")

    await log(f"[generalvote] Began a general vote.\ndescription={description}\nnotify={notify}")

@botManager.bot.tree.command(name="testvote", description="Starts a testing vote")
async def testvote(intr: discord.Interaction, description: str, notify: bool, duration: int):
    await log(f"[testvote] {intr.user.display_name} ({intr.user.name}) ran this command")
    role = intr.guild.get_role(botManager.serverData["roles"]["senator"])
    if role not in intr.user.roles:
        await intr.response.send_message("You are not a Senator.", ephemeral=botManager.hideRespones)
        await log("[testvote] Denied")
        return
    await log("[testvote] Approved")

    embed = discord.Embed(
        title="A GENERAL VOTE has been started",
        description=description,
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.description+=f"\n\nVOTING\n👍 - AYE\n✋ - ABSTAIN (No vote)\n👎 - NAY\n\nAs a Senator, it is your duty to do what is right for Hippokratia"

    embed.set_footer(
        text=f"Initiated by {intr.user.display_name}",
        icon_url=intr.user.display_avatar.url
    )

    await intr.response.send_message("Created!", ephemeral=botManager.hideRespones)

    senChan = botManager.bot.get_channel(botManager.debug_channel)
    if senChan:
        msg = await senChan.send(embed=embed)
        if notify:
            await senChan.send(f"<@&{botManager.serverData["roles"]["senator"]}>")
            await notify_senator(embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("✋")
        await msg.add_reaction("👎")
        registerElection(msg.id, "a test", True, 1, duration)
    else:
        print("Could not fetch senate channel")

    await log(f"[generalvote] Began a general vote.\ndescription={description}\nnotify={notify}")

@botManager.bot.tree.command(name="ballot", description="Get the ballot of an election")
async def ballot(intr: discord.Interaction, message: str):
    data = botManager.electionData[str(message)]
    embed = discord.Embed(
        title=f"Ballot for election ID {message}",
        description="",
        color=discord.Color.blue()
    )
    if data["reactionary"] == True:
        embed.description += f"AYE: {data["aye"]}\nNAY: {data["nay"]}\nABS: {data["abs"]}"
    else:
        people = data["userPolls"]
        top = heapq.nlargest(9, people.items(), key=lambda item: item[1])
        i = 1
        for key, votes in top:
            user = await botManager.bot.fetch_user(int(key))
            embed.description = embed.description + f"{i}. {user.display_name} | {votes} ({(votes/data["totalUsers"])*100}%)\n"
            i+=1
    
    await intr.response.send_message(embed=embed, ephemeral=botManager.hideRespones)

@botManager.bot.tree.command(name="proposebill", description="Proposes a bill and starts a vote")
async def proposebill(intr: discord.Interaction, description: str, url: str, notify: bool):
    role = intr.guild.get_role(botManager.serverData["roles"]["senator"])
    await log(f"[proposebill] {intr.user.display_name} ({intr.user.name}) ran this command")
    if role not in intr.user.roles:
        await intr.response.send_message("You are not a Senator.", ephemeral=botManager.hideRespones)
        await log("[proposebill] Denied")
        return
    
    title = await getdocstitle(url)
    if title == "Invalid Google Docs URL":
        await log(f"[proposebill] Unable to create vote, improper URL attached ({url})")
        await intr.response.send_message("Unable to create vote, improper URL attached")
        return

    await log("[proposebill] Approved")

    embed = discord.Embed(
        title="A BILL has been PROPOSED",
        description="**"+title+"**\n\n"+description,
        color=discord.Color.blue(),
        url=url,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.description+=f"\n\n[LINK]({url}) to the proposition\n\nVOTING\n👍 - AYE\n✋ - ABSTAIN (No vote)\n👎 - NAY\n\nAs a Senator, it is your duty to do what is right for Hippokratia, it is advised to read the attached document in it's entirety.\n\nFOUR Senators must vote AYE for this bill to pass\nThis vote will end after 24 hours."

    embed.set_footer(
        text=f"Initiated by {intr.user.display_name}",
        icon_url=intr.user.display_avatar.url
    )

    await intr.response.send_message("Created!", ephemeral=botManager.hideRespones)

    senChan = botManager.bot.get_channel(botManager.electionData["channels"]["senate"])
    if senChan:
        msg = await senChan.send(embed=embed)
        if notify:
            await senChan.send(f"<@&{botManager.serverData["roles"]["senator"]}>")
            await notify_senator(embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("✋")
        await msg.add_reaction("👎")
        registerElection(msg.id, "a bill", True, 4, 24)
    else:
        print("Could not fetch senate channel")

    await log(f"[proposebill] Proposed a bill vote.\burl={url}\nnotify={notify}")

@botManager.bot.tree.command(name="proposeamendment", description="Proposes an amendment and starts a vote")
async def proposeamendment(intr: discord.Interaction, description: str, url: str, notify: bool):
    await log(f"[proposeamendment] {intr.user.display_name} ({intr.user.name}) ran this command")
    role = intr.guild.get_role(botManager.serverData["roles"]["senator"])
    if role not in intr.user.roles:
        await intr.response.send_message("You are not a Senator.", ephemeral=botManager.hideRespones)
        await log("[proposeamendment] Denied")
        return
    title = await getdocstitle(url)
    if title == "Invalid Google Docs URL":
        await log(f"[proposebill] Unable to create vote, improper URL attached ({url})")
        await intr.response.send_message("Unable to create vote, improper URL attached")
        return

    await log("[proposeamendment] Approved")

    embed = discord.Embed(
        title="AN AMENDMENT has been proposed",
        description="**"+title+"**\n\n"+description,
        color=discord.Color.blue(),
        url=url,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    embed.description+=f"\n\n[LINK]({url}) to the proposition\n\nVOTING\n👍 - AYE\n✋ - ABSTAIN (No vote)\n👎 - NAY\n\nAs a Senator, it is your duty to do what is right for Hippokratia, it is advised to read the attached document in it's entirety.\n\nSIX Senators must vote AYE for this bill to pass\nThis vote will end after 48 hours."

    embed.set_footer(
        text=f"Initiated by {intr.user.display_name}",
        icon_url=intr.user.display_avatar.url
    )

    await intr.response.send_message("Created!", ephemeral=botManager.hideRespones)

    senChan = botManager.bot.get_channel(botManager.electionData["channels"]["senate"])
    if senChan:
        msg = await senChan.send(embed=embed)
        if notify:
            await senChan.send(f"<@&{botManager.serverData["roles"]["senator"]}>")
            await notify_senator(embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("✋")
        await msg.add_reaction("👎")
        registerElection(msg.id, "an amendment", True, 6, 48)
    else:
        print("Could not fetch senate channel")

    await log(f"[proposeammendment] Proposed an amendment vote.\burl={url}\nnotify={notify}")

@botManager.bot.tree.command(name="proposeveto", description="Proposes a Senatorial veto")
async def proposeveto(intr: discord.Interaction, description: str, url: str, notify: bool):
    await log(f"[proposeveto] {intr.user.display_name} ({intr.user.name}) ran this command")
    role = intr.guild.get_role(botManager.serverData["roles"]["senator"])
    if role not in intr.user.roles:
        await intr.response.send_message("You are not a Senator.", ephemeral=botManager.hideRespones)
        await log("[proposeveto] Denied")
        return
    await log("[proposeveto] Approved")

    embed = discord.Embed(
        title="A VETO has been started",
        description=description,
        color=discord.Color.blue(),
        url=url,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.description+=f"\n\n[LINK]({url}) to the proposition\n\nVOTING\n👍 - AYE\n✋ - ABSTAIN (No vote)\n👎 - NAY\n\nAs a Senator, it is your duty to do what is right for Hippokratia, it is advised to read the attached document in it's entirety.\n\nSIX Senators must vote AYE for this bill to pass\nThis vote will end after 24 hours."

    embed.set_footer(
        text=f"Initiated by {intr.user.display_name}",
        icon_url=intr.user.display_avatar.url
    )

    await intr.response.send_message("Created!", ephemeral=botManager.hideRespones)

    senChan = botManager.bot.get_channel(botManager.electionData["channels"]["senate"])
    if senChan:
        msg = await senChan.send(embed=embed)
        if notify:
            await senChan.send(f"<@&{botManager.serverData["roles"]["senator"]}>")
            await notify_senator(embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("✋")
        await msg.add_reaction("👎")
        registerElection(msg.id, "a veto", True, 6, 24)
    else:
        print("Could not fetch senate channel")

    await log(f"[proposeveto] Proposed a veto. url={url} notify={notify}")

@botManager.bot.tree.command(name="vote", description="Vote in the Senatorial Election")
async def vote(intr: discord.Interaction, user: discord.User):
    id = str(intr.user.id)
    otherID = str(user.id)

    if id == otherID:
        await intr.response.send_message("You can not vote for yourself.", ephemeral=botManager.hideRespones)
        return

    if id in botManager.votingData:
        data = botManager.votingData[id]
        if data == True:
            await intr.response.send_message("You have already voted.", ephemeral=botManager.hideRespones)
            return
    else:
        botManager.votingData[id] = False
    
    active = botManager.votingData["active"]
    polls = botManager.electionData[str(active)]["userPolls"]
    if otherID in polls:
        polls[otherID] += 1
    else:
        polls[otherID] = 1
    botManager.votingData[id] = True

    botManager.electionData[str(active)]["totalUsers"] += 1

    await intr.response.send_message(f"Registered vote for {user.name}", ephemeral=botManager.hideRespones)

@botManager.bot.tree.command(name="senatorialelection", description="Proposes a Senatorial Election")
async def senatorialelection(intr: discord.Interaction, notify: bool):
    await log(f"[senatorialelection] {intr.user.display_name} ({intr.user.name}) ran this command")
    role = intr.guild.get_role(botManager.serverData["roles"]["senator"])
    if role not in intr.user.roles:
        await intr.response.send_message("You are not a Senator.", ephemeral=botManager.hideRespones)
        await log("[senatorialelection] Denied")
        return
    await log("[senatorialelection] Approved")

    embed = discord.Embed(
        title="A Senatorial Election has been started",
        description="",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.description+=f"\nVOTING\nPlease use the /vote command to register a vote for any member of the server\n\nAs a citizen, you can only vote once. This vote is final, and can not be rescinded\nThis vote will end after 48 hours."

    embed.set_footer(
        text=f"Initiated by {intr.user.display_name}",
        icon_url=intr.user.display_avatar.url
    )

    await intr.response.send_message("Started!", ephemeral=botManager.hideRespones)

    elChan = botManager.bot.get_channel(botManager.serverData["channels"]["elections"])
    if elChan:
        msg = await elChan.send(embed=embed)
        if notify:
            await elChan.send(f"@everyone")
            await notify_senator(embed)
        registerElection(msg.id, "a Senatorial Election", False, 0, 48)

        # set up active
        botManager.votingData.clear()
        botManager.votingData["active"] = msg.id
    else:
        print("Could not fetch election channel")

    await log(f"[senatorialelection] Started an election")

@botManager.bot.tree.command(name="declareemergency", description="Declare Emergency Power")
async def declareemergency(intr: discord.Interaction, description: str, notify: bool):
    await log(f"[declareemergency] {intr.user.display_name} ({intr.user.name}) ran this command")
    role = intr.guild.get_role(botManager.serverData["roles"]["senator"])
    if role not in intr.user.roles:
        await intr.response.send_message("You are not a Senator.", ephemeral=botManager.hideRespones)
        await log("[declareemergency] Denied")
        return
    await log("[declareemergency] Approved")

    embed = discord.Embed(
        title="EMERGENCY POWER has been PROPOSED",
        description=description,
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.description+=f"\n\nVOTING\n👍 - AYE\n✋ - ABSTAIN (No vote)\n👎 - NAY\n\nAs a Senator, it is your duty to do what is right for Hippokratia\n\nSIX Senators must vote AYE for this bill to pass\nThis vote will end after 24 hours."

    embed.set_footer(
        text=f"Initiated by {intr.user.display_name}",
        icon_url=intr.user.display_avatar.url
    )

    await intr.response.send_message("Created!", ephemeral=botManager.hideRespones)

    senChan = botManager.bot.get_channel(botManager.electionData["channels"]["senate"])
    if senChan:
        msg = await senChan.send(embed=embed)
        if notify:
            await senChan.send(f"<@&{botManager.serverData["roles"]["senator"]}>")
            await notify_senator(embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("✋")
        await msg.add_reaction("👎")
        registerElection(msg.id, "emergency power", True, 6, 24)
    else:
        print("Could not fetch senate channel")

    await log(f"[declareemergency] Emergency Power proposed")

@botManager.bot.tree.command(name="help", description="Shows a command guide")
async def help(intr: discord.Interaction):
    embed = discord.Embed(
        title="Help",
        description="""proposebill(description, url, notify)
        """,
        color=discord.Color.green()
    )

    await intr.response.send_message(embed=embed, ephemeral=botManager.hideRespones)

def loadData():
    with open(electionf, "r", encoding="utf-8") as file:
        botManager.electionData = json.load(file)

    with open(votingf, "r", encoding="utf-8") as file:
        botManager.votingData = json.load(file)

    with open(serverf, "r", encoding="utf-8") as file:
        botManager.serverData = json.load(file)

    with open(adminf, "r", encoding="utf-8") as file:
        admin.adminData = json.load(file)

def flushData():
    data = json.dumps(botManager.electionData, indent=4)
    with open(electionf, "w", encoding="utf-8") as file:
        file.write(data)

    data = json.dumps(botManager.votingData, indent=4)
    with open(votingf, "w", encoding="utf-8") as file:
        file.write(data)

    data = json.dumps(admin.adminData, indent=4)
    with open(adminf, "w", encoding="utf-8") as file:
        file.write(data)

def registerElection(id: int, type: str, reactionary: bool, needed: int, duration: int):
    botManager.electionData[str(id)] = {
        "timestamp": datetime.datetime.now().timestamp(),
        "type": type,
        "reactionary": reactionary,
        "expired": False,
        "neededAye": needed,
        "duration":duration,
        "aye": 0,
        "nay": 0,
        "abs": 0,
        "totalUsers": 0,
        "userPolls":{}
    }

def handle_exit(signum, frame):
    print("Handling CTRL+C")
    economy.updateEconomy()
    flushData()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)

economy.readEconomy()
loadData()

key = ""

# read key from .env
with open(keyf, "r", encoding="utf-8") as file:
    key = file.read()

@botManager.bot.event
async def on_ready():
    checkExpiration.start()

botManager.bot.run(key)