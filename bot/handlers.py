from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re
import html

import config
import database as db
import rcon_client as rcon
import keyboards as kb

router = Router()


# ── FSM States ──────────────────────────────────────────────────────

class AddServer(StatesGroup):
    name = State()
    host = State()
    password = State()


class WaitInput(StatesGroup):
    broadcast = State()
    kick = State()
    rcon_cmd = State()


# ── Helpers ─────────────────────────────────────────────────────────

def _srv(server: dict):
    """Return (host, port, rcon_password) tuple from a server dict."""
    return server["host"], server["port"], server["rcon_password"]


def _rcon(server: dict, command: str) -> str:
    """Execute an RCON command on the given server, return text result."""
    try:
        return rcon.execute(*_srv(server), command)
    except Exception as e:
        return f"Error: {e}"


# ── /start ──────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    db.ensure_user(uid, message.from_user.username)

    servers = db.get_user_servers(uid)
    if servers:
        await message.answer("Your servers:", reply_markup=kb.servers_list(servers))
    else:
        await message.answer(
            "You have no servers yet. Add one to get started!",
            reply_markup=kb.no_servers(),
        )
    await message.answer("Menu", reply_markup=kb.reply_menu())


@router.message(F.text.lower() == "menu")
async def cmd_menu(message: types.Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    db.ensure_user(uid, message.from_user.username)
    servers = db.get_user_servers(uid)
    if servers:
        await message.answer("Your servers:", reply_markup=kb.servers_list(servers))
    else:
        await message.answer("No servers yet.", reply_markup=kb.no_servers())


# ── Add server flow ────────────────────────────────────────────────

@router.callback_query(F.data == "add_server")
async def cb_add_server(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddServer.name)
    await cb.message.answer("Enter a name for this server (e.g. My CS2):", reply_markup=kb.cancel_keyboard())
    await cb.answer()


@router.message(AddServer.name, F.text)
async def on_server_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddServer.host)
    await message.answer("Enter server IP and port (e.g. 123.45.67.89:27015):", reply_markup=kb.cancel_keyboard())


@router.message(AddServer.host, F.text)
async def on_server_host(message: types.Message, state: FSMContext):
    text = message.text.strip()
    # Parse host:port
    if ":" in text:
        parts = text.rsplit(":", 1)
        host = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            return await message.answer("Invalid port. Enter host:port (e.g. 123.45.67.89:27015):")
    else:
        host = text
        port = 27015

    await state.update_data(host=host, port=port)
    await state.set_state(AddServer.password)
    await message.answer("Enter RCON password:", reply_markup=kb.cancel_keyboard())


@router.message(AddServer.password, F.text)
async def on_server_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    host = data["host"]
    port = data["port"]
    rcon_pw = message.text.strip()

    # Test connection
    await message.answer("Testing RCON connection...")
    ok, info = rcon.test_connection(host, port, rcon_pw)

    if not ok:
        await message.answer(
            f"Connection failed: {info}\n\n"
            "Check IP, port and RCON password. Try again:",
            reply_markup=kb.cancel_keyboard(),
        )
        return  # stay in password state so user can retry

    uid = message.from_user.id
    db.ensure_user(uid, message.from_user.username)
    server_id = db.add_server(uid, name, host, port, rcon_pw)
    await state.clear()

    await message.answer(
        f"Server <b>{html.escape(name)}</b> added! ({host}:{port})",
        parse_mode="HTML",
        reply_markup=kb.server_panel(server_id),
    )


