from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import bot_config as config

def get_maps_keyboard(mode, page=0):
    if mode in config.MODE_MAPS:
        all_maps = config.MODE_MAPS[mode]
    else:
        # Fallback to all maps (values of MAPS dict)
        all_maps = list(config.MAPS.values())
        
    # Build lookup dictionaries
    NAME_TO_CODE = {**config.MAPS, **config.WORKSHOP_MAPS}
    CODE_TO_NAME = {v: k for k, v in NAME_TO_CODE.items()}
    

    # Custom pagination for Competitive/Random Rounds
    if mode in ["Competitive", "🎲 Random Rounds"]:
        if page == 0:
            start = 0
            end = 8
        else:
            # Page 1 starts after the first 8 maps
            # Page 1: 8 to 8+18=26
            # Page 2: 26 to 26+18=44
            start = 8 + (page - 1) * 18
            end = start + 18
    else:
        PAGE_SIZE = 18
        start = page * PAGE_SIZE
        end = start + PAGE_SIZE
        
    current_maps = all_maps[start:end]
    
    keyboard = []
    row = []
    for item in current_maps:
        # Determine Name and Code
        if item in NAME_TO_CODE:
            # Item is a Name
            map_name = item
            map_code = NAME_TO_CODE[item]
        elif item in CODE_TO_NAME:
            # Item is a Code
            map_name = CODE_TO_NAME[item]
            map_code = item
        else:
            # Fallback
            map_name = item
            map_code = item
            
        # Truncate name
        display_name = map_name[:20] + "..." if len(map_name) > 20 else map_name
        
        row.append(InlineKeyboardButton(text=display_name, callback_data=f"map:{map_code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    
    # Navigation
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"maps:page:{page-1}:{mode}"))
    if end < len(all_maps):
        nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"maps:page:{page+1}:{mode}"))
    
    if nav_row:
        keyboard.append(nav_row)
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_modes_keyboard():
    keyboard = []
    row = []
    for mode in config.GAME_MODES:
        row.append(InlineKeyboardButton(text=mode, callback_data=f"mode:{mode}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    
    # Add RR On/Off buttons at the bottom
    keyboard.append([
        InlineKeyboardButton(text="🎲 RR On", callback_data="menu:enable_rr"),
        InlineKeyboardButton(text="🎲 RR Off", callback_data="menu:disable_rr")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📊 Status", callback_data="menu:status"),
         InlineKeyboardButton(text="📂 Logs", callback_data="menu:logs")],
        [InlineKeyboardButton(text="🎮 Change Mode", callback_data="menu:mode"),
         InlineKeyboardButton(text="🗺 Change Map", callback_data="menu:map")],
        [InlineKeyboardButton(text="🔄 Restart", callback_data="menu:restart"),
         InlineKeyboardButton(text="⏳ Warmup On", callback_data="menu:warmup_start"),
         InlineKeyboardButton(text="🔥 Warmup Off", callback_data="menu:warmup_end")],
        [InlineKeyboardButton(text="🤖 Add T", callback_data="menu:addt"),
         InlineKeyboardButton(text="🤖 Add CT", callback_data="menu:addct"),
         InlineKeyboardButton(text="🚫 Clear Bots", callback_data="menu:removebots")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_reply_keyboard():
    keyboard = [
        [KeyboardButton(text="☰ Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
