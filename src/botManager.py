import discord
import time
from discord.ext import commands

serverData = {}
electionData = {}
votingData = {}
hideRespones = True

class HKbot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Command tree synced")
    
    async def altLog(self, message: str):
        guild = self.get_guild(serverData["guild_id"])
        logc = guild.get_channel(serverData["channels"]["logs"])

        await logc.send(f"(<t:{int(time.time())}:f>) {message}")

    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id:
            return

        if str(payload.message_id) in electionData:
            member = payload.member
            if member is None:
                guild = self.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)

            # check if the player has Senate permissions AND hasn't already reacted

            channel = self.get_channel(payload.channel_id)
            msg = await channel.fetch_message(payload.message_id)
            already_voted = False

            #check aye
            te0 = '👍'
            te0r = discord.utils.get(msg.reactions, emoji=te0)
            if te0r and te0 != payload.emoji.name:
                async for user in te0r.users():
                    if user.id == payload.user_id:
                        already_voted = True
                        print("ALREADY VOTED! Detected Aye")

            #check nay
            te1 = '👎'
            te1r = discord.utils.get(msg.reactions, emoji=te1)
            if te1r and te1 != payload.emoji.name:
                async for user in te1r.users():
                    if user.id == payload.user_id:
                        already_voted = True
                        print("ALREADY VOTED! Detected Nay")

            #check abstain
            te2 = '✋'
            te2r = discord.utils.get(msg.reactions, emoji=te2)
            if te2r and te2 != payload.emoji.name:
                async for user in te2r.users():
                    if user.id == payload.user_id:
                        already_voted = True
                        print("ALREADY VOTED! Detected Abstain")

            await self.altLog(f"[on_raw_reaction_add] User {payload.user_id} reacted with {payload.emoji} to message {payload.message_id}")
            if electionData["roles"]["senator"] in [role.id for role in member.roles] and already_voted == False:
                if payload.emoji.name == te0:
                    electionData[str(payload.message_id)]["aye"] = electionData[str(payload.message_id)]["aye"] + 1
                elif payload.emoji.name == te1:
                    electionData[str(payload.message_id)]["nay"] = electionData[str(payload.message_id)]["nay"] + 1
                elif payload.emoji.name == te2:
                    electionData[str(payload.message_id)]["abs"] = electionData[str(payload.message_id)]["abs"] + 1

                await self.altLog("[on_raw_reaction_add] Approved")
            else:
                if not electionData["roles"]["senator"] in [role.id for role in member.roles]:
                    await self.altLog("[on_raw_reaction_add] Denied: Member is not a Senator")
                else:
                    await self.altLog("[on_raw_reaction_add] Denied: Member has already voted")
                await msg.remove_reaction(payload.emoji, member)

    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.user.id:
            return

        if str(payload.message_id) in electionData:
            member = payload.member
            if member is None:
                guild = self.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)

            # check if the player has Senate permissions AND hasn't already reacted

            channel = self.get_channel(payload.channel_id)
            msg = await channel.fetch_message(payload.message_id)

            #check aye
            te0 = '👍'
            #check nay
            te1 = '👎'
            #check abstain
            te2 = '✋'

            await self.altLog(f"[on_raw_reaction_remove] User {payload.user_id} reacted with {payload.emoji} to message {payload.message_id}")
            if electionData["roles"]["senator"] in [role.id for role in member.roles]:
                if payload.emoji.name == te0:
                    electionData[str(payload.message_id)]["aye"] = electionData[str(payload.message_id)]["aye"] - 1
                if payload.emoji.name == te1:
                    electionData[str(payload.message_id)]["nay"] = electionData[str(payload.message_id)]["nay"] - 1
                if payload.emoji.name == te2:
                    electionData[str(payload.message_id)]["abs"] = electionData[str(payload.message_id)]["abs"] - 1

                await self.altLog("[on_raw_reaction_remove] Approved")
            else:
                if not electionData["roles"]["senator"] in [role.id for role in member.roles]:
                    await self.altLog("[on_raw_reaction_remove] Denied: Member is not a Senator")
                await msg.remove_reaction(payload.emoji, member)

bot = HKbot()