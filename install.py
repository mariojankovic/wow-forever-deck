#!/usr/bin/env python3
import argparse
import glob
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
STEAM = os.path.expanduser("~/.local/share/Steam")
NAME = "World of Warcraft Forever"
PRODUCT = "WoWF"
ART = {
    "p.png": "https://cdn2.steamgriddb.com/grid/1ccc0ad70725fbdef023f6c431881114.png",
    ".png": "https://cdn2.steamgriddb.com/grid/4e09bd41dcb70a21065f3ebdf67b605a.png",
    "_hero.png": "https://cdn2.steamgriddb.com/hero/c20ad4d76fe97759aa27a0c99bff6710.png",
    "_logo.png": "https://cdn2.steamgriddb.com/logo/5236d2d466e7a1d9785a33e298a58c3c.png",
}


def find_prefix():
    hits = glob.glob(f"{STEAM}/steamapps/compatdata/*/pfx/drive_c/Program Files (x86)/Battle.net/Battle.net.exe")
    if not hits:
        sys.exit("Battle.net not found in any Proton prefix. Install it as a non-Steam game first.")
    prefixes = [h.split("/pfx/")[0] for h in hits]
    with_wow = [p for p in prefixes if os.path.isdir(f"{p}/pfx/drive_c/Program Files (x86)/World of Warcraft/_forever_")]
    return (with_wow or prefixes)[0]


def find_user():
    users = glob.glob(f"{STEAM}/userdata/*/config/localconfig.vdf")
    if not users:
        sys.exit("No Steam user found.")
    return os.path.dirname(os.path.dirname(max(users, key=os.path.getmtime)))


def parse(d, i):
    out = []
    while True:
        t = d[i]
        i += 1
        if t == 8:
            return out, i
        j = d.index(b"\0", i)
        k = d[i:j]
        i = j + 1
        if t == 0:
            v, i = parse(d, i)
        elif t == 1:
            j = d.index(b"\0", i)
            v = d[i:j]
            i = j + 1
        elif t == 2:
            v = d[i:i + 4]
            i += 4
        else:
            raise ValueError(f"unsupported vdf type {t}")
        out.append((t, k, v))


def dump(items):
    b = b""
    for t, k, v in items:
        b += bytes([t]) + k + b"\0"
        b += dump(v) if t == 0 else (v + b"\0" if t == 1 else v)
    return b + b"\x08"


def read_shortcuts(path):
    if not os.path.exists(path):
        return b"", [(0, b"shortcuts", [])]
    raw = open(path, "rb").read()
    root, _ = parse(raw, 0)
    return raw, root


def write_shortcuts(path, raw, root):
    out = dump(root)
    if (not raw or raw.endswith(b"\x08\x08")) and not out.endswith(b"\x08\x08"):
        out += b"\x08"
    parse(out, 0)
    with open(path + ".tmp", "wb") as f:
        f.write(out)
    os.replace(path + ".tmp", path)


def shortcut_fields(appid, prefix):
    drive_c = f"{prefix}/pfx/drive_c"
    s = lambda v: v.encode()
    return [
        (2, b"appid", struct.pack("<I", appid)),
        (1, b"AppName", s(NAME)),
        (1, b"Exe", s(f'"{drive_c}/windows/system32/cmd.exe"')),
        (1, b"StartDir", s(f'"{drive_c}/"')),
        (1, b"icon", b""),
        (1, b"ShortcutPath", b""),
        (1, b"LaunchOptions", s(f'STEAM_COMPAT_DATA_PATH="{prefix}" %command% /c C:\\launch-wowf.bat')),
        (2, b"IsHidden", struct.pack("<I", 0)),
        (2, b"AllowDesktopConfig", struct.pack("<I", 1)),
        (2, b"AllowOverlay", struct.pack("<I", 1)),
        (2, b"OpenVR", struct.pack("<I", 0)),
        (2, b"Devkit", struct.pack("<I", 0)),
        (1, b"DevkitGameID", b""),
        (2, b"DevkitOverrideAppID", struct.pack("<I", 0)),
        (2, b"LastPlayTime", struct.pack("<I", 0)),
        (1, b"FlatpakAppID", b""),
        (0, b"tags", []),
    ]


