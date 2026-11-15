# wow-forever-deck

Play World of Warcraft: Forever on the Steam Deck straight from the Steam library.

- Adds **World of Warcraft Forever** to your library with cover art, background and logo.
- One press starts Battle.net and goes straight into the game. No clicking Play in the launcher.
- Optional **DictateKeys** add-on so [deck-dictate](https://github.com/mariojankovic/deck-dictate) voice chat opens the chat box by itself.

## Why the launcher

A shortcut to `Battle.net.exe --exec="launch WoWF"` should start the game, but on a cold start Battle.net is still logging in when the command arrives, so it only selects WoW and waits for you to click Play.

The launcher starts Battle.net with the command, waits 15 seconds, then sends the command again to the running Battle.net, which then launches the game. Battle.net stays the foreground process, so Steam treats it as the running game (overlay, Game Mode focus and the Steam Input layout all work).

## Requirements

- Battle.net installed as a non-Steam game in a Proton prefix (for example with [NonSteamLaunchers](https://github.com/moraroy/NonSteamLaunchers-On-Steam-Deck)), and logged in.
- WoW Forever installed through Battle.net.

## Install

In Desktop Mode, open Konsole:

```bash
git clone https://github.com/mariojankovic/wow-forever-deck.git ~/wow-forever-deck
```

```bash
python3 ~/wow-forever-deck/install.py --restart-steam
```

Add `--dictate-keys` if you use deck-dictate. Run with `--dry-run` first to see which Battle.net prefix and Steam user it found.

The installer:

1. Finds the Proton prefix that has Battle.net (and WoW Forever, if there are several).
2. Copies `launch-wowf.bat` and `wowf-delay.bat` to that prefix's `C:\`.
3. Adds or updates the library shortcut (runs the launcher through `cmd.exe` in the same prefix) and sets it to Proton Experimental.
4. Downloads library artwork from SteamGridDB.

Steam has to be closed while the shortcut is written, `--restart-steam` does that for you. In Game Mode Steam comes back by itself; in Desktop Mode open it again.

## Options

| Flag | What it does |
|---|---|
| `--restart-steam` | Close Steam if it is running. |
| `--dictate-keys` | Install the DictateKeys add-on. |
| `--no-art` | Skip the artwork download. |
| `--proton <name>` | Compatibility tool, default `proton_experimental`. |
| `--dry-run` | Only print what it found. |

## DictateKeys add-on

Binds **F12** to WoW's **Open Chat** each time you log in. You never press F12 yourself: deck-dictate taps it right before pasting, so if chat is closed it opens, and if chat is already open nothing happens (keybinds don't fire while typing).

The binding is set for the session only, it doesn't overwrite your saved keybinds.

## Troubleshooting

- **Battle.net opens but the game doesn't start:** Battle.net needed longer than 15 seconds to log in. Raise the number in `wowf-delay.bat` (`ping -n 16` waits about 15 seconds) and run the installer again.
- **Nothing happens at all:** check the shortcut's compatibility setting is Proton Experimental.
- **Wrong Battle.net install picked:** run with `--dry-run` to see which prefix was found.

## Credits

Library artwork from [SteamGridDB](https://www.steamgriddb.com/game/33707) contributors. World of Warcraft is a trademark of Blizzard Entertainment. This project is not affiliated with Blizzard or Valve.

## License

MIT
