# BroadcastCenter Plugin

Small CounterStrikeSharp plugin that adds the console command `css_broadcast_center <text>`. The command renders the provided text as a center-screen banner for every connected player.

## Build

```powershell
cd counterstrikesharp/BroadcastCenter
dotnet build -c Release
```

The compiled `BroadcastCenterPlugin.dll` will be located under `bin/Release/net8.0/`.

## Deploy to the server container

1. Copy the DLL into the mounted plugin folder, e.g. `cs2-data/game/csgo/addons/counterstrikesharp/plugins/`.
2. Restart the CS2 server container or run `css_plugins load BroadcastCenterPlugin` in the server console.

## Usage

Send center banners via RCON/console:

```
css_broadcast_center The match starts in 2 minutes
```

You can now call the command from the Telegram bot (`Send Broadcast` button) to display urgent announcements for all players.
