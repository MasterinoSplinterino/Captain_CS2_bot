import re
import os

file_path = r"c:/Users/Kirill/Desktop/VS  MVP/cs2/cs2-data/game/csgo/gamemodes_server.txt"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Regex to find workshop maps: "workshop/ID/name"
matches = re.findall(r'"(workshop/\d+/\w+)"', content)

# Also find standard maps that are not in the main list, but let's focus on workshop first as requested.
# Actually, let's just get all unique maps that look like workshop maps.

unique_maps = sorted(list(set(matches)))

print("WORKSHOP_MAPS = {")
for map_path in unique_maps:
    # Extract name from path: workshop/12345/de_dust2 -> de_dust2
    parts = map_path.split("/")
    name = parts[-1]
    print(f'    "{name}": "{map_path}",')
print("}")
