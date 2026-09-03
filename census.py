#!/usr/bin/env python3
"""
census.py - file-path, item-script and sandbox-option census for a Project Zomboid mod set.

Answers the question descriptions cannot: which installed mods ship the SAME thing, and
therefore silently overwrite each other at load time.

Reads:  settings.json (next to this file) for the workshop and Zomboid paths
        the newest Zomboid\\Logs debug log for the running game build
Writes: census\\census.json   - full machine-readable result
        census\\census.txt    - the readable summary

Standard library only. Nothing is modified outside the census\\ folder.

    cd C:\\Users\\igor\\Zomboid\\pzmods
    python census.py
"""

import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "census")

# Paths the game reads from a mod. Everything else in a mod folder is inert.
MEDIA_ROOTS = ("lua", "scripts", "textures", "models", "models_x", "anims_x",
               "sound", "ui", "maps", "fileGuidTable.xml")


# ---------------------------------------------------------------- settings

def load_settings():
    with open(os.path.join(HERE, "settings.json"), encoding="utf-8") as f:
        s = json.load(f)
    return s["workshop"], s["zomboid"], s.get("gameVersion", "auto")


def game_build(zomboid, declared):
    """Read the build out of the game's own debug log, like pzmods does."""
    if declared and declared != "auto":
        return declared
    logs = os.path.join(zomboid, "Logs")
    if not os.path.isdir(logs):
        return None
    files = sorted(
        (os.path.join(logs, n) for n in os.listdir(logs) if n.lower().endswith(".txt")),
        key=os.path.getmtime, reverse=True)
    pat = re.compile(r"version=(\d+\.\d+(?:\.\d+)?)")
    for path in files[:6]:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = pat.search(line)
                    if m:
                        return m.group(1)
        except OSError:
            continue
    return None


def vtuple(s):
    out = []
    for part in s.split("."):
        out.append(int(part) if part.isdigit() else 0)
    return tuple(out + [0] * (3 - len(out)))[:3]


# ---------------------------------------------------------------- discovery

def find_mods(workshop, zomboid):
    """Yield (workshop_id, mod_folder_path). workshop_id is None for local mods."""
    content = os.path.join(workshop, "content", "108600")
    if os.path.isdir(content):
        for wid in os.listdir(content):
            item = os.path.join(content, wid)
            mods = os.path.join(item, "mods")
            base = mods if os.path.isdir(mods) else item
            if not os.path.isdir(base):
                continue
            for name in os.listdir(base):
                folder = os.path.join(base, name)
                if os.path.isdir(folder) and has_modinfo(folder):
                    yield wid, folder
    local = os.path.join(zomboid, "mods")
    if os.path.isdir(local):
        for name in os.listdir(local):
            folder = os.path.join(local, name)
            if os.path.isdir(folder) and has_modinfo(folder):
                yield None, folder


def has_modinfo(folder):
    if os.path.isfile(os.path.join(folder, "mod.info")):
        return True
    for name in os.listdir(folder):
        sub = os.path.join(folder, name)
        if os.path.isdir(sub) and os.path.isfile(os.path.join(sub, "mod.info")):
            return True
    return False


def read_modinfo(path):
    info = {}
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "=" in line:
                    k, _, v = line.partition("=")
                    info.setdefault(k.strip().lower(), v.strip())
    except OSError:
        pass
    return info


def active_dirs(folder, build):
    """
    The folders the game actually loads: common/ (or the root) plus the highest
    version folder that is not above the running build. Same rule pzmods uses.
    """
    dirs = []
    root_info = os.path.join(folder, "mod.info")
    versioned = []
    for name in sorted(os.listdir(folder)):
        sub = os.path.join(folder, name)
        if not os.path.isdir(sub):
            continue
        if name.lower() == "common":
            dirs.append(sub)
        elif re.fullmatch(r"\d+(\.\d+)*", name):
            versioned.append((vtuple(name), name, sub))
    if os.path.isfile(root_info) and os.path.isdir(os.path.join(folder, "media")):
        dirs.append(folder)
    if versioned:
        b = vtuple(build) if build else (99, 99, 99)
        usable = [v for v in versioned if v[0] <= b] or [min(versioned)]
        dirs.append(max(usable)[2])
    if not dirs:
        dirs.append(folder)
    return dirs


# ---------------------------------------------------------------- census

def media_files(vdir):
    """Every file under vdir/media, as a path relative to media/, forward-slashed."""
    media = os.path.join(vdir, "media")
    if not os.path.isdir(media):
        return []
    out = []
    for base, _dirs, names in os.walk(media):
        rel = os.path.relpath(base, media).replace("\\", "/")
        rel = "" if rel == "." else rel + "/"
        for n in names:
            out.append(rel + n)
    return out


