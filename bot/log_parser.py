import re
import os

def parse_log_file(filepath):
    stats = {}  # steamid -> {name, kills, assists, deaths, damage, team}
    map_name = "Unknown"
    date_str = "Unknown"
    
    # Regex patterns
    # L 11/29/2025 - 18:50:23: "Player<2><STEAM_1:1:12345><TERRORIST>" killed "Bot<3><BOT><CT>" with "ak47"
    # Group 1: Name, 2: ID, 3: SteamID, 4: Team
    player_pattern = r'"([^"]+)<(\d+)><([^>]+)><([^>]+)>"'
    
    kill_pattern = re.compile(f'^L .+?: {player_pattern} killed {player_pattern}')
    assist_pattern = re.compile(f'^L .+?: {player_pattern} assisted killing {player_pattern}')
    # "Player<...>" attacked "Victim<...>" with "weapon" (damage "27")
    damage_pattern = re.compile(f'^L .+?: {player_pattern} attacked {player_pattern}.*?\(damage "(\d+)"\)')
    
    map_pattern = re.compile(r'Started map "([^"]+)"')
    time_pattern = re.compile(r'^L (\d{2}/\d{2}/\d{4} - \d{2}:\d{2}:\d{2})')

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Date/Time
                if date_str == "Unknown":
                    m = time_pattern.match(line)
                    if m: date_str = m.group(1)
                
                # Map
                if 'Started map' in line:
                    m = map_pattern.search(line)
                    if m: map_name = m.group(1)
                
                # Kill
                if " killed " in line:
                    m = kill_pattern.search(line)
                    if m:
                        # Attacker: groups 1-4
                        a_name, a_id, a_steam, a_team = m.group(1), m.group(2), m.group(3), m.group(4)
                        # Victim: groups 5-8
                        v_name, v_id, v_steam, v_team = m.group(5), m.group(6), m.group(7), m.group(8)
                        
                        # Update Attacker Kills
                        if a_steam not in stats: stats[a_steam] = {'name': a_name, 'kills': 0, 'assists': 0, 'deaths': 0, 'damage': 0, 'team': a_team}
                        stats[a_steam]['kills'] += 1
                        stats[a_steam]['name'] = a_name # Update name
                        stats[a_steam]['team'] = a_team
                        
                        # Update Victim Deaths
                        if v_steam not in stats: stats[v_steam] = {'name': v_name, 'kills': 0, 'assists': 0, 'deaths': 0, 'damage': 0, 'team': v_team}
                        stats[v_steam]['deaths'] += 1
                        stats[v_steam]['name'] = v_name
                        stats[v_steam]['team'] = v_team

                # Assist
                elif " assisted killing " in line:
                    m = assist_pattern.search(line)
                    if m:
                        a_name, a_id, a_steam, a_team = m.group(1), m.group(2), m.group(3), m.group(4)
                        if a_steam not in stats: stats[a_steam] = {'name': a_name, 'kills': 0, 'assists': 0, 'deaths': 0, 'damage': 0, 'team': a_team}
                        stats[a_steam]['assists'] += 1
                        stats[a_steam]['name'] = a_name
                        stats[a_steam]['team'] = a_team

                # Damage
                elif " attacked " in line and "(damage " in line:
                    m = damage_pattern.search(line)
                    if m:
                        a_name, a_id, a_steam, a_team = m.group(1), m.group(2), m.group(3), m.group(4)
                        dmg = int(m.group(9))
                        
                        if a_steam not in stats: stats[a_steam] = {'name': a_name, 'kills': 0, 'assists': 0, 'deaths': 0, 'damage': 0, 'team': a_team}
                        stats[a_steam]['damage'] += dmg
                        stats[a_steam]['name'] = a_name
                        stats[a_steam]['team'] = a_team

    except Exception as e:
        print(f"Error parsing log: {e}")
        return None, None, None

    return map_name, date_str, stats

def generate_report(filepath):
    map_name, date_str, stats = parse_log_file(filepath)
    
    if not stats:
        return "❌ Could not parse stats from the log file."

    # Group by team
    t_team = []
    ct_team = []
    other_team = []
    
    for steamid, data in stats.items():
        # Filter out BOTs if desired? User didn't say. But usually stats include bots.
        # If user wants only humans, we can check steamid format (BOT usually has 'BOT').
        # But user asked for "2 tables with teams", implying all players.
        
        if data['team'] == 'TERRORIST':
            t_team.append(data)
        elif data['team'] == 'CT':
            ct_team.append(data)
        else:
            other_team.append(data)
            
    # Sort by Kills (desc)
    t_team.sort(key=lambda x: x['kills'], reverse=True)
    ct_team.sort(key=lambda x: x['kills'], reverse=True)
    
    report = f"📅 **Date:** {date_str}\n🗺 **Map:** {map_name}\n\n"
    
    def format_table(team_name, players):
        if not players:
            return f"**{team_name}**: No players\n"
        
        # Header
        # Name | K | A | D | DMG
        # Using code block for alignment
        table = f"**{team_name}**\n```\n"
        table += f"{'Name':<15} {'K':<3} {'A':<3} {'D':<3} {'DMG':<5}\n"
        table += "-"*35 + "\n"
        for p in players:
            name = p['name'][:15] # Truncate name
            table += f"{name:<15} {p['kills']:<3} {p['assists']:<3} {p['deaths']:<3} {p['damage']:<5}\n"
        table += "```\n"
        return table

    report += format_table("👮 Counter-Terrorists", ct_team)
    report += "\n"
    report += format_table("🏴‍☠️ Terrorists", t_team)
    
    return report