# ── Cancel input ────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel_input")
async def cb_cancel_input(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer("Cancelled.")
    uid = cb.from_user.id
    servers = db.get_user_servers(uid)
    if servers:
        await cb.message.answer("Your servers:", reply_markup=kb.servers_list(servers))
    await cb.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Cancelled.")


# ── Back to server list ─────────────────────────────────────────────

@router.callback_query(F.data == "back_servers")
async def cb_back_servers(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    uid = cb.from_user.id
    servers = db.get_user_servers(uid)
    if servers:
        await cb.message.edit_text("Your servers:", reply_markup=kb.servers_list(servers))
    else:
        await cb.message.edit_text("No servers yet.", reply_markup=kb.no_servers())
    await cb.answer()


# ── Select server → panel ───────────────────────────────────────────

@router.callback_query(F.data.startswith("srv:"))
async def cb_select_server(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    server_id = int(cb.data.split(":")[1])
    server = db.get_server(server_id, cb.from_user.id)
    if not server:
        await cb.answer("Server not found", show_alert=True)
        return
    text = f"<b>{html.escape(server['name'])}</b>\n{server['host']}:{server['port']}"
    try:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=kb.server_panel(server_id))
    except Exception:
        await cb.message.answer(text, parse_mode="HTML", reply_markup=kb.server_panel(server_id))
    await cb.answer()


# ── Server actions (s:{id}:{action}) ───────────────────────────────

@router.callback_query(F.data.regexp(r"^s:\d+:\w"))
async def cb_server_action(cb: types.CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    server_id = int(parts[1])
    action = parts[2]
    server = db.get_server(server_id, cb.from_user.id)
    if not server:
        await cb.answer("Server not found", show_alert=True)
        return

    # ── Status ──
    if action == "status":
        await cb.answer("Fetching...")
        raw = _rcon(server, "status")
        if raw.startswith("Error"):
            await cb.message.answer(f"Error:\n<code>{html.escape(raw)}</code>", parse_mode="HTML")
            return

        hostname = "Unknown"
        m = re.search(r"hostname\s*:\s*(.*)", raw)
        if m:
            hostname = m.group(1).strip()

        map_name = "Unknown"
        m = re.search(r"map\s*:\s*(\S+)", raw)
        if m:
            map_name = m.group(1)

        players_m = re.search(r"players\s*:\s*(\d+)\s+humans", raw)
        player_count = players_m.group(1) if players_m else "?"

        player_names = []
        for pm in re.finditer(r"^\s*\d+\s+(\S+).*\s+'([^']+)'", raw, re.MULTILINE):
            if pm.group(1) != "BOT":
                player_names.append(pm.group(2))

        msg = (
            f"<b>{html.escape(hostname)}</b>\n"
            f"Map: <b>{html.escape(map_name)}</b>\n"
            f"Players: <b>{player_count}</b>\n"
        )
        if player_names:
            msg += "\n".join(f"- {html.escape(n)}" for n in player_names)
        else:
            msg += "No human players"

        msg += f"\n\n<code>connect {server['host']}:{server['port']}</code>"
        await cb.message.answer(msg, parse_mode="HTML", reply_markup=kb.server_panel(server_id))

    # ── Maps ──
    elif action == "maps":
        await cb.message.answer("Choose a map:", reply_markup=kb.maps_keyboard(server_id, None, 0))
        await cb.answer()

    # ── Modes ──
    elif action == "modes":
        await cb.message.answer("Choose a mode:", reply_markup=kb.modes_keyboard(server_id))
        await cb.answer()

    # ── Restart ──
    elif action == "restart":
        result = _rcon(server, "mp_restartgame 1")
        await cb.message.answer(f"Restart: {result or 'ok'}")
        await cb.answer()

    # ── Warmup ──
    elif action == "warmup_on":
        _rcon(server, "mp_warmuptime 90; mp_warmup_pausetimer 0; mp_warmup_start")
        await cb.message.answer("Warmup started")
        await cb.answer()

    elif action == "warmup_off":
        _rcon(server, "mp_warmup_end")
        await cb.message.answer("Warmup ended")
        await cb.answer()

    # ── Bots ──
    elif action == "addt":
        _rcon(server, "bot_difficulty 3; bot_add_t")
        await cb.message.answer("T bot added")
        await cb.answer()

    elif action == "addct":
        _rcon(server, "bot_difficulty 3; bot_add_ct")
        await cb.message.answer("CT bot added")
        await cb.answer()

    elif action == "kickbots":
        _rcon(server, "bot_kick")
        await cb.message.answer("Bots removed")
        await cb.answer()

    # ── Broadcast ──
    elif action == "broadcast":
        await state.set_state(WaitInput.broadcast)
        await state.update_data(server_id=server_id)
        await cb.message.answer("Enter message to broadcast:", reply_markup=kb.cancel_keyboard())
        await cb.answer()

    # ── Kick player ──
    elif action == "kick":
        await state.set_state(WaitInput.kick)
        await state.update_data(server_id=server_id)
        await cb.message.answer("Enter player name to kick:", reply_markup=kb.cancel_keyboard())
        await cb.answer()

    # ── Raw RCON command ──
    elif action == "rcon":
        await state.set_state(WaitInput.rcon_cmd)
        await state.update_data(server_id=server_id)
        await cb.message.answer("Enter RCON command:", reply_markup=kb.cancel_keyboard())
        await cb.answer()

    # ── Delete ──
    elif action == "delete":
        await cb.message.answer(
            f"Delete <b>{html.escape(server['name'])}</b>?",
            parse_mode="HTML",
            reply_markup=kb.confirm_delete(server_id),
        )
        await cb.answer()


# ── Delete confirm ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("del_yes:"))
async def cb_del_yes(cb: types.CallbackQuery):
    server_id = int(cb.data.split(":")[1])
    db.delete_server(server_id, cb.from_user.id)
    await cb.answer("Deleted")
    servers = db.get_user_servers(cb.from_user.id)
    if servers:
        await cb.message.edit_text("Your servers:", reply_markup=kb.servers_list(servers))
    else:
        await cb.message.edit_text("No servers yet.", reply_markup=kb.no_servers())


# ── Map change callback ────────────────────────────────────────────

@router.callback_query(F.data.startswith("map:"))
async def cb_change_map(cb: types.CallbackQuery):
    parts = cb.data.split(":", 2)
    server_id = int(parts[1])
    map_code = parts[2]

    server = db.get_server(server_id, cb.from_user.id)
    if not server:
        await cb.answer("Server not found", show_alert=True)
        return

    if map_code.startswith("workshop/"):
        workshop_id = map_code.split("/")[1]
        result = _rcon(server, f"host_workshop_map {workshop_id}")
    else:
        result = _rcon(server, f"changelevel {map_code}")

    if result.startswith("Error"):
        await cb.message.answer(f"Failed: {result}")
    else:
        await cb.message.answer(f"Map changed to {map_code}")
    await cb.answer()


# ── Map pagination ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mpage:"))
async def cb_map_page(cb: types.CallbackQuery):
    parts = cb.data.split(":")
    server_id = int(parts[1])
    page = int(parts[2])
    mode = parts[3] if len(parts) > 3 and parts[3] else None
    await cb.message.edit_reply_markup(reply_markup=kb.maps_keyboard(server_id, mode, page))
    await cb.answer()


# ── Mode change callback ───────────────────────────────────────────

@router.callback_query(F.data.startswith("mode:"))
async def cb_change_mode(cb: types.CallbackQuery):
    parts = cb.data.split(":", 2)
    server_id = int(parts[1])
    mode_name = parts[2]

    server = db.get_server(server_id, cb.from_user.id)
    if not server:
        await cb.answer("Server not found", show_alert=True)
        return

    cmd = config.GAME_MODES.get(mode_name)
    if not cmd:
        await cb.answer("Unknown mode", show_alert=True)
        return

    result = _rcon(server, cmd)
    if result.startswith("Error"):
        await cb.message.answer(f"Failed: {result}")
    else:
        await cb.message.answer(f"Mode set to {mode_name}")

    # Show map selection for this mode
    maps_in_mode = config.MODE_MAPS.get(mode_name)
    if maps_in_mode:
        await cb.message.answer("Choose a map for this mode:", reply_markup=kb.maps_keyboard(server_id, mode_name, 0))
    await cb.answer()


# ── Text input handlers (broadcast, kick, rcon) ────────────────────

@router.message(WaitInput.broadcast, F.text)
async def on_broadcast(message: types.Message, state: FSMContext):
    data = await state.get_data()
    server = db.get_server(data["server_id"], message.from_user.id)
    await state.clear()
    if not server:
        return await message.answer("Server not found.")
    result = _rcon(server, f'say "{message.text.strip()}"')
    await message.answer(f"Broadcast sent. {result}")


@router.message(WaitInput.kick, F.text)
async def on_kick(message: types.Message, state: FSMContext):
    data = await state.get_data()
    server = db.get_server(data["server_id"], message.from_user.id)
    await state.clear()
    if not server:
        return await message.answer("Server not found.")
    result = _rcon(server, f'kick "{message.text.strip()}"')
    await message.answer(f"Kick: {result or 'ok'}")


@router.message(WaitInput.rcon_cmd, F.text)
async def on_rcon_cmd(message: types.Message, state: FSMContext):
    data = await state.get_data()
    server = db.get_server(data["server_id"], message.from_user.id)
    await state.clear()
    if not server:
        return await message.answer("Server not found.")
    result = _rcon(server, message.text.strip())
    text = result if result else "(empty response)"
    # Truncate long responses
    if len(text) > 4000:
        text = text[:4000] + "\n...(truncated)"
    await message.answer(f"<code>{html.escape(text)}</code>", parse_mode="HTML")
