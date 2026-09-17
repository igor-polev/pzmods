#!/usr/bin/env python3
"""
census.py - conflict census for a Project Zomboid mod set.

Answers the two questions descriptions cannot.

STAGE 1 - FILES.     Which installed mods ship the SAME file, item id or sandbox key,
                     and therefore silently overwrite each other at load time.

STAGE 2 - FUNCTIONS. Which mods overwrite the same Lua function at runtime, and
                     whether each one calls the version it replaced.

                     Almost every modern PZ mod monkey-patches rather than shipping
                     copies of vanilla files:

                         local old = ISFoo.bar
                         function ISFoo.bar(a, b)
                             old(a, b)      <- polite: chains
                             ...            <- rude:   does not
                         end

                     Two polite mods coexist. One rude mod silently kills every mod
                     loaded before it, and stage 1 cannot see that at all.

Reads:  settings.json (next to this file) for the workshop and Zomboid paths
        the newest Zomboid\\Logs debug log for the running game build
        the game's own media\\lua, as ground truth for "this is a vanilla function"
Writes: census\\census.json   - full machine-readable result
        census\\census.txt    - the readable summary

Standard library only. Nothing is modified outside the census\\ folder.

    cd C:\\Users\\igor\\Zomboid\\pzmods
    python census.py              full run
    python census.py --no-lua     stage 1 only (seconds instead of ~a minute)
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
    return s


def find_game_dir(settings):
    """
    The game install, for reading vanilla's own media/lua. Explicit `gameDir` in
    settings.json wins; otherwise look beside the workshop folder.
    """
    d = settings.get("gameDir")
    if d and os.path.isdir(os.path.join(d, "media", "lua")):
        return d
    common = os.path.join(os.path.dirname(settings["workshop"]), "common")
    if os.path.isdir(common):
        for nm in sorted(os.listdir(common)):
            cand = os.path.join(common, nm)
            if os.path.isdir(os.path.join(cand, "media", "lua")) and "zomboid" in nm.lower():
                return cand
    return None


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


# =====================================================================
#  LUA STAGE - who overwrites whose functions, and do they chain
# =====================================================================
#
# The file census answers "do two mods ship the same file". Almost every
# modern PZ mod instead monkey-patches at runtime:
#
#     local old = ISFoo.bar
#     function ISFoo.bar(a, b)
#         old(a, b)      <- polite: chains
#         ...            <- rude:   does not
#     end
#
# Two polite mods coexist. One rude mod silently kills every mod loaded
# before it, and nothing in the file census can see that. This stage finds
# it by parsing, not by reading.
#
# Vanilla's own media/lua is scanned first, so "this is a vanilla function"
# is a fact read off disk rather than a guess from a name.

LUA_KEYWORDS = {
    "and", "break", "do", "else", "elseif", "end", "false", "for", "function",
    "goto", "if", "in", "local", "nil", "not", "or", "repeat", "return",
    "then", "true", "until", "while",
}

# Blocks that must be closed by `end`. `for`/`while` are NOT counted: their
# `do` is what opens the block, and `elseif`/`else` continue an open `if`.
BLOCK_OPENERS = {"function", "if", "do"}


def lua_blank(src, keep_strings=False):
    """
    Return src with every comment and string literal replaced by spaces of the
    same length, so offsets still line up but no keyword inside a comment or a
    string can be mistaken for code.

    Handles: -- line comments, --[[ ]] and --[==[ ]==] long comments,
             '...' and "..." with backslash escapes,
             [[ ]] and [==[ ]==] long strings.

    keep_strings=True blanks comments only - used for the keybind scan, where
    the interesting content is inside the string literals.
    """
    out = list(src)
    i, n = 0, len(src)

    def blank(a, b):
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    def long_bracket(pos):
        """If src[pos] opens a long bracket, return (level, body_start)."""
        if pos >= n or src[pos] != "[":
            return None
        j = pos + 1
        eq = 0
        while j < n and src[j] == "=":
            eq += 1
            j += 1
        if j < n and src[j] == "[":
            return eq, j + 1
        return None

    while i < n:
        c = src[i]
        if c == "-" and src.startswith("--", i):
            lb = long_bracket(i + 2)
            if lb:
                level, body = lb
                close = "]" + "=" * level + "]"
                end = src.find(close, body)
                end = n if end < 0 else end + len(close)
                blank(i, end)
                i = end
            else:
                end = src.find("\n", i)
                end = n if end < 0 else end
                blank(i, end)
                i = end
            continue
        if c in "'\"":
            if keep_strings:
                j = i + 1
                while j < n:
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == c or src[j] == "\n":
                        j += 1
                        break
                    j += 1
                i = j
                continue
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == c or src[j] == "\n":
                    j += 1
                    break
                j += 1
            blank(i, j)
            i = j
            continue
        if c == "[":
            lb = long_bracket(i)
            if lb and not keep_strings:
                level, body = lb
                close = "]" + "=" * level + "]"
                end = src.find(close, body)
                end = n if end < 0 else end + len(close)
                blank(i, end)
                i = end
                continue
        i += 1
    return "".join(out)


WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def block_end(clean, start):
    """
    Given an offset at (or just before) a `function` keyword in blanked source,
    return the offset just past its matching `end`, or len(clean) if unbalanced.
    """
    depth = 0
    seen_first = False
    for m in WORD_RE.finditer(clean, start):
        w = m.group(0)
        if w in BLOCK_OPENERS:
            depth += 1
            seen_first = True
        elif w == "repeat":
            depth += 1
            seen_first = True
        elif w == "until":
            depth -= 1
        elif w == "end":
            depth -= 1
        if seen_first and depth <= 0:
            return m.end()
    return len(clean)


QUALIFIED = r"[A-Za-z_][A-Za-z0-9_]*(?:[.:][A-Za-z_][A-Za-z0-9_]*)+"

# function ISFoo.bar(...)   /   function ISFoo:bar(...)
RE_FUNC_QUAL = re.compile(r"\bfunction\s+(" + QUALIFIED + r")\s*\(")
# function bar(...)  - a bare global, only when not preceded by `local`
RE_FUNC_BARE = re.compile(r"(?<!\.)\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
RE_LOCAL_FUNC = re.compile(r"\blocal\s+function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
# ISFoo.bar = function(...)
RE_ASSIGN_FUNC = re.compile(r"(?m)^[ \t]*(" + QUALIFIED + r")\s*=\s*function\b")
# local old = ISFoo.bar        (a reference, not a call - no '(' after)
RE_SAVE_LOCAL = re.compile(
    r"\blocal\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(" + QUALIFIED
    + r"|[A-Za-z_][A-Za-z0-9_]*)\s*(?![\w.(:])")
# ISFoo._oldBar = ISFoo.bar
RE_SAVE_FIELD = re.compile(
    r"(?m)^[ \t]*(" + QUALIFIED + r"|[A-Za-z_][A-Za-z0-9_]*)\s*=\s*("
    + QUALIFIED + r")\s*(?![\w.(:])")
# Foo.saved = Foo.saved or ISFoo.bar   - "capture once" idiom
RE_SAVE_OR = re.compile(
    r"(?m)^[ \t]*(" + QUALIFIED + r"|[A-Za-z_][A-Za-z0-9_]*)\s*=\s*[^\n=]*?\bor\s+("
    + QUALIFIED + r")\s*(?![\w.(:])")
RE_LOCAL_DECL = re.compile(r"\blocal\s+([A-Za-z_][A-Za-z0-9_]*)")
RE_EVENT = re.compile(r"\bEvents\.([A-Za-z_][A-Za-z0-9_]*)\.(Add|Remove)\s*\(")
RE_KEY_MODOPT = re.compile(
    r"addKeyBind\s*\(\s*[\"']([^\"']*)[\"']\s*,\s*[^,]*,\s*(Keyboard\.KEY_[A-Z0-9_]+|\d+)")
RE_KEY_CORE = re.compile(
    r"addKeyBinding\s*\(\s*[\"']([^\"']*)[\"']\s*,\s*(Keyboard\.KEY_[A-Z0-9_]+|\d+)")
RE_KEY_TABLE = re.compile(
    r"value\s*=\s*[\"']([^\"']*)[\"'][^}]{0,200}?key\s*=\s*(Keyboard\.KEY_[A-Z0-9_]+|\d+)")


def lua_files(vdir):
    """Every .lua under vdir/media/lua, as (path-relative-to-lua, full path)."""
    root = os.path.join(vdir, "media", "lua")
    if not os.path.isdir(root):
        return []
    out = []
    for base, _dirs, names in os.walk(root):
        for nm in names:
            if nm.lower().endswith(".lua"):
                full = os.path.join(base, nm)
                rel = os.path.relpath(full, root).replace("\\", "/")
                out.append((rel, full))
    return out


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def scan_lua_source(src):
    """
    Parse one Lua file. Returns a dict:
      declares : {target: [{'kind','chains','saved_as','line'}]}
      events   : [(eventName, 'Add'|'Remove')]
      keys     : [(label, keyConstant)]
    `target` is a qualified global like 'ISInventoryPaneContextMenu.getContainers'
    or a bare global name.
    """
    clean = lua_blank(src)

    # file-local names: a target rooted at one of these is not a global
    locals_ = set(RE_LOCAL_DECL.findall(clean)) | set(RE_LOCAL_FUNC.findall(clean))

    # saved references: var -> qualified name it was captured from
    saves = {}
    for m in RE_SAVE_LOCAL.finditer(clean):
        var, tgt = m.group(1), m.group(2)
        saves.setdefault(tgt.replace(":", "."), []).append(var)
    for m in RE_SAVE_FIELD.finditer(clean):
        lhs, tgt = m.group(1), m.group(2)
        if lhs != tgt:
            saves.setdefault(tgt.replace(":", "."), []).append(lhs)
    for m in RE_SAVE_OR.finditer(clean):
        lhs, tgt = m.group(1), m.group(2)
        if lhs != tgt:
            saves.setdefault(tgt.replace(":", "."), []).append(lhs)

    def line_of(pos):
        return clean.count("\n", 0, pos) + 1

    declares = defaultdict(list)

    def record(target, pos, kind, body_from):
        root = target.split(".")[0].split(":")[0]
        if root in locals_ or root in LUA_KEYWORDS or root == "self":
            return
        norm = target.replace(":", ".")
        end = block_end(clean, body_from)
        body = clean[body_from:end]
        chains = "no"
        saved_as = None
        for var in saves.get(norm, []):
            short = var.split(".")[-1]
            if re.search(r"\b" + re.escape(short) + r"\s*\(", body):
                chains, saved_as = "yes", var
                break
            if re.search(r"\b" + re.escape(short) + r"\b", body):
                chains, saved_as = "referenced", var
        if saved_as is None and saves.get(norm):
            saved_as = saves[norm][0]
        declares[norm].append({
            "kind": kind,
            "saves_original": bool(saves.get(norm)),
            "chains": chains,
            "saved_as": saved_as,
            "line": line_of(pos),
        })

    for m in RE_FUNC_QUAL.finditer(clean):
        record(m.group(1), m.start(), "function", m.start())
    for m in RE_ASSIGN_FUNC.finditer(clean):
        fpos = clean.find("function", m.start())
        record(m.group(1), m.start(), "assign", fpos if fpos >= 0 else m.start())
    for m in RE_FUNC_BARE.finditer(clean):
        pre = clean[max(0, m.start() - 12):m.start()]
        if re.search(r"\blocal\s*$", pre):
            continue
        record(m.group(1), m.start(), "function", m.start())

    events = [(m.group(1), m.group(2)) for m in RE_EVENT.finditer(clean)]
    with_strings = lua_blank(src, keep_strings=True)
    keys = []
    for rx in (RE_KEY_MODOPT, RE_KEY_CORE, RE_KEY_TABLE):
        for m in rx.finditer(with_strings):
            keys.append((m.group(1).strip(), m.group(2)))
    return {"declares": dict(declares), "events": events, "keys": keys}


def scan_vanilla_lua(game_dir):
    """Every global function the game itself declares - the ground truth."""
    root = os.path.join(game_dir, "media", "lua")
    known = set()
    if not os.path.isdir(root):
        return known, 0
    count = 0
    for base, _d, names in os.walk(root):
        for nm in names:
            if not nm.lower().endswith(".lua"):
                continue
            count += 1
            clean = lua_blank(read_text(os.path.join(base, nm)))
            for m in RE_FUNC_QUAL.finditer(clean):
                nm = m.group(1).replace(":", ".")
                if not nm.startswith("self."):
                    known.add(nm)
            for m in RE_ASSIGN_FUNC.finditer(clean):
                nm = m.group(1).replace(":", ".")
                if not nm.startswith("self."):
                    known.add(nm)
            for m in RE_FUNC_BARE.finditer(clean):
                pre = clean[max(0, m.start() - 12):m.start()]
                if not re.search(r"\blocal\s*$", pre):
                    known.add(m.group(1))
    return known, count


def rank(d):
    """Prefer the record that tells us most: a chaining patch beats a bare redefine."""
    return ({"yes": 3, "referenced": 2, "no": 1}[d["chains"]], 1 if d["saves_original"] else 0)


def main():
    settings = load_settings()
    workshop, zomboid = settings["workshop"], settings["zomboid"]
    build = game_build(zomboid, settings.get("gameVersion", "auto"))
    scan_lua = "--no-lua" not in sys.argv
    game = find_game_dir(settings) if scan_lua else None

    print("game build : %s" % (build or "unknown - assuming newest folders"))
    print("workshop   : %s" % workshop)
    if not scan_lua:
        print("game dir   : (skipped, --no-lua)")
    elif game:
        print("game dir   : %s" % game)
    else:
        print("game dir   : NOT FOUND - set \"gameDir\" in settings.json.")
        print("             Without it, vanilla functions cannot be told from mod-owned")
        print("             ones, so sections D and E will be empty and everything lands in F.")

    # ---- stage 2 groundwork: what does vanilla itself declare ----
    vanilla = set()
    vfiles = 0
    if scan_lua and game:
        print("scanning vanilla lua ...", end=" ", flush=True)
        vanilla, vfiles = scan_vanilla_lua(game)
        print("%d globals in %d files" % (len(vanilla), vfiles))

    mods = []                     # one record per mod.info folder
    files = defaultdict(list)     # media-relative path -> [mod key]
    items = defaultdict(list)
    options = defaultdict(list)
    lua_decl = defaultdict(dict)  # target -> {mod key: decl record}
    events = defaultdict(lambda: defaultdict(int))   # event -> mod -> count
    keybinds = defaultdict(list)  # key constant -> [(mod, label)]
    lua_files_seen = 0

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
            "globals": 0, "vanillaPatches": 0, "unchained": 0,
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

            if not scan_lua:
                continue
            for rel, full in lua_files(d):
                lua_files_seen += 1
                res = scan_lua_source(read_text(full))
                for target, decls in res["declares"].items():
                    for dd in decls:
                        prev = lua_decl[target].get(key)
                        # keep the most informative record per (target, mod)
                        if prev and rank(prev) >= rank(dd):
                            continue
                        lua_decl[target][key] = dict(dd, file=rel)
                        rec["globals"] += 0 if prev else 1
                for ev, how in res["events"]:
                    if how == "Add":
                        events[ev][key] += 1
                for label, kc in res["keys"]:
                    keybinds[kc].append((key, label))

        rec["fileCount"] = len(seen)
        mods.append(rec)

    # per-mod unchained count, now that every target is known
    bykey = {m["key"]: m for m in mods}
    for target, owners in lua_decl.items():
        if target not in vanilla:
            continue
        for k, dd in owners.items():
            if k not in bykey:
                continue
            bykey[k]["vanillaPatches"] += 1
            if dd["chains"] == "no":
                bykey[k]["unchained"] += 1

    def clashes(table):
        out = {}
        for k, owners in table.items():
            uniq = sorted(set(owners))
            if len(uniq) > 1:
                out[k] = uniq
        return dict(sorted(out.items()))

    # ---- stage 2 group-bys ----
    contested = {}          # vanilla function, 2+ mods
    vanilla_clobber = {}    # vanilla function, 1 mod, no chain
    third_party = {}        # non-vanilla global, 2+ mods
    for target, owners in sorted(lua_decl.items()):
        is_vanilla = target in vanilla
        if len(owners) > 1:
            (contested if is_vanilla else third_party)[target] = owners
        elif is_vanilla:
            only = next(iter(owners.values()))
            if only["chains"] == "no":
                vanilla_clobber[target] = owners

    key_clashes = {k: v for k, v in sorted(keybinds.items())
                   if len({m for m, _ in v}) > 1}
    hot_events = {e: dict(sorted(ms.items())) for e, ms in sorted(events.items())
                  if len(ms) > 1}

    result = {
        "build": build,
        "modCount": len(mods),
        "fileCount": len(files),
        "luaFileCount": lua_files_seen,
        "vanillaGlobalCount": len(vanilla),
        "vanillaLuaFiles": vfiles,
        "mods": sorted(mods, key=lambda m: m["key"]),
        "filePathClashes": clashes(files),
        "itemScriptClashes": clashes(items),
        "sandboxOptionClashes": clashes(options),
        "contestedVanillaFunctions": contested,
        "vanillaFunctionsClobbered": vanilla_clobber,
        "contestedModFunctions": third_party,
        "keyBindClashes": key_clashes,
        "eventHandlers": hot_events,
    }

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "census.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)

    # ---------------------------------------------------------- report
    lines = []
    w = lines.append
    w("PZ MOD CENSUS")
    w("build %s   %d mods   %d distinct media paths" % (build, len(mods), len(files)))
    if scan_lua:
        w("lua: %d mod files parsed, %d vanilla globals from %d game files"
          % (lua_files_seen, len(vanilla), vfiles))
    w("")

    def section(title, note, body):
        w("=" * 78)
        w(title)
        w("  " + note)
        w("=" * 78)
        body()
        w("")

    def simple(table):
        def go():
            for k, owners in table.items():
                w("  %s" % k)
                for o in owners:
                    w("      %s" % o)
        return go

    section("A. FILE PATHS SHIPPED BY MORE THAN ONE MOD  (%d)"
            % len(result["filePathClashes"]),
            "the later mod in the load order wins outright",
            simple(result["filePathClashes"]))
    section("B. ITEM SCRIPT IDS DECLARED BY MORE THAN ONE MOD  (%d)"
            % len(result["itemScriptClashes"]),
            "the later declaration replaces the earlier item",
            simple(result["itemScriptClashes"]))
    section("C. SANDBOX OPTION KEYS DECLARED BY MORE THAN ONE MOD  (%d)"
            % len(result["sandboxOptionClashes"]),
            "two mods reading one slider",
            simple(result["sandboxOptionClashes"]))

    if not scan_lua:
        text = "\n".join(lines)
        with open(os.path.join(OUT, "census.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        print("\nstage 1 only. written to %s" % OUT)
        return

    def owners_block(owners):
        for k in sorted(owners):
            dd = owners[k]
            flag = {"yes": "chains",
                    "referenced": "chains?",
                    "no": "DOES NOT CHAIN"}[dd["chains"]]
            saved = "" if dd["saves_original"] else "   (no original saved)"
            w("      %-44s %-15s%s" % (k, flag, saved))
            w("          %s:%d  %s" % (dd["file"], dd["line"], dd["kind"]))

    def contested_body():
        risky = [t for t, o in contested.items()
                 if any(d["chains"] == "no" for d in o.values())]
        w("  %d of these have at least one mod that does not chain - listed first."
          % len(risky))
        w("")
        for t in risky + [t for t in contested if t not in risky]:
            w("  %s%s" % (t, "        <<< at least one mod does not chain" if t in risky else ""))
            owners_block(contested[t])
            w("")

    section("D. VANILLA FUNCTIONS REPLACED BY TWO OR MORE MODS  (%d)" % len(contested),
            "the headline: only one survives, and a mod that does not chain erases the others"
            if vanilla else
            "EMPTY because the game folder was not found - see the note at the top of the run",
            contested_body)

    def clobber_body():
        for t, o in vanilla_clobber.items():
            w("  %s" % t)
            owners_block(o)
    section("E. VANILLA FUNCTIONS REPLACED WITHOUT CHAINING, BY ONE MOD  (%d)"
            % len(vanilla_clobber),
            "no conflict today, but any future mod touching these is erased by this one",
            clobber_body)

    def third_body():
        for t, o in third_party.items():
            w("  %s" % t)
            owners_block(o)
    section("F. NON-VANILLA GLOBALS DECLARED BY TWO OR MORE MODS  (%d)" % len(third_party),
            "usually an addon extending its base mod - check the ones that are not",
            third_body)

    def key_body():
        for kc, lst in key_clashes.items():
            w("  %s" % kc)
            for m, label in sorted(lst):
                w("      %-42s %s" % (m, label))
    section("G. KEYBINDS REGISTERED ON THE SAME DEFAULT KEY  (%d)" % len(key_clashes),
            "both fire; rebind one",
            key_body)

    def event_body():
        w("  %-34s %5s  mods" % ("event", "total"))
        for ev, ms in sorted(hot_events.items(),
                             key=lambda kv: -sum(kv[1].values())):
            tot = sum(ms.values())
            if ev in ("OnTick", "OnPlayerUpdate", "OnRenderTick", "OnFETick"):
                w("  %-34s %5d  <<< per-frame" % (ev, tot))
            else:
                w("  %-34s %5d" % (ev, tot))
            for m, c in sorted(ms.items(), key=lambda kv: -kv[1]):
                w("        %-44s %d" % (m, c))
    section("H. EVENT HANDLERS BY EVENT  (%d events with 2+ mods)" % len(hot_events),
            "per-frame events are a performance map: every handler runs every frame",
            event_body)

    top = sorted((m for m in mods if m["unchained"]),
                 key=lambda m: -m["unchained"])[:25]
    def rude_body():
        w("  %-46s %9s %9s" % ("mod", "vanilla", "no chain"))
        for m in top:
            w("  %-46s %9d %9d" % (m["key"], m["vanillaPatches"], m["unchained"]))
    section("I. MODS THAT REPLACE VANILLA FUNCTIONS WITHOUT CHAINING  (top %d)" % len(top),
            "the mods most likely to erase another mod's work",
            rude_body)

    text = "\n".join(lines)
    with open(os.path.join(OUT, "census.txt"), "w", encoding="utf-8") as f:
        f.write(text)

    print("")
    print("%d mods, %d media paths, %d lua files" % (len(mods), len(files), lua_files_seen))
    print("file-path clashes            : %d" % len(result["filePathClashes"]))
    print("item-script clashes          : %d" % len(result["itemScriptClashes"]))
    print("sandbox-key clashes          : %d" % len(result["sandboxOptionClashes"]))
    print("contested vanilla functions  : %d" % len(contested))
    print("  of those, someone won't chain: %d"
          % len([t for t, o in contested.items()
                 if any(d["chains"] == "no" for d in o.values())]))
    print("vanilla clobbered by one mod : %d" % len(vanilla_clobber))
    print("contested mod-owned globals  : %d" % len(third_party))
    print("keybind clashes              : %d" % len(key_clashes))
    print("")
    print("written to %s" % OUT)


if __name__ == "__main__":
    sys.exit(main())
