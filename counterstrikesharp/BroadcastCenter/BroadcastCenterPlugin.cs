using CounterStrikeSharp.API;
using CounterStrikeSharp.API.Core;
using CounterStrikeSharp.API.Core.Attributes.Registration;
using CounterStrikeSharp.API.Modules.Commands;
using CounterStrikeSharp.API.Modules.Entities;
using CounterStrikeSharp.API.Modules.Entities.Constants;
using CounterStrikeSharp.API.Modules.Utils;

namespace CaptainCS2.BroadcastCenter;

[MinimumApiVersion(228)]
public sealed class BroadcastCenterPlugin : BasePlugin
{
    private const int MaxMessageLength = 256;

    public override string ModuleName => "BroadcastCenter";
    public override string ModuleDescription => "Adds css_broadcast_center to show a center-screen overlay";
    public override string ModuleVersion => "1.0.0";

    public override void Load(bool hotReload)
    {
        AddCommand("css_broadcast_center", "Show a center-screen banner", BroadcastCenterCommand);
    }

    private void BroadcastCenterCommand(CCSPlayerController? caller, CommandInfo command)
    {
        var rawText = command.ArgString?.Trim();
        if (string.IsNullOrEmpty(rawText))
        {
            command.ReplyToCommand("Usage: css_broadcast_center <text>");
            return;
        }

        var sanitized = Sanitize(rawText);
        if (sanitized.Length > MaxMessageLength)
        {
            sanitized = sanitized[..MaxMessageLength];
        }

        var payload = $"<span style=\"font-size:32px;color:#FFD54F;font-weight:600;text-shadow:2px 2px #000;\">{sanitized}</span>";
        var recipients = Broadcast(payload);

        command.ReplyToCommand($"Sent banner to {recipients} players.");
    }

    private static int Broadcast(string htmlPayload)
    {
        var sent = 0;
        foreach (var player in Utilities.GetPlayers())
        {
            if (!IsPlayable(player))
            {
                continue;
            }

            player.PrintToCenterHtml(htmlPayload);
            sent++;
        }

        return sent;
    }

    private static bool IsPlayable(CCSPlayerController? player)
    {
        return player is not null
            && player.IsValid
            && player.Connected == PlayerConnectedState.PlayerConnected
            && !player.IsBot;
    }

    private static string Sanitize(string value)
    {
        return value
            .Replace("&", "&amp;")
            .Replace("<", "&lt;")
            .Replace(">", "&gt;");
    }
}