ITEM_RE = re.compile(r"^\s*item\s+([A-Za-z0-9_.\-]+)", re.M)
MODULE_RE = re.compile(r"^\s*module\s+([A-Za-z0-9_.\-]+)", re.M)
OPTION_RE = re.compile(r"^\s*option\s+([A-Za-z0-9_.\-]+)", re.M)


def scan_scripts(vdir):
    """Item ids declared in this mod's script files, as Module.Item."""
    root = os.path.join(vdir, "media", "scripts")
    items = set()
    if not os.path.isdir(root):
        return items
    for base, _d, names in os.walk(root):
        for n in names:
            if not n.lower().endswith(".txt"):
                continue
            try:
                with open(os.path.join(base, n), encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            mods = MODULE_RE.findall(text) or ["Base"]
            module = mods[0]
            for it in ITEM_RE.findall(text):
                items.add("%s.%s" % (module, it))
    return items


def scan_sandbox(vdir):
    """Sandbox option keys this mod declares."""
    path = os.path.join(vdir, "media", "sandbox-options.txt")
    if not os.path.isfile(path):
        return set()
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return set(OPTION_RE.findall(f.read()))
    except OSError:
        return set()


def main():
    workshop, zomboid, declared = load_settings()
    build = game_build(zomboid, declared)
    print("game build : %s" % (build or "unknown - assuming newest folders"))
    print("workshop   : %s" % workshop)

    mods = []           # one record per mod.info folder
    files = defaultdict(list)    # media-relative path -> [mod key]
    items = defaultdict(list)
    options = defaultdict(list)

    for wid, folder in find_mods(workshop, zomboid):
        vdirs = active_dirs(folder, build)
        info = {}
        for d in (vdirs[-1], folder):
            info = read_modinfo(os.path.join(d, "mod.info")) or info
            if info:
                break
        mod_id = info.get("id") or os.path.basename(folder)
        key = "%s/%s" % (wid or "local", mod_id)
        rec = {
            "key": key, "workshopId": wid, "modId": mod_id,
            "name": info.get("name", ""), "folder": folder,
            "activeDirs": [os.path.basename(d) for d in vdirs],
            "fileCount": 0, "luaCount": 0,
        }
        seen = set()
        for d in vdirs:
            for rel in media_files(d):
                if rel in seen:
                    continue
                seen.add(rel)
                files[rel].append(key)
                if rel.startswith("lua/"):
                    rec["luaCount"] += 1
            for it in scan_scripts(d):
                items[it].append(key)
            for op in scan_sandbox(d):
                options[op].append(key)
        rec["fileCount"] = len(seen)
        mods.append(rec)

    def clashes(table):
        out = {}
        for k, owners in table.items():
            uniq = sorted(set(owners))
            if len(uniq) > 1:
                out[k] = uniq
        return dict(sorted(out.items()))

    result = {
        "build": build,
        "modCount": len(mods),
        "fileCount": len(files),
        "mods": sorted(mods, key=lambda m: m["key"]),
        "filePathClashes": clashes(files),
        "itemScriptClashes": clashes(items),
        "sandboxOptionClashes": clashes(options),
    }

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "census.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)

    lines = []
    w = lines.append
    w("PZ MOD CENSUS")
    w("build %s   %d mods   %d distinct media paths" % (build, len(mods), len(files)))
    w("")
    for title, table, note in (
        ("FILE PATHS SHIPPED BY MORE THAN ONE MOD", result["filePathClashes"],
         "the later mod in the load order wins; a lua path here is a silent behaviour override"),
        ("ITEM SCRIPT IDS DECLARED BY MORE THAN ONE MOD", result["itemScriptClashes"],
         "the later declaration replaces the earlier item outright"),
        ("SANDBOX OPTION KEYS DECLARED BY MORE THAN ONE MOD", result["sandboxOptionClashes"],
         "two mods reading one slider"),
    ):
        w("=" * 72)
        w("%s  (%d)" % (title, len(table)))
        w("  %s" % note)
        w("=" * 72)
        for k, owners in table.items():
            w("  %s" % k)
            for o in owners:
                w("      %s" % o)
        w("")
    text = "\n".join(lines)
    with open(os.path.join(OUT, "census.txt"), "w", encoding="utf-8") as f:
        f.write(text)

    print("")
    print("%d mods, %d distinct media paths" % (len(mods), len(files)))
    print("file-path clashes    : %d" % len(result["filePathClashes"]))
    print("item-script clashes  : %d" % len(result["itemScriptClashes"]))
    print("sandbox-key clashes  : %d" % len(result["sandboxOptionClashes"]))
    print("")
    print("written to %s" % OUT)


if __name__ == "__main__":
    sys.exit(main())
