import re
import os

def parse_readme():
    readme_path = 'README_cs2Server_info.md'
    output_txt_path = 'maps_by_mode.txt'
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all mode sections
    # Modes are marked by #### mg_...
    mode_sections = re.split(r'#### (mg_\w+)', content)
    
    maps_by_mode = {}
    workshop_maps = {} # name -> id
    
    # Skip the first split part (before first mode)
    # The split results in [preamble, mode_name, mode_content, mode_name, mode_content...]
    for i in range(1, len(mode_sections), 2):
        mode_name = mode_sections[i]
        mode_content = mode_sections[i+1]
        
        maps_by_mode[mode_name] = []
        
        # Regex to find maps in the table structure
        # We look for the map name and the command in the <sup><sub> tag
        # Pattern for Workshop maps: <a href="...">map_name</a><br><sup><sub>host_workshop_map ID</sub></sup>
        # Pattern for Standard maps: map_name<br><sup><sub>changelevel map_name</sub></sup>
        
        # Let's try a generic approach to capture the cell content
        # Each map is in a <table align="left">...</table> block
        cells = re.findall(r'<table align="left">.*?</table>', mode_content, re.DOTALL)
        
        for cell in cells:
            # Extract map name
            # It could be inside an <a> tag or just text
            name_match = re.search(r'<tr><td>(?:<a href="[^"]+">)?([^<]+)(?:</a>)?<br>', cell)
            if not name_match:
                continue
            map_name = name_match.group(1).strip()
            
            # Extract command
            cmd_match = re.search(r'<sup><sub>(.*?)</sub></sup>', cell)
            if not cmd_match:
                continue
            command = cmd_match.group(1).strip()
            
            maps_by_mode[mode_name].append({
                'name': map_name,
                'command': command
            })
            
            # If it's a workshop map, store the ID
            ws_match = re.search(r'host_workshop_map\s+(\d+)', command)
            if ws_match:
                workshop_id = ws_match.group(1)
                workshop_maps[map_name] = workshop_id

    # Write to maps_by_mode.txt
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        for mode, maps in maps_by_mode.items():
            f.write(f"Mode: {mode}\n")
            for m in maps:
                f.write(f"  - {m['name']} ({m['command']})\n")
            f.write("\n")
            
    print(f"Updated {output_txt_path}")
    
    # Print WORKSHOP_MAPS dictionary for config.py
    print("\nGenerated WORKSHOP_MAPS dictionary:")
    print("WORKSHOP_MAPS = {")
    for name, ws_id in workshop_maps.items():
        print(f'    "{name}": "workshop/{ws_id}/{name}",')
    print("}")

if __name__ == "__main__":
    parse_readme()
