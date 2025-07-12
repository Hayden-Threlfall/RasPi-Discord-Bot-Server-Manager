import asyncio
import discord
import platform
import RPi.GPIO as GPIO
import os

from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from threading import Thread
from threading import Lock
from wakeonlan import send_magic_packet

POWER_PIN = 14
CHIP = "gpiochip0"
SERVER_IP = <"YOUR SERVER IP">
SERVER_MAC = <"YOUR SERVER MAC ADDRESS">
mutex_lock = Lock()

load_dotenv()

# Check if a given IP is online using ping
def is_online(ip):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    response = os.system(f"ping {param} 1 {ip} > /dev/null 2>&1")
    return response == 0

# Custom Bot class
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=discord.Intents.default()
        )

# Create the bot instance
bot = MyBot()

@bot.event
async def on_ready():
    print(f"Bot is ready! Logged in as {bot.user} (ID: {bot.user.id})")
    
    # Sync slash commands to your specific guild
    guild = discord.Object(id=int(os.getenv('GUILD_ID')))
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    print(f"Synced Commands to Server {int(os.getenv('GUILD_ID'))}")
    

# Command to toggle GPIO pin for 10 seconds
@bot.tree.command(name="start_server")
async def start_server(interaction: discord.Interaction):
    if not mutex_lock.acquire(blocking=False):
        await interaction.response.send_message("I'm Busy Right Now", ephemeral=True)
        return

    try:
        await interaction.response.send_message(f"{interaction.user.mention} Attempting To Start The Server...", ephemeral=True)

        if is_online(SERVER_IP):
            await interaction.edit_original_response(content = "✅ Server Already Online... ✅")
            return
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(POWER_PIN, GPIO.OUT)
        GPIO.output(POWER_PIN, GPIO.LOW)
        await asyncio.sleep(1)
        GPIO.output(POWER_PIN, GPIO.HIGH)
        await asyncio.sleep(2)
        GPIO.output(POWER_PIN, GPIO.LOW)

        for _ in range(6):
            await asyncio.sleep(10)
            if is_online(SERVER_IP):
                await interaction.edit_original_response(content = "✅ Server Is Online✅ ")
                break
        else:
            await interaction.edit_original_response(content = "❌ Server Failed To Start ❌")
    finally:
        mutex_lock.release()


@bot.tree.command(name="shutdown_server")
async def shutdown_server(interaction: discord.Interaction):
    
    if not mutex_lock.acquire(blocking=False):
        await interaction.response.send_message("I'm Busy Right Now", ephemeral=True)
        return

    try:
        await interaction.response.send_message(f"{interaction.user.mention} Attempting To Stop The Server...", ephemeral=True)

        if not is_online(SERVER_IP):
            await interaction.edit_original_response(content = "✅ Server Already Offline... ✅")
            return
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(POWER_PIN, GPIO.OUT)
        GPIO.output(POWER_PIN, GPIO.LOW)
        await asyncio.sleep(1)
        GPIO.output(POWER_PIN, GPIO.HIGH)
        await asyncio.sleep(10)
        GPIO.output(POWER_PIN, GPIO.LOW)
        await asyncio.sleep(4)

        if not is_online(SERVER_IP):
            await interaction.edit_original_response(content = "✅ Server Is Offline ✅")
        else:
            await interaction.edit_original_response(content = "❌ Server Failed To Shutdown ❌")
        
    finally:
        mutex_lock.release()

@bot.tree.command(name="wake_on_lan_server")
async def wol_server(interaction: discord.Interaction):
    if not mutex_lock.acquire(blocking=False):
        await interaction.response.send_message("I'm Busy Right Now", ephemeral=True)
        return

    try:
        await interaction.response.send_message("Attempting Wake On Lan...", ephemeral=True)

        if is_online(SERVER_IP):
            await interaction.edit_original_response(content = "✅ Server Already Awake... ✅")
            return
        send_magic_packet(SERVER_MAC, ip_address=SERVER_IP)
        for _ in range(6):
            await asyncio.sleep(10)
            if is_online(SERVER_IP):
                await interaction.edit_original_response(content ="✅ Server Is Awake ✅")
                break
        else:
            await interaction.edit_original_response(content ="❌ Server Is Not Awake Yet Or Off ❌")
    finally:
        mutex_lock.release()

@bot.tree.command(name="status_server")
async def status_server(interaction: discord.Interaction):
    await interaction.response.send_message("Checking Status...", ephemeral=True)
    if is_online(SERVER_IP):
        await interaction.edit_original_response(content = "✅ Server Is Online ✅")
    else:
        await interaction.edit_original_response(content = "❌ Server Is Offline ❌")

@bot.tree.command(name="commands")
async def commands(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**COMMANDS FOR XBOT**\n/start_server\n/shutdown_server\n/wake_on_lan_server\n/status_server\n/commands", ephemeral=True)

# Run the bot
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
