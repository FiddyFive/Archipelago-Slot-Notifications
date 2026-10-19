import asyncio
import json
from urllib.request import urlopen

from discord.ext import commands
import discord

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="", intents=intents)
watches: dict[str, list]

# Endpoints:
trackerAPI = "https://archipelago.gg/api/tracker/"
roomAPI = "https://archipelago.gg/api/room_status/"

async def loop():
    await asyncio.sleep(60*60)
    await update()

async def update():
    for room in watches:
        with urlopen(roomAPI + room) as response:
            body = response.read()
            roomData = json.loads(body)
        
        with urlopen(trackerAPI + roomData["tracker"]) as response:
            body = response.read()
            trackerData = json.loads(body)

        for slotObject in watches[room]:
            # TODO: Double check for off by one error in slot no
            # New checks are appended to the end of the response

            '''
            player_items_received [
                {
                    items: [int[4]]
                    player: int # Should be object's list index + 1
                    team: int
                }
            ]
            '''
            mostRecentCount = len(trackerData["player_items_received"][slotObject.slotNo]["items"])
            previousCount = int(slotObject["lastCount"])
            if mostRecentCount != slotObject["lastCount"]:
                await notify(slotObject["discordId"], slotObject["slotName"], mostRecentCount - previousCount)

async def notify(discordID: str, slotName: str, diff: int):
    user = bot.get_user(int(discordID))
    # TODO: Test if user exists. 
    #       If not exists, clear all watches tied to that user
    if not user: return
    await user.send(slotName + " has " + str(diff) + " new checks.")


@bot.event
async def on_ready():
    global watches
    with open("store.json") as data:
        watches = json.load(data)
        json.dumps

@bot.tree.command()
async def sync(interaction: discord.Interaction):
    if (not interaction.user.id == bot.owner_id): 
        await interaction.response.send_message("Insufficient permission, please contact the owner of this bot.")
        return
    await interaction.response.send_message("Beginning sync.")
    await bot.tree.sync()
    await interaction.followup.send("Sync complete.")

# Data will be stored in watches["roomToken"]["slotNo"]
# {
#   discordId,
#   slotNo,
#   slotName,
#   lastCount
# }

# IMPORTANT: Slot No stores the 0 indexed slot ID, which is 1 less than the 1 indexed player ID.
@discord.app_commands.user_install()
@bot.tree.command()
async def watch(interaction: discord.Interaction, roomToken: str, slot: str, rate: int = 60):
    global watches
    
    with urlopen(roomAPI + roomToken) as response:
        body = response.read()

    roomData = json.loads(body)
    slotNo: int = roomData["players"].index(slot)
    
    id = str(interaction.user.id)
    if not watches[roomToken]:
        watches[roomToken] = [];
    watches[roomToken].append({
        "discordId": id,
        "slotNo": slotNo,
        "slotName": slot,
        "lastReceived": ""
    })

@discord.app_commands.user_install()
@bot.tree.command()
async def unwatch(interaction: discord.Interaction, roomToken: str, slot: str, rate: int = 60):
    global watches

    try:
        for i, item in enumerate(watches[roomToken]):
            if item.slotName == slot:
                del watches[roomToken][i]
                await interaction.response.send_message("Deleted watch on " + slot)
                break   
    except Exception as e:
        await interaction.response.send_message("Error: " + str(e))
        

@discord.app_commands.user_install()
@bot.tree.command()
async def watch_port(_: discord.Interaction, roomToken: str):
    return

async def main():
    async with asyncio.TaskGroup() as group:
        bot_task = group.create_task(bot.start(conf["token"]))
        watch_task = group.create_task(loop())

    return bot_task.result(), watch_task.result()

if __name__ == '__main__':
    with open("bot.json") as data:
        conf = json.load(data)

    asyncio.run(main())