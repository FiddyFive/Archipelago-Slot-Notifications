import asyncio
import json
from urllib.request import urlopen

from discord.ext import commands
import discord

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="", intents=intents)
watches: dict[str, list]

# Endpoints:
trackerAPI = "https://archipelago.gg/api/tracker/"
roomAPI = "https://archipelago.gg/api/room_status/"

async def loop():
    await asyncio.sleep(60*60)
    await update()
    await save()

async def update():
    global watches

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
            mostRecentCount = len(trackerData["player_items_received"][int(slotObject["slotNo"])]["items"])
            previousCount = int(slotObject["lastCount"])
            if mostRecentCount != previousCount:
                await notify(slotObject["discordId"], slotObject["slotName"], mostRecentCount - previousCount)
                slotObject["lastCount"] = str(mostRecentCount)

async def save():
    global watches

    with open("store.json", 'w') as store:
        json.dump(watches, store)

async def notify(discordID: str, slotName: str, diff: int):
    global bot

    user = await bot.fetch_user(int(discordID))
    # TODO: Test if user exists. 
    #       If not exists, clear all watches tied to that user
    if not user: return
    await user.send(slotName + " has " + str(diff) + " new checks.")

@bot.event
async def on_ready():
    global watches

    # Don't use unless the command tree breaks and you can't run the sync command.
    # try:
    #     print("Syncing")
    #     result = await bot.tree.sync()
    #     print(result)
    # except Exception as e:
    #     print(e)

    print("Loading store")
    with open("store.json") as data:
        watches = json.load(data)
    print("Ready")

@bot.tree.command()
async def sync(interaction: discord.Interaction):
    if (interaction.user.id != bot.owner_id): 
        await interaction.response.send_message("Insufficient permission, please contact the owner of this bot.")
        return
    await interaction.response.send_message("Beginning sync.")
    await bot.tree.sync()
    await interaction.followup.send("Sync complete.")

@discord.app_commands.user_install()
@bot.tree.command()
async def debug_update(_):
    await update()

@discord.app_commands.user_install()
@bot.tree.command()
async def debug_save(_):
    await save()


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
async def watch(interaction: discord.Interaction, roomtoken: str, slot: str, rate: int = 60):
    global watches

    await interaction.response.send_message("Requested watch on " + roomtoken + " player " + slot, ephemeral=True)
    
    with urlopen(roomAPI + roomtoken) as response:
        body = response.read()
    roomData = json.loads(body)

    slotNo: int = next(i for i,x in enumerate(roomData["players"]) if x[0] == slot)
    print(str(slotNo))
    
    id = str(interaction.user.id)

    if not roomtoken in watches:
        watches[roomtoken] = []

    watches[roomtoken].append({
        "discordId": id,
        "slotNo": str(slotNo),
        "slotName": slot,
        "lastCount": "0"
    })
    print(watches[roomtoken])

    await interaction.followup.send("Created watch on player " + str(slotNo+1), ephemeral=True)

@discord.app_commands.user_install()
@bot.tree.command()
async def unwatch(interaction: discord.Interaction, roomtoken: str, slot: str):
    global watches

    try:
        for i, item in enumerate(watches[roomtoken]):
            if item.slotName == slot:
                del watches[roomtoken][i]
                await interaction.response.send_message("Deleted watch on " + slot)
                break
        raise Exception("Did not find this watch")
    except Exception as e:
        await interaction.response.send_message("Error: " + str(e))

@discord.app_commands.user_install()
@bot.tree.command()
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong")

# @discord.app_commands.user_install()
# @bot.tree.command()
# async def watch_port(_: discord.Interaction, roomToken: str):
#     return

async def main(conf):
    async with asyncio.TaskGroup() as group:
        bot_task = group.create_task(bot.start(conf["token"]))
        watch_task = group.create_task(loop())

    return bot_task.result(), watch_task.result()

if __name__ == '__main__':
    with open("bot.json") as data:
        conf = json.load(data)

    asyncio.run(main(conf))