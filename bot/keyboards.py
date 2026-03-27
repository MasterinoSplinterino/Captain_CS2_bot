from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import config

PAGE_SIZE = 18


def reply_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Menu")]],
        resize_keyboard=True,
    )


# ── Main: server list ──────────────────────────────────────────────

def servers_list(servers: list[dict]):
    rows = []
    for s in servers:
        rows.append([InlineKeyboardButton(
            text=f"{s['name']}  ({s['host']}:{s['port']})",
            callback_data=f"srv:{s['id']}",
        )])
    rows.append([InlineKeyboardButton(text="+ Добавить сервер", callback_data="add_server")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def no_servers():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="+ Добавить сервер", callback_data="add_server")]
    ])


# ── Server control panel ───────────────────────────────────────────

def server_panel(server_id: int):
    p = f"s:{server_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Status", callback_data=f"{p}:status"),
         InlineKeyboardButton(text="RCON cmd", callback_data=f"{p}:rcon")],
        [InlineKeyboardButton(text="Change Map", callback_data=f"{p}:maps"),
         InlineKeyboardButton(text="Change Mode", callback_data=f"{p}:modes")],
        [InlineKeyboardButton(text="Restart", callback_data=f"{p}:restart"),
         InlineKeyboardButton(text="Warmup On", callback_data=f"{p}:warmup_on"),
         InlineKeyboardButton(text="Warmup Off", callback_data=f"{p}:warmup_off")],
        [InlineKeyboardButton(text="+ Bot T", callback_data=f"{p}:addt"),
         InlineKeyboardButton(text="+ Bot CT", callback_data=f"{p}:addct"),
         InlineKeyboardButton(text="Kick bots", callback_data=f"{p}:kickbots")],
        [InlineKeyboardButton(text="Broadcast", callback_data=f"{p}:broadcast"),
         InlineKeyboardButton(text="Kick player", callback_data=f"{p}:kick")],
        [InlineKeyboardButton(text="Delete server", callback_data=f"{p}:delete")],
        [InlineKeyboardButton(text="<< Back to servers", callback_data="back_servers")],
    ])


# ── Maps keyboard ──────────────────────────────────────────────────

def maps_keyboard(server_id: int, mode: str | None, page: int = 0):
    if mode and mode in config.MODE_MAPS:
        all_maps = config.MODE_MAPS[mode]
    else:
        all_maps = list(config.MAPS.keys())

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    current = all_maps[start:end]

    rows = []
    row = []
    for name in current:
        code = config.MAPS.get(name, name)
        display = name[:22] + ".." if len(name) > 24 else name
        row.append(InlineKeyboardButton(text=display, callback_data=f"map:{server_id}:{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="<< Prev", callback_data=f"mpage:{server_id}:{page - 1}:{mode or ''}"))
    if end < len(all_maps):
        nav.append(InlineKeyboardButton(text="Next >>", callback_data=f"mpage:{server_id}:{page + 1}:{mode or ''}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="<< Back", callback_data=f"srv:{server_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Modes keyboard ─────────────────────────────────────────────────

def modes_keyboard(server_id: int):
    rows = []
    row = []
    for mode_name in config.GAME_MODES:
        row.append(InlineKeyboardButton(text=mode_name, callback_data=f"mode:{server_id}:{mode_name}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="<< Back", callback_data=f"srv:{server_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── Confirm delete ──────────────────────────────────────────────────

def confirm_delete(server_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Yes, delete", callback_data=f"del_yes:{server_id}"),
         InlineKeyboardButton(text="Cancel", callback_data=f"srv:{server_id}")],
    ])


def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Cancel", callback_data="cancel_input")],
    ])