def add_compat_tool(appid, tool):
    cfg_path = f"{STEAM}/config/config.vdf"
    cfg = open(cfg_path, encoding="utf-8").read()
    m = re.search(r'"CompatToolMapping"\s*\n(\t*)\{\n', cfg)
    if not m:
        print("CompatToolMapping not found, set Proton manually in the shortcut's properties")
        return
    depth, end = 1, m.end()
    while depth and end < len(cfg):
        c = cfg[end]
        depth += c == "{"
        depth -= c == "}"
        end += 1
    if f'"{appid}"' in cfg[m.end():end]:
        return
    ind = m.group(1) + "\t"
    block = (f'{ind}"{appid}"\n{ind}{{\n{ind}\t"name"\t\t"{tool}"\n'
             f'{ind}\t"config"\t\t""\n{ind}\t"priority"\t\t"250"\n{ind}}}\n')
    cfg = cfg[:m.end()] + block + cfg[m.end():]
    with open(cfg_path + ".tmp", "w", encoding="utf-8") as f:
        f.write(cfg)
    os.replace(cfg_path + ".tmp", cfg_path)


def steam_running():
    return subprocess.run(["pgrep", "-x", "steam"], capture_output=True).returncode == 0


def stop_steam():
    subprocess.Popen(["steam", "-shutdown"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        if not steam_running():
            return
        time.sleep(0.5)
    sys.exit("Steam did not close. Close it yourself and run again.")


def install_launcher(prefix):
    drive_c = f"{prefix}/pfx/drive_c"
    for name in ("launch-wowf.bat", "wowf-delay.bat"):
        with open(os.path.join(HERE, "launcher", name), "rb") as f:
            data = f.read().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        with open(f"{drive_c}/{name}", "wb") as f:
            f.write(data)


def install_addon(prefix):
    dst = f"{prefix}/pfx/drive_c/Program Files (x86)/World of Warcraft/_forever_/Interface/AddOns/DictateKeys"
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(os.path.join(HERE, "addon", "DictateKeys"), dst)
    print("installed DictateKeys add-on")


def install_art(grid, appid):
    os.makedirs(grid, exist_ok=True)
    for suffix, url in ART.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "wow-forever-deck"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            with open(f"{grid}/{appid}{suffix}", "wb") as f:
                f.write(data)
        except Exception as ex:
            print(f"could not download artwork {suffix}: {ex}")


def main():
    ap = argparse.ArgumentParser(description="Add WoW Forever to the Steam library on a Steam Deck")
    ap.add_argument("--dictate-keys", action="store_true", help="also install the DictateKeys add-on (F12 = Open Chat)")
    ap.add_argument("--no-art", action="store_true", help="skip downloading library artwork")
    ap.add_argument("--proton", default="proton_experimental", help="compatibility tool name")
    ap.add_argument("--restart-steam", action="store_true", help="close Steam automatically if it is running")
    ap.add_argument("--dry-run", action="store_true", help="only show what would happen")
    args = ap.parse_args()

    prefix = find_prefix()
    user = find_user()
    shortcuts_path = f"{user}/config/shortcuts.vdf"
    drive_c = f"{prefix}/pfx/drive_c"
    appid = zlib.crc32((f'"{drive_c}/windows/system32/cmd.exe"' + NAME).encode()) | 0x80000000
    print("Battle.net prefix:", prefix)
    print("Steam user:", os.path.basename(user))

    raw, root = read_shortcuts(shortcuts_path)
    shortcuts = root[0][2]
    existing = next((s for s in shortcuts if dict((k.lower(), v) for _, k, v in s[2]).get(b"appname") == NAME.encode()), None)
    if existing:
        appid = struct.unpack("<I", dict((k.lower(), v) for _, k, v in existing[2])[b"appid"])[0]
    print("Shortcut:", "update" if existing else "add", "app id", appid)

    if args.dry_run:
        return

    if steam_running():
        if not args.restart_steam:
            sys.exit("Steam is running. Close it first, or run again with --restart-steam.")
        stop_steam()

    install_launcher(prefix)
    if args.dictate_keys:
        install_addon(prefix)

    raw, root = read_shortcuts(shortcuts_path)
    shortcuts = root[0][2]
    fields = shortcut_fields(appid, prefix)
    if existing:
        for s in shortcuts:
            if dict((k.lower(), v) for _, k, v in s[2]).get(b"appname") == NAME.encode():
                keep = {k.lower(): (t, k, v) for t, k, v in s[2]}
                for t, k, v in fields:
                    if k.lower() in (b"exe", b"startdir", b"launchoptions"):
                        keep[k.lower()] = (t, keep.get(k.lower(), (t, k, v))[1], v)
                s[2][:] = list(keep.values())
    else:
        shortcuts.append((0, str(len(shortcuts)).encode(), fields))
    write_shortcuts(shortcuts_path, raw, root)
    add_compat_tool(appid, args.proton)
    if not args.no_art:
        install_art(f"{user}/config/grid", appid)

    print(f"Done. Start Steam and look for \"{NAME}\" in your library.")


if __name__ == "__main__":
    main()
