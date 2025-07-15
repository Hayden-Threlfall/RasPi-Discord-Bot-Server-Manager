import asyncio
import asyncssh
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
#Set .env Declarations
load_dotenv()
DISCORD_TOKEN = os.getenv("SERVER_IP")
DISCORD_GUILD_ID = int(os.getenv("SERVER_IP")) 
SERVER_IP = os.getenv("SERVER_IP")
PORT = int(os.getenv("PORT", 22))  # fallback to 22 if not set
SERVER_MAC = os.getenv("SERVER_MAC")
SERVER_USER = os.getenv("SERVER_USER")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")
ALLOWED_ROLE_ID = int(os.getenv("ALLOWED_ROLE_ID", 0)) # set to 0, so any user can use
lock = Lock()

# Check if a given IP is online using ping
def is_online(ip):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    response = os.system(f"ping {param} 1 {ip} > /dev/null 2>&1")
    return response == 0

async def ssh_run_command(server_ip, port, username, key_filepath, command):
    async with asyncssh.connect(
        server_ip,
        port=port,
        username=username,
        client_keys=[key_filepath]
    ) as conn:
        result = await conn.run(command, check=True)
        print(result.stdout)

# Custom Bot class
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=discord.Intents.default()
        )

async def role_check(interaction):
    if ALLOWED_ROLE_ID == 0:
        return True
    if not any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return False
    return True

async def lock_check(interaction):
    if not lock.acquire(blocking=False):
        await interaction.response.send_message("I'm Busy Right Now", ephemeral=True)
        return False
    return True

# Create the bot instance
bot = MyBot()

