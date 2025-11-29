from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import bot_config as config

def get_maps_keyboard(page: int = 1, game_mode: str = None):
    keyboard = []
    
    # Filter maps if game_mode is provided
    if game_mode and game_mode in config.MODE_MAPS:
        allowed_maps = set(config.MODE_MAPS[game_mode])
        current_maps = {k: v for k, v in config.MAPS.items() if v in allowed_maps}
        current_workshop = {k: v for k, v in config.WORKSHOP_MAPS.items() if k in allowed_maps}
    else:
        current_maps = config.MAPS
        current_workshop = config.WORKSHOP_MAPS

    # Page 1: Main Maps (or Workshop if no Main Maps)
    if page == 1:
        row = []
        # If we have standard maps, show them
        if current_maps:
            for name, code in current_maps.items():
                row.append(InlineKeyboardButton(text=name, callback_data=f"map:{code}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row: keyboard.append(row)
            
            # Navigation to Workshop maps (only if there are any)
            if current_workshop:
                keyboard.append([InlineKeyboardButton(text="Next (Workshop) ➡️", callback_data=f"map_page:2:{game_mode}" if game_mode else "map_page:2")])
        
        # If NO standard maps but we HAVE workshop maps, show first page of workshop maps immediately
        elif current_workshop:
            # Sort workshop maps by name
            sorted_workshop = sorted(current_workshop.items(), key=lambda x: x[0])
            items_per_page = 10
            current_items = sorted_workshop[:items_per_page]
            
            for name, code in current_items:
                # Truncate name if too long
                display_name = name[:20] + "..." if len(name) > 20 else name
                row.append(InlineKeyboardButton(text=display_name, callback_data=f"map:{code}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row: keyboard.append(row)
            
            # Navigation for Workshop maps (if more than 1 page)
            if len(sorted_workshop) > items_per_page:
                cb_data = f"map_page:2:{game_mode}" if game_mode else "map_page:2"
                keyboard.append([InlineKeyboardButton(text="Next ➡️", callback_data=cb_data)])

    else:
        # Workshop Maps Pagination (Page 2+)
        # Sort workshop maps by name
        sorted_workshop = sorted(current_workshop.items(), key=lambda x: x[0])
        
        items_per_page = 10
        
        # If we started showing workshop maps on Page 1 (because no standard maps), 
        # then Page 2 is actually the 2nd page of workshop maps (index 1).
        # If we showed standard maps on Page 1, then Page 2 is the 1st page of workshop maps (index 0).
        
        if not current_maps and current_workshop:
            # Workshop maps started on Page 1
            workshop_page_index = page - 1
        else:
            # Workshop maps start on Page 2
            workshop_page_index = page - 2 
            
        start_idx = workshop_page_index * items_per_page
        end_idx = start_idx + items_per_page
        
        current_items = sorted_workshop[start_idx:end_idx]
        
        row = []
        for name, code in current_items:
            # Truncate name if too long
            display_name = name[:20] + "..." if len(name) > 20 else name
            row.append(InlineKeyboardButton(text=display_name, callback_data=f"map:{code}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row: keyboard.append(row)
        
        # Navigation
        nav_row = []
        if page > 1:
            prev_page = page - 1
            cb_data = f"map_page:{prev_page}:{game_mode}" if game_mode else f"map_page:{prev_page}"
            nav_row.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=cb_data))
        
        if end_idx < len(sorted_workshop):
            next_page = page + 1
            cb_data = f"map_page:{next_page}:{game_mode}" if game_mode else f"map_page:{next_page}"
            nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=cb_data))
            
        if nav_row: keyboard.append(nav_row)

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
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🗺 Change Map", callback_data="menu:map"),
         InlineKeyboardButton(text="🎮 Change Mode", callback_data="menu:mode")],
        [InlineKeyboardButton(text="🔄 Restart Match", callback_data="menu:restart")],
        [InlineKeyboardButton(text="🤖 Add T Bot", callback_data="menu:addt"),
         InlineKeyboardButton(text="🤖 Add CT Bot", callback_data="menu:addct")],
        [InlineKeyboardButton(text="🚫 Remove Bots", callback_data="menu:removebots")],
        [InlineKeyboardButton(text="📊 Status", callback_data="menu:status")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
