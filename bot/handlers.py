from aiogram import Router, F, types
from aiogram.filters import Command, CommandObject
import bot_config as config
from keyboards import get_maps_keyboard, get_modes_keyboard, get_main_keyboard, get_reply_keyboard
from rcon_client import RCONClient
import re
import random
import os
import glob
import html
from log_parser import generate_report

router = Router()
rcon = RCONClient()

# Middleware / Filter for security
def is_admin(message: types.Message):
    # Handle both Message and CallbackQuery
    user_id = message.from_user.id
    return user_id == config.ALLOWED_USER_ID

def get_current_mode_name():
    try:
        info = rcon.get_full_info()
        g_type = -1
        g_mode = -1
        
        type_match = re.search(r'game_type\s*=\s*(\d+)', info.get("game_type", ""))
        if type_match: g_type = int(type_match.group(1))
        
        mode_match = re.search(r'game_mode\s*=\s*(\d+)', info.get("game_mode", ""))
        if mode_match: g_mode = int(mode_match.group(1))
        
        return config.MODE_LOOKUP.get((g_type, g_mode))
    except Exception:
        return None
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    if not is_admin(message):
        return await message.answer("⛔ Access Denied")
    
    await message.answer(
        "🏴‍☠️ **Йо-хо-хо! Ты попал на борт нашего кибер-судна, салага!**\n\n"
        "Здесь мы не просто ставим хэдшоты, мы грабим раунды и берем плент на абордаж! "
        "Хватай свой девайс, как бутылку рома, и покажи этим КТ, кто здесь настоящий капитан! Аррр! 💣🦜",
        reply_markup=get_reply_keyboard()
    )
    header = get_menu_header_text()
    await message.answer(
        header,
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

def get_menu_header_text():
    try:
        info = rcon.get_full_info()
        status_text = info.get("status", "")
        
        hostname = "Unknown"
        hostname_match = re.search(r"hostname\s*:\s*(.*)", status_text)
        if hostname_match: hostname = hostname_match.group(1).strip()
        if hostname == "Counter-Strike 2" or hostname == "Unknown": hostname = config.CS2_SERVERNAME
        
        map_name = "Unknown"
        map_match = re.search(r"map\s*:\s*([^\s]+)", status_text) 
        if map_match: 
             map_name = map_match.group(1)
        else:
             map_match = re.search(r"loaded spawngroup\(\s*1\)\s*:\s*SV:\s*\[\d+:\s*([^|]+)\s*\|", status_text)
             if map_match: map_name = map_match.group(1).strip()
        
        g_type = -1
        g_mode = -1
        type_match = re.search(r'game_type\s*=\s*(\d+)', info.get("game_type", ""))
        if type_match: g_type = int(type_match.group(1))
        mode_match = re.search(r'game_mode\s*=\s*(\d+)', info.get("game_mode", ""))
        if mode_match: g_mode = int(mode_match.group(1))
        
        mode_name = config.MODE_LOOKUP.get((g_type, g_mode), f"Unknown ({g_type},{g_mode})")
        
        return f"🖥 <b>{html.escape(hostname)}</b>\n🎮 Mode: <b>{html.escape(mode_name)}</b>\n🗺 Map: <b>{html.escape(map_name)}</b>"
    except Exception as e:
        return f"Select an action:"

@router.message(F.text == "☰ Menu")
async def cmd_menu(message: types.Message):
    if not is_admin(message): return
    header = get_menu_header_text()
    await message.answer(header, reply_markup=get_main_keyboard(), parse_mode="HTML")

@router.callback_query(lambda c: c.data.startswith("menu:"))
async def process_menu_callback(callback: types.CallbackQuery):
    if not is_admin(callback): return
    
    parts = callback.data.split(":")
    action = parts[1]
    forced_mode = parts[2] if len(parts) > 2 else None
    
    if action == "map":
        current_mode = forced_mode if forced_mode else get_current_mode_name()
        msg = "🗺 **Choose a map:**"
        if current_mode:
            msg += f"\n(Filtered for **{current_mode}**)"
        await callback.message.answer(msg, reply_markup=get_maps_keyboard(current_mode, 0), parse_mode="Markdown")
    elif action == "mode":
        await callback.message.answer("🎮 **Choose a game mode:**", reply_markup=get_modes_keyboard())
    elif action == "restart":
        response = rcon.execute("mp_restartgame 1")
        if "Error" in response:
            await callback.message.answer(f"❌ Failed to restart match.\nRCON: `{response}`")
        else:
            await callback.message.answer(f"✅ Match restarting...")
    elif action == "addt":
        response = rcon.add_bot("t")
        if "Error" in response:
            await callback.message.answer(f"❌ Failed to add T Bot.\nRCON: `{response}`")
        else:
            await callback.message.answer(f"✅ T Bot added.\nRCON: `{response}`")
    elif action == "addct":
        response = rcon.add_bot("ct")
        if "Error" in response:
            await callback.message.answer(f"❌ Failed to add CT Bot.\nRCON: `{response}`")
        else:
            await callback.message.answer(f"✅ CT Bot added.\nRCON: `{response}`")
    elif action == "removebots":
        response = rcon.remove_bots()
        if "Error" in response:
            await callback.message.answer(f"❌ Failed to remove bots.\nRCON: `{response}`")
        else:
            await callback.message.answer(f"✅ All bots removed.\nRCON: `{response}`")
    elif action == "warmup_end":
        response = rcon.execute("mp_warmup_end")
        if "Error" in response:
            await callback.message.answer(f"❌ Failed to end warmup.\nRCON: `{response}`")
        else:
            await callback.message.answer(f"🔥 Warmup ended.")
    elif action == "warmup_start":
        response = rcon.execute("mp_warmuptime 90; mp_warmup_pausetimer 0; mp_warmup_start")
        if "Error" in response:
            await callback.message.answer(f"❌ Failed to start warmup.\nRCON: `{response}`")
        else:
            await callback.message.answer(f"⏳ Warmup started.")
    elif action == "status":
        await send_status(callback.message)
    elif action == "logs":
        await send_logs(callback.message)
    elif action == "enable_rr":
        cmd = config.GAME_MODES.get("🎲 Random Rounds")
        if cmd:
            response = rcon.execute(cmd)
            if "Error" in response:
                await callback.message.answer(f"❌ Failed to enable Random Rounds.\nRCON: `{response}`")
            else:
                await callback.message.answer(f"🎲 Random Rounds enabled.")
        else:
            await callback.message.answer("❌ Random Rounds mode not found in config.")
    elif action == "disable_rr":
        response = rcon.execute("exec settings/disable_random_round.cfg")
        if "Error" in response:
            await callback.message.answer(f"❌ Failed to disable Random Rounds.\nRCON: `{response}`")
        else:
            await callback.message.answer(f"🎲 Random Rounds disabled.")
    
    await callback.answer()

async def send_status(message: types.Message):
    await message.answer("🔄 Fetching server status...")
    try:
        info = rcon.get_full_info()
        status_text = info.get("status", "")
        
        hostname = "Unknown"
        # import re # Already imported globally
        hostname_match = re.search(r"hostname\s*:\s*(.*)", status_text)
        if hostname_match: hostname = hostname_match.group(1).strip()
        if hostname == "Counter-Strike 2" or hostname == "Unknown": hostname = config.CS2_SERVERNAME
        
        ip = "Unknown"
        ip_match = re.search(r"udp/ip\s*:\s*(.*)", status_text)
        if ip_match: 
            full_ip_str = ip_match.group(1).strip()
            # Try to extract public IP
            public_match = re.search(r"\(public\s+([^\)]+)\)", full_ip_str)
            if public_match:
                ip = public_match.group(1)
            else:
                # Fallback to the first part (usually local IP)
                ip = full_ip_str.split()[0]
        
        map_name = "Unknown"
        map_match = re.search(r"loaded spawngroup\(\s*1\)\s*:\s*SV:\s*\[\d+:\s*([^|]+)\s*\|", status_text)
        if map_match: map_name = map_match.group(1).strip()
        
        password = "None"
        pass_raw = info.get("password", "")
        pass_match = re.search(r'sv_password\s*=\s*(.*)', pass_raw)
        if pass_match: 
            val = pass_match.group(1).strip().strip('"')
            password = val if val else config.CS2_PASSWORD
        else:
             password = config.CS2_PASSWORD
        
        g_type = -1
        g_mode = -1
        type_match = re.search(r'game_type\s*=\s*(\d+)', info.get("game_type", ""))
        if type_match: g_type = int(type_match.group(1))
        mode_match = re.search(r'game_mode\s*=\s*(\d+)', info.get("game_mode", ""))
        if mode_match: g_mode = int(mode_match.group(1))
        
        mode_name = config.MODE_LOOKUP.get((g_type, g_mode), f"Type: {g_type}, Mode: {g_mode}")
        
        players = []
        player_count_match = re.search(r"players\s*:\s*(\d+)\s+humans", status_text)
        player_count = player_count_match.group(1) if player_count_match else "?"
        player_matches = re.finditer(r"^\s*(\d+)\s+([^\s]+).*\s+'([^']+)'", status_text, re.MULTILINE)
        for m in player_matches:
            if m.group(2) != 'BOT':
                players.append(m.group(3))
            
        msg = (
            f"✅ **Server is running**\n\n"
            f"📛 **Name:** `{hostname}`\n"
            f"🔑 **Password:** `{password}`\n"
            f"🗺 **Map:** `{map_name}`\n"
            f"🎮 **Mode:** `{mode_name}`\n"
            f"🌐 **IP:** `{ip}`\n\n"
            f"👥 **Players ({player_count}):**\n"
        )
        if players:
            for p in players: msg += f"- {p}\n"
        else:
            msg += "- No players online"

        # Quick Connect Command
        connect_cmd = f"connect {ip}"
        if password and password != "None":
            connect_cmd += f"; password {password}"
            
        msg += f"\n\n🚀 **Quick Connect:**\n`{connect_cmd}`"

        await message.answer(msg, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Error fetching status: {e}")

async def send_logs(message: types.Message):
    # Search for logs in /cs2-data/game/csgo and /cs2-data/game/csgo/logs
    # Note: Volume mounted at /cs2-data
    log_dirs = ["/cs2-data/game/csgo", "/cs2-data/game/csgo/logs"]
    files = []
    for d in log_dirs:
        if os.path.exists(d):
            files.extend(glob.glob(os.path.join(d, "*.log")))
    
    if not files:
        await message.answer("❌ No log files found.")
        return

    # Sort by modification time, newest first
    latest_file = max(files, key=os.path.getmtime)
    
    try:
        # Generate report
        report = generate_report(latest_file)
        await message.answer(report, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Error generating report: {e}")

@router.message(Command("map"))
async def cmd_map(message: types.Message, command: CommandObject = None):
    if not is_admin(message): return
    
    # If arguments provided, change map
    if command and command.args:
        map_arg = command.args.strip()
        
        # Check if it's a direct workshop command
        if map_arg.startswith("host_workshop_map"):
            response = rcon.execute(map_arg)
        else:
            # Standard map change
            response = rcon.change_map(map_arg)
            
        if "Error" in response:
            await message.answer(f"❌ Failed to change map.\nRCON: `{response}`")
        else:
            await message.answer(f"✅ Changing map to `{map_arg}`...")
        return

    current_mode = get_current_mode_name()
    msg = "🗺 **Choose a map:**"
    if current_mode:
        msg += f"\n(Filtered for **{current_mode}**)"
    await message.answer(msg, reply_markup=get_maps_keyboard(current_mode, 0), parse_mode="Markdown")

@router.callback_query(lambda c: c.data and c.data.startswith('map:'))
async def process_map_callback(callback_query: types.CallbackQuery):
    if not is_admin(callback_query): return
    map_code = callback_query.data.split(':')[1]
    
    # Check if it's a workshop map
    is_workshop = False
    workshop_id = None
    
    if map_code.startswith("workshop/"):
        is_workshop = True
        try:
            workshop_id = map_code.split('/')[1]
        except IndexError:
            await callback_query.answer("Invalid workshop map format", show_alert=True)
            return

    await callback_query.answer(f"Changing map to {map_code}...")
    
    if is_workshop and workshop_id:
        response = rcon.execute(f"host_workshop_map {workshop_id}")
    else:
        response = rcon.change_map(map_code)
    
    if "Error" in response:
         await callback_query.message.answer(f"❌ Failed to change map: {response}")
    else:
         await callback_query.message.answer(f"✅ Map changed to {map_code}")

@router.callback_query(lambda c: c.data and c.data.startswith('maps:page:'))
async def process_map_pagination_callback(callback_query: types.CallbackQuery):
    if not is_admin(callback_query): return
    parts = callback_query.data.split(':')
    # maps:page:{page}:{mode}
    page = int(parts[2])
    game_mode = parts[3] if len(parts) > 3 else None
    
    await callback_query.message.edit_reply_markup(reply_markup=get_maps_keyboard(game_mode, page))
    await callback_query.answer()

@router.message(Command("mode"))
async def cmd_mode(message: types.Message):
    if not is_admin(message): return
    await message.answer("🎮 **Choose a game mode:**", reply_markup=get_modes_keyboard())

@router.callback_query(lambda c: c.data and c.data.startswith('mode:'))
async def process_mode_callback(callback_query: types.CallbackQuery):
    if not is_admin(callback_query): return
    mode_name = callback_query.data.split(':', 1)[1]
    
    mode_command = config.GAME_MODES.get(mode_name)
    if not mode_command:
        await callback_query.answer("❌ Unknown mode", show_alert=True)
        return

    await callback_query.answer(f"Changing mode to {mode_name}...")
    
    # Get available maps for this mode
    available_maps = config.MODE_MAPS.get(mode_name, [])
    
    # Auto-select a map if available
    selected_map = None
    map_arg = None
    
    if mode_name == "Casual":
        selected_map = "de_dust2"
        map_arg = "de_dust2"
    elif available_maps:
        # For Competitive and Random Rounds, pick from the main pool (first 8 maps)
        if mode_name in ["Competitive", "🎲 Random Rounds"] and len(available_maps) >= 8:
            pool = available_maps[:8]
        else:
            pool = available_maps
            
        selected_map = random.choice(pool)
        # Resolve to workshop path if it's a workshop map
        map_arg = config.WORKSHOP_MAPS.get(selected_map, selected_map)
    
    # Change mode (and map if selected)
    response = rcon.change_mode(mode_command, map_arg)
    
    if "Error" in response:
        await callback_query.message.answer(f"❌ Failed to change mode.\nRCON: `{response}`", parse_mode="Markdown")
    else:
        safe_mode_name = mode_name.replace("_", "\\_")
        msg = f"✅ Mode changed to **{safe_mode_name}**"
        if selected_map:
            safe_map_name = selected_map.replace("_", "\\_")
            msg += f"\n🗺 Map set to: **{safe_map_name}**"
        else:
            msg += "\n(No specific map selected, keeping current)"
            
        # Prompt for map selection (filtered for the new mode)
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🗺 Change Map", callback_data=f"menu:map:{mode_name}")]
        ])
        await callback_query.message.answer(f"{msg}\n\nSelect a different map for this mode:", reply_markup=keyboard, parse_mode="Markdown")

@router.message(Command("kick"))
async def cmd_kick(message: types.Message):
    if not is_admin(message): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.answer("Usage: /kick <player_name>")
    player_name = args[1]
    response = rcon.kick_player(player_name)
    if "Error" in response:
        await message.answer(f"❌ Failed to kick {player_name}.\nRCON: `{response}`", parse_mode="Markdown")
    else:
        await message.answer(f"✅ Kicked {player_name}.\nRCON: `{response}`", parse_mode="Markdown")

@router.message(Command("addt"))
async def cmd_addt(message: types.Message):
    if not is_admin(message): return
    response = rcon.add_bot("t")
    if "Error" in response:
        await message.answer(f"❌ Failed to add T Bot.\nRCON: `{response}`")
    else:
        await message.answer(f"✅ T Bot added.\nRCON: `{response}`")

@router.message(Command("addct"))
async def cmd_addct(message: types.Message):
    if not is_admin(message): return
    response = rcon.add_bot("ct")
    if "Error" in response:
        await message.answer(f"❌ Failed to add CT Bot.\nRCON: `{response}`")
    else:
        await message.answer(f"✅ CT Bot added.\nRCON: `{response}`")

@router.message(Command("removebots"))
async def cmd_removebots(message: types.Message):
    if not is_admin(message): return
    response = rcon.remove_bots()
    if "Error" in response:
        await message.answer(f"❌ Failed to remove bots.\nRCON: `{response}`")
    else:
        await message.answer(f"✅ All bots removed.\nRCON: `{response}`")

@router.message(Command("restart"))
async def cmd_restart(message: types.Message):
    if not is_admin(message): return
    response = rcon.execute("mp_restartgame 1")
    if "Error" in response:
        await message.answer(f"❌ Failed to restart match.\nRCON: `{response}`")
    else:
        await message.answer(f"✅ Match restarting...\nRCON: `{response}`")