@bot.event
async def on_ready():
    print(f"Bot is ready! Logged in as {bot.user} (ID: {bot.user.id})")
    
    # Sync slash commands to your specific guild
    guild = discord.Object(id=DISCORD_GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    print(f"Synced Commands to Server {DISCORD_GUILD_ID}")
    

# Command to toggle GPIO pin for 10 seconds
@bot.tree.command(name="force_start_server")
async def force_start_server(interaction: discord.Interaction):
    if not await lock_check(interaction): return
    try:
        if not await role_check(interaction): return
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

        for _ in range(12):
            await asyncio.sleep(5)
            if is_online(SERVER_IP):
                await interaction.edit_original_response(content = "✅ Server Is Online✅ ")
                break
        else:
            await interaction.edit_original_response(content = "❌ Server Failed To Start ❌")
    finally:
        lock.release()


@bot.tree.command(name="force_stop_server")
async def force_stop_server(interaction: discord.Interaction):
    if not await lock_check(interaction): return
    try:
        if not await role_check(interaction): return
        await interaction.response.send_message(f"{interaction.user.mention} Attempting To Stop The Server...", ephemeral=True)

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(POWER_PIN, GPIO.OUT)
        GPIO.output(POWER_PIN, GPIO.LOW)
        await asyncio.sleep(1)
        GPIO.output(POWER_PIN, GPIO.HIGH)
        await asyncio.sleep(10)
        GPIO.output(POWER_PIN, GPIO.LOW)
        await asyncio.sleep(5)

        if not is_online(SERVER_IP):
            await interaction.edit_original_response(content = "✅ Server Is Offline ✅")
        else:
            await interaction.edit_original_response(content = "❌ Server Failed To Shutdown ❌")
        
    finally:
        lock.release()

@bot.tree.command(name="start_server")
async def start_server(interaction: discord.Interaction):
    if not await lock_check(interaction): return
    try:
        if not await role_check(interaction): return
        await interaction.response.send_message("Attempting To Start (Wake On Lan) The Server...", ephemeral=True)

        if is_online(SERVER_IP):
            await interaction.edit_original_response(content = "✅ Server Already Awake... ✅")
            return
        send_magic_packet(SERVER_MAC)
        for _ in range(6):
            await asyncio.sleep(10)
            if is_online(SERVER_IP):
                await interaction.edit_original_response(content ="✅ Server Is Awake ✅")
                break
        else:
            await interaction.edit_original_response(content ="❌ Server Is Not Awake Yet ❌")
    finally:
        lock.release()

@bot.tree.command(name="stop_server")
async def stop_server(interaction: discord.Interaction):
    command = "sudo systemctl poweroff"
    if not await lock_check(interaction): return
    try:
        if not await role_check(interaction): return
        await interaction.response.send_message("Attempting To Stop The Server...", ephemeral=True)
        if not is_online(SERVER_IP):
            await interaction.edit_original_response(content = "✅ Server Is Offline Already... ✅")
            return
        await ssh_run_command(SERVER_IP, PORT, SERVER_USER, SSH_KEY_PATH, command)
        for _ in range(6):
            await asyncio.sleep(5)
            if not is_online(SERVER_IP):
                await interaction.edit_original_response(content = "✅ Server Is Offline ✅")
                break
        else:
            await interaction.edit_original_response(content = "❌ Server Failed To stop ❌")
    finally:
        lock.release()

@bot.tree.command(name="restart_server")
async def restart_server(interaction: discord.Interaction):    
    command = "sudo systemctl reboot"
    if not await lock_check(interaction): return
    try:
        if not await role_check(interaction): return
        await interaction.response.send_message("Attempting To Restart The Server...", ephemeral=True)
        if not is_online(SERVER_IP):
            await interaction.edit_original_response(content = "❌ Server Is Offline Already Cant Restart... ❌")
            return
        await ssh_run_command(SERVER_IP, PORT, SERVER_USER, SSH_KEY_PATH, command)
        for _ in range(6):
            await asyncio.sleep(5)
            if is_online(SERVER_IP):
                await interaction.edit_original_response(content = "✅ Server Is Back Online ✅")
                break
        else:
            await interaction.edit_original_response(content = "❌ Server Failed To Restart ❌")
    finally:
        lock.release()

@bot.tree.command(name="sleep_server")
async def sleep_server(interaction: discord.Interaction):
    command = "sudo systemctl hybrid-sleep"
    if not await lock_check(interaction): return
    try:
        if not await role_check(interaction): return
        await interaction.response.send_message("Attempting To Sleep The Server...", ephemeral=True)
        if not is_online(SERVER_IP):
            await interaction.edit_original_response(content = "❌ Server Is Offline Already Cant Sleep... ❌")
            return
        await ssh_run_command(SERVER_IP, PORT, SERVER_USER, SSH_KEY_PATH, command)
        for _ in range(6):
            await asyncio.sleep(5)
            if not is_online(SERVER_IP):
                await interaction.edit_original_response(content = "✅ Server Is Offline ✅")
                break
        else:
            await interaction.edit_original_response(content = "❌ Server Failed To Sleep ❌")
    finally:
        lock.release()

@bot.tree.command(name="hybernate_server")
async def sleep_server(interaction: discord.Interaction):
    command = "sudo systemctl hibernate"
    if not await lock_check(interaction): return
    try:
        if not await role_check(interaction): return
        await interaction.response.send_message("Attempting To Hybernate The Server...", ephemeral=True)
        if not is_online(SERVER_IP):
            await interaction.edit_original_response(content = "❌ Server Is Offline Already Cant Hybernate... ❌")
            return
        await ssh_run_command(SERVER_IP, PORT, SERVER_USER, SSH_KEY_PATH, command)
        for _ in range(6):
            await asyncio.sleep(5)
            if not is_online(SERVER_IP):
                await interaction.edit_original_response(content = "✅ Server Is Offline ✅")
                break
        else:
            await interaction.edit_original_response(content = "❌ Server Failed To Sleep ❌")
    finally:
        lock.release()

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
        "**COMMANDS FOR XBOT**\n"
        "/start_server\n"
        "/stop_server\n"
        "/sleep_server\n"
        "/hibernate_server\n"
        "/restart_server\n"
        "/force_start_server\n"
        "/force_stop_server\n"
        "/status_server\n"
        "/commands",
        ephemeral=True
    )

# Run the bot
bot.run(DISCORD_TOKEN)
