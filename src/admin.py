import botManager
import discord
from discord import app_commands
from botManager import bot
import economy
import datetime

adminData = {}

# adminData user structure
# warns = the amount of warnings a user has received through the admin panel
# flags = the amount of automated flags a user has received
# risk = a score from 0 to 1 representing how likely they are to violate the rules, calculated through the following
# r=1-(1/(w+0.25f+1))

@bot.tree.command(name="panel")
@app_commands.checks.has_permissions(mute_members=True)
async def panel(intr: discord.Interaction, user: discord.User):
    strID = str(user.id)
    if strID not in adminData:
        adminData[strID] = {"warns": [], "flags": 0, "risk": 0}
    data = adminData[strID]
    data["risk"] = 1-(1/(len(data["warns"]) + (data["flags"]*0.25)+1))

    panelEmbed = discord.Embed(
        title=f"Admin Panel for {user.global_name} ({user.name})",
        description="**Admin Data:**",
        color=discord.Color.red()
    )
    panelEmbed.description+=f"\nWarns: {len(data["warns"])}"
    panelEmbed.description+=f"\nFlags: {data["flags"]}"
    panelEmbed.description+=f"\nRisk Score: {data["risk"]}"

    # economy
    if strID in economy.econ:
        econData = economy.econ[strID]

        panelEmbed.description+=f"\n\n**Economy Data:**"
        panelEmbed.description+=f"\nBalance: {econData["bal"]}"
        panelEmbed.description+=f"\nPIN: ||{econData["pin"]}||"
        panelEmbed.description+=f"\nCan Gamble: {econData["cangamble"]}"

    for warning in data["warns"]:
        if warning["expired"] == False and (datetime.datetime.now().timestamp() - warning["timestamp"] >= (48 * 3600)):
            warning["expired"] = True

    await intr.response.send_message(embed=panelEmbed, ephemeral=botManager.hideRespones)

@bot.tree.command(name="warnhistory", description="See the warning history of a user")
@app_commands.checks.has_permissions(mute_members=True)
async def warnhistory(intr: discord.Interaction, user: discord.User):
    strID = str(user.id)
    if strID not in adminData:
        adminData[strID] = {"warns": [], "flags": 0, "risk": 0}
    data = adminData[strID]

    histEmbed = discord.Embed(
        title=f"Warning history of {user.global_name} ({user.name})",
        description="",
        color=discord.Color.red()
    )

    count = len(data["warns"])
    pos = 0
    histEmbed.description += f"History length: {count}\n"
    for warning in data["warns"]:
        histEmbed.description += f"{pos:04d} <t:{warning["timestamp"]}:f> / <t:{warning["timestamp"]}:R>"
        if warning["expired"] == False and (datetime.datetime.now().timestamp() - warning["timestamp"] >= (48 * 3600)):
            warning["expired"] = True
            histEmbed.description += " (EXPIRED)"
        elif warning["expired"] == True:
            histEmbed.description += " (EXPIRED)"
        histEmbed.description += "\n"
        pos+=1

    await intr.response.send_message(embed=histEmbed, ephemeral=botManager.hideRespones)

@bot.tree.command(name="warn", description="Warn a user")
@app_commands.checks.has_permissions(mute_members=True)
async def warn(intr: discord.Interaction, user: discord.User, reason: str):
    strID = str(user.id)
    if strID not in adminData:
        adminData[strID] = {"warns": [], "flags": 0, "risk": 0}
    data = adminData[strID]
    
    for warning in data["warns"]:
        if warning["expired"] == False and (datetime.datetime.now().timestamp() - warning["timestamp"] >= (48 * 3600)):
            warning["expired"] = True

    newWarn = {
        "expired": False,
        "timestamp": round(datetime.datetime.now().timestamp()),
        "reason": reason,
        "by": intr.user.id
    }

    data["warns"].append(newWarn)
    data["risk"] = 1-(1/(len(data["warns"]) + (data["flags"]*0.25)+1))

    respEmbed = discord.Embed(
        title="Success",
        description=f"Warned {user.global_name} ({user.name}) for the following: ```{reason}```\nThis will expire in 48 hours",
        color=discord.Color.green()
    )

    guild = bot.get_guild(int(botManager.serverData["guild_id"]))
    member = guild.get_member(user.id)

    notifEmbed = discord.Embed(
        title="You have received a warning",
        description=f"You have been warned by {intr.user.global_name} ({intr.user.name})\nReason: ```{reason}```\nFor this, you have been "
    )
    count = 0
    for warning in data["warns"]:
        if warning["expired"] == False:
            count+=1

    if count == 1:
        notifEmbed.description += "timed out for 30 minutes."
        await member.send(embed=notifEmbed)
        await member.timeout(datetime.timedelta(minutes=30), reason="Reached first warning")  
    elif count == 2:
        notifEmbed.description += "timed out for 2 hours."
        await member.send(embed=notifEmbed)
        await member.timeout(datetime.timedelta(hours=2), reason="Reached second warning")
    elif count == 3:
        notifEmbed.description += "timed out for 12 hours."
        await member.send(embed=notifEmbed)
        await member.timeout(datetime.timedelta(hours=2), reason="Reached third warning")
    elif count == 4:
        notifEmbed.description += "banned."
        await member.send(embed=notifEmbed)
        await member.ban(reason="Reached fourth warning")

    await intr.response.send_message(embed=respEmbed, ephemeral=botManager.hideRespones)

@bot.tree.command(name="seewarning", description="See the warning of a user")
@app_commands.checks.has_permissions(mute_members=True)
async def seewarning(intr: discord.Interaction, user: discord.User, id: int):
    strID = str(user.id)
    if strID not in adminData:
        adminData[strID] = {"warns": [], "flags": 0, "risk": 0}
    data = adminData[strID]

    for warning in data["warns"]:
        if warning["expired"] == False and (datetime.datetime.now().timestamp() - warning["timestamp"] >= (48 * 3600)):
            warning["expired"] = True

    if id >= len(data["warns"]):
        await intr.response.send_message("Invalid warning ID", ephemeral=botManager.hideRespones)
        return

    warning = data["warns"][id]

    issuer = await bot.fetch_user(int(warning["by"]))

    resEmbed = discord.Embed(
        title=f"Warning {id} for {user.global_name} ({user.name})",
        description=f"Reason: ```{warning["reason"]}```\nTimestamp: <t:{warning["timestamp"]}:f> / <t:{warning["timestamp"]}:R>\nIssued by {issuer.global_name} ({issuer.name})",
        color=discord.Color.red()
    )

    await intr.response.send_message(embed=resEmbed, ephemeral=botManager.hideRespones)