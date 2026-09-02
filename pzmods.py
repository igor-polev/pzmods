#!/usr/bin/env python3
"""pzmods - local mod collection manager for Project Zomboid.

One command, no dependencies:

    python pzmods.py

Five sources of truth, read together by one Update pass:

    local   the workshop content folder      ...\\steamapps\\workshop\\content\\108600
    local   your own mods folder             ...\\Zomboid\\mods
    local   the mod list config              ...\\Zomboid\\Lua\\pz_modlist_settings.cfg
    online  the public Workshop API          titles, descriptions, tags, comments
    online  your subscription list           the only source that needs you signed in

Everything else in this program is a view over that one snapshot.
"""

import hashlib
import http.server
import json
import os
import re
import shutil
import socketserver
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
APPID = "108600"

# --------------------------------------------------------------------------
# settings
# --------------------------------------------------------------------------

DEFAULTS = {
    "workshop": r"C:\Program Files (x86)\Steam\steamapps\workshop",
    "zomboid": str(Path.home() / "Zomboid"),
    "port": 8765,
    "modImageSize": 40,
    "fetchCommentsOnUpdate": False,
    "updateOnStartup": True,
    "gameVersion": "auto",
}


def load_settings():
    f = HERE / "settings.json"
    s = dict(DEFAULTS)
    if f.exists():
        try:
            s.update(json.loads(f.read_text(encoding="utf-8")))
        except Exception as e:
            print("  settings.json unreadable (%s), using defaults" % e)
    s["workshop"] = os.environ.get("PZMODS_WORKSHOP", s["workshop"])
    s["zomboid"] = os.environ.get("PZMODS_ZOMBOID", s["zomboid"])
    s["port"] = int(os.environ.get("PZMODS_PORT", s["port"]))
    try:
        s["modImageSize"] = max(16, min(96, int(s.get("modImageSize", 40))))
    except Exception:
        s["modImageSize"] = 40
    return s


def save_settings(s):
    (HERE / "settings.json").write_text(
        json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


SET = load_settings()
PORT = int(SET["port"])
WORKSHOP = Path(SET["workshop"])
CONTENT = WORKSHOP / "content" / APPID
ACF = WORKSHOP / ("appworkshop_%s.acf" % APPID)
ZOMBOID = Path(SET["zomboid"])
CFG = ZOMBOID / "Lua" / "pz_modlist_settings.cfg"
LOCAL_MODS = ZOMBOID / "mods"

DATA = HERE / "data"
BACKUPS = HERE / "backups"
SAND_BACKUPS = BACKUPS / "sandbox"
for d in (DATA, BACKUPS, SAND_BACKUPS, DATA / "comments"):
    d.mkdir(parents=True, exist_ok=True)

TAGS_FILE = DATA / "tags.json"
SNAP_FILE = DATA / "snapshot.json"
# written by the workshop-discovery skill, not by pzmods. The one file in there
# pzmods owns is verdicts.json, which the skill never writes.
DISCOVERY = HERE / "discovery"


def jread(path, default):
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def jwrite(path, obj):
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def read_subs():
    """The synced list is a snapshot, not a standing fact, so it is stored with the
    moment it was taken. Older files were a bare list; treat those as undated."""
    raw = jread(DATA / "subs.json", [])
    if isinstance(raw, dict):
        return raw.get("items") or [], int(raw.get("fetched") or 0)
    return raw or [], 0


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------
# which build of the game are you actually running?
# --------------------------------------------------------------------------
#
# This number decides which version folder a mod's mod.info is read from, and
# whether versionMin / versionMax put a mod out of range. Getting it from a
# setting means it is right on the day it is typed and wrong after the next patch,
# and wrong quietly: 42.20 against 42.20.4 makes three up-to-date mods look like
# they need a newer game. The game itself knows, and says so in its own log every
# time it starts:
#
#     LOG  : General      f:0> version=42.20.4 b0bbce05d5 demo=false.
#
# so that is the witness, the same way every other fact here comes from a file
# rather than from something remembered.

VERSION_RE = re.compile(rb"version=(\d+\.\d+(?:\.\d+)?)\s+\S+\s+demo=")
GAME = {"version": "42.20", "source": "the built-in default"}


def detect_game_version():
    """The newest debug log that names a version wins. Only the newest few are
    read: a B41-era log names no version in this format, and one that is years old
    is not evidence about the build installed now."""
    logs = ZOMBOID / "Logs"
    if not logs.is_dir():
        return None, None
    files = sorted(list(logs.glob("*DebugLog*.txt")) + list(logs.glob("logs_*/*DebugLog*.txt")),
                   key=lambda p: p.stat().st_mtime, reverse=True)[:6]
    for p in files:
        try:
            with p.open("rb") as f:
                m = VERSION_RE.search(f.read(1 << 20))     # the line is written at startup
        except OSError:
            continue
        if m:
            return m.group(1).decode(), p.name
    return None, None


def resolve_game_version():
    """settings.json wins when it names a version outright; "auto" or nothing means
    ask the log, and the old default falls back to it too."""
    want = str(SET.get("gameVersion") or "").strip()
    if want and want.lower() != "auto":
        GAME.update(version=want, source="gameVersion in settings.json")
        return GAME
    found, where = detect_game_version()
    if found:
        GAME.update(version=found, source=where)
    else:
        GAME.update(version="42.20", source="no debug log named one - using the default")
    return GAME


resolve_game_version()


# --------------------------------------------------------------------------
# source 1 and 2: the two local mod folders
# --------------------------------------------------------------------------

INFO_KEYS = ("id", "name", "description", "require", "versionMin", "versionMax",
             "pzversion", "modversion", "author", "url", "loadModAfter", "loadModBefore",
             "incompatible", "icon", "poster")

# The fallback, for a mod that declares no usable picture. Tried at the mod root
# first and then in each version folder; exact names win over patterns, so a mod
# carrying both poster.png and a pile of icon_something.png files still shows its
# poster.
IMAGE_NAMES = ("poster.png", "icon.png", "thumbnail.png", "preview.png",
               "poster.jpg", "icon.jpg")
IMAGE_GLOBS = ("icon_*.png", "poster_*.png", "icon_*.jpg")

# A map ships one of these per 300x300 world cell it covers, and x and y are
# positions in the vanilla map's own grid - which is the whole reason two mods can
# be compared at all.
LOTPACK_RE = re.compile(r"^world_(\d+)_(\d+)\.lotpack$", re.I)


def parse_mod_info(path):
    out = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if k in INFO_KEYS:
            out.setdefault(k, v.strip())
    return out


def image_in(d):
    """First matching picture in one directory, exact names before patterns."""
    for n in IMAGE_NAMES:
        p = d / n
        if p.is_file():
            return p
    for g in IMAGE_GLOBS:
        # a pattern can match several files, so sort for a stable pick
        hits = sorted((p for p in d.glob(g) if p.is_file()), key=lambda p: p.name)
        if hits:
            return hits[0]
    return None


def find_image(mod_root):
    p = image_in(mod_root)
    if p:
        return p
    if mod_root.is_dir():
        for child in sorted(mod_root.iterdir()):
            if child.is_dir():
                p = image_in(child)
                if p:
                    return p
    return None


def find_mod_infos(mod_root):
    """mod.info sits at the mod root or inside a version folder (42, 42.20, common)."""
    found = []
    direct = mod_root / "mod.info"
    if direct.exists():
        found.append(direct)
    for child in sorted(mod_root.iterdir()) if mod_root.is_dir() else []:
        if child.is_dir():
            f = child / "mod.info"
            if f.exists():
                found.append(f)
    return found


def dep_list(value):
    """Split a require= / loadModAfter= value into clean mod ids.

    Most Build 42 mod.info files write dependencies with a leading backslash -
    require=\\damnlib - and often a trailing comma. In this collection 241 of 323
    dependency tokens are written that way, no token ever contains an interior
    separator, and no mod ever mixes the two styles, so the backslash is a house
    style the game ignores, not a path. Strip it, or every one of those mods looks
    like it is missing a dependency it plainly has.
    """
    out = []
    for tok in re.split(r"[;,]", value or ""):
        tok = tok.strip().strip("\\/").strip()
        if tok:
            out.append(tok)
    return out


def vkey(name):
    """Sort key for a mod's version folder. Numeric folders rank by version;
    'common' and the mod root rank below every numeric one."""
    m = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?$", name or "")
    if not m:
        return (0, 0, 0, 0)
    return (1,) + tuple(int(x or 0) for x in m.groups())


def vbound(value, build):
    """A versionMin/versionMax from mod.info, as a key, together with the build cut
    to the same precision. (None, None) when the value is not a version at all -
    one mod writes versionMin=42.16.+, and a bound nobody can read is not a bound.

    A bound is only as precise as it is written: versionMax=42.20 names the whole
    42.20 family, not 42.20.0, so the build must be compared at the bound's own
    depth. Comparing the full keys reads 42.20.4 as newer than 42.20 and flags
    every such mod as out of range."""
    txt = (value or "").strip()
    k = vkey(txt)
    if not k[0]:
        return None, None
    depth = len(txt.split("."))
    return k, build[:1 + depth] + (0,) * (3 - depth)


def read_mod_dir(mdir, rel_to=None, build=None):
    """One folder under <workshop item>/mods/ or Zomboid/mods/ -> one mod record.

    A Build 42 mod keeps a mod.info per version folder, and the game reads the
    newest one that is not above the build it is running. Those files do not have
    to agree: TwisTonFire - Exercises declares id=TwisTonFireExercises in 42.20 and
    id=twistexercises in common. Picking the wrong folder means reporting an id the
    game never uses, and then reporting the id it does use as 'not installed'.
    """
    build = vkey(build or GAME["version"])
    cands = []
    for info in find_mod_infos(mdir):
        d = parse_mod_info(info)
        if d.get("id"):
            fname = info.parent.name if info.parent != mdir else ""
            cands.append((vkey(fname), fname or "(root)", d))
    if not cands:
        return None
    usable = [c for c in cands if c[0] <= build] or cands
    usable.sort(key=lambda c: c[0])
    best = usable[-1][2]
    active_folder = usable[-1][1]
    ids = []
    for _, fname, d in cands:
        if d["id"] not in ids:
            ids.append(d["id"])

    # A declared picture beats a guessed one. icon= and poster= name a file relative
    # to the folder their own mod.info sits in, and some point outside it
    # (../common/poster.png). Neither field is mandatory and 55 of the posters in
    # this collection name a file that was never shipped, so a value is only worth
    # taking when it resolves to a real file inside the mod - hence the scan below.
    order = [usable[-1]] + sorted((c for c in cands if c is not usable[-1]),
                                  key=lambda c: c[0], reverse=True)

    def declared(field):
        # normpath, not resolve: it collapses the ../ textually, so the answer keeps
        # the same prefix the scan uses and stays comparable to it
        for _, fname, d in order:
            v = (d.get(field) or "").strip()
            if not v:
                continue
            base = mdir if fname == "(root)" else mdir / fname
            for cand in (base / v, mdir / v):
                p = Path(os.path.normpath(str(cand)))
                if p.is_file() and str(p).startswith(str(mdir) + os.sep):
                    return p
        return None

    # poster= first, and the same picture everywhere - the row and the mod's own
    # page. It is what the author made to be recognised by, and it is declared far
    # more often than icon=; icon= only stands in when there is no usable poster.
    img = declared("poster") or declared("icon") or find_image(mdir)

    # The ground the mod's maps occupy, read from the cell files themselves rather
    # than from anything declared. Only the folders Build 42 loads are looked at -
    # common/ plus the one version folder chosen above - so a Build 41 map still
    # sitting in the mod root is not counted: the game never reads it. Petroville
    # ships exactly that, an old Petroville/ next to the real Petroville42/.
    cells = {}
    for base in (mdir / "common", mdir if active_folder == "(root)" else mdir / active_folder):
        mroot = base / "media" / "maps"
        for d in sorted(mroot.iterdir()) if mroot.is_dir() else []:
            for p in d.iterdir() if d.is_dir() else []:
                m = LOTPACK_RE.match(p.name)
                if m:
                    cells.setdefault(d.name, set()).add((int(m.group(1)), int(m.group(2))))

    lo, blo = vbound(best.get("versionMin", ""), build)
    hi, bhi = vbound(best.get("versionMax", ""), build)
    rec = {
        "modId": best["id"],
        "modIds": ids,                    # every id this folder declares anywhere
        "name": best.get("name", best["id"]),
        "folder": mdir.name,
        "versionFolders": [c[1] for c in cands],
        "activeFolder": active_folder,
        "require": dep_list(best.get("require", "")),
        "loadAfter": dep_list(best.get("loadModAfter", "")),
        "loadBefore": dep_list(best.get("loadModBefore", "")),
        "incompatible": dep_list(best.get("incompatible", "")),
        "maps": [{"name": n, "cells": sorted(cells[n])} for n in sorted(cells)],
        "requireRaw": (best.get("require", "") or "").strip(),
        "versionMin": best.get("versionMin", ""),
        "versionMax": best.get("versionMax", ""),
        # settled here, against the same build that chose the folder above, so the
        # drawer and the Issues tab cannot end up disagreeing about the same mod
        "versionFit": ("too new" if lo and build[0] and lo > blo else
                       "too old" if hi and build[0] and hi < bhi else ""),
        "pzversion": best.get("pzversion", ""),
        "modversion": best.get("modversion", ""),
        "author": best.get("author", ""),
        "path": str(mdir),
    }
    if img:
        if rel_to:
            rec["image"] = str(img.relative_to(rel_to)).replace("\\", "/")
        else:
            rec["localImage"] = str(img)
    return rec


def scan_workshop():
    """workshop id -> the mods it contains. One item routinely carries several."""
    result = {}
    if not CONTENT.is_dir():
        return result, "workshop content folder not found: %s" % CONTENT
    for folder in sorted(CONTENT.iterdir()):
        if not folder.is_dir() or not folder.name.isdigit():
            continue
        mods = []
        mroot = folder / "mods"
        if mroot.is_dir():
            for mdir in sorted(mroot.iterdir()):
                if mdir.is_dir():
                    rec = read_mod_dir(mdir, rel_to=CONTENT)
                    if rec:
                        mods.append(rec)
        result[folder.name] = {"mods": mods}
    return result, None


def scan_local_mods():
    out = []
    if not LOCAL_MODS.is_dir():
        return out
    for mdir in sorted(LOCAL_MODS.iterdir()):
        if mdir.is_dir():
            rec = read_mod_dir(mdir)
            if rec:
                out.append(rec)
    return out


def parse_acf():
    """Steam's own record: what is installed, and what this account subscribed to."""
    if not ACF.exists():
        return {}
    text = ACF.read_text(encoding="utf-8", errors="replace")

    def section(name):
        i = text.find('"%s"' % name)
        if i < 0:
            return ""
        j = text.find("{", i)
        depth = 0
        for k in range(j, len(text)):
            if text[k] == "{":
                depth += 1
            elif text[k] == "}":
                depth -= 1
                if depth == 0:
                    return text[j:k + 1]
        return ""

    out = {}
    for m in re.finditer(r'"(\d{6,})"\s*\{(.*?)\}', section("WorkshopItemsInstalled"), re.S):
        body = m.group(2)
        g = lambda k: (re.search(r'"%s"\s+"([^"]*)"' % k, body) or [None, None])[1]
        out[m.group(1)] = {"size": int(g("size") or 0), "timeupdated": int(g("timeupdated") or 0)}
    for m in re.finditer(r'"(\d{6,})"\s*\{(.*?)\}', section("WorkshopItemDetails"), re.S):
        body = m.group(2)
        g = lambda k: (re.search(r'"%s"\s+"([^"]*)"' % k, body) or [None, None])[1]
        sb = g("subscribedby")
        d = out.setdefault(m.group(1), {})
        d["subscribedBy"] = sb or ""
        d["subscribed"] = bool(sb and sb != "0")
        if not d.get("timeupdated"):
            d["timeupdated"] = int(g("timeupdated") or 0)
    return out


# --------------------------------------------------------------------------
# source 3: the config file
# --------------------------------------------------------------------------

CONFIG_LINE_RE = re.compile(r"^-\d+-\s")
MARKER_RE = re.compile(r"^\s*[!@#$*]")     # !fav! and friends: Mod Manager's own

DISABLED = "-- Disabled"


def line_kind(name, kinds=None):
    """What sort of line is this?

    The config file has no type marker, so the shape of the name is all there is.
    A leading -N- is a config; a name starting with punctuation like !fav! is a
    marker Mod Manager keeps for itself; anything else is one of your tags. Tag
    names used to have to start with two digits - that was only ever cosmetic, and
    the rule is gone. Whatever pzmods has already classified wins over the shape,
    so a tag called "Sound" keeps being a tag."""
    if kinds and name in kinds:
        return kinds[name]
    if CONFIG_LINE_RE.match(name):
        return "config"
    if MARKER_RE.match(name):
        return "passthrough"
    return "tag"


def valid_tag_name(name):
    name = (name or "").strip()
    if not name:
        return "a tag needs a name"
    if ":" in name or ";" in name:
        return "a tag name cannot contain : or ; - the config file uses them as separators"
    if CONFIG_LINE_RE.match(name):
        return "that looks like a config name (-N- Something), not a tag"
    if MARKER_RE.match(name):
        return "a name starting with punctuation is reserved for Mod Manager's markers"
    return None


def read_cfg():
    if not CFG.exists():
        return []
    out = []
    for line in CFG.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        name, _, rest = line.partition(":")
        out.append({"name": name, "mods": [m.strip() for m in rest.split(";") if m.strip()]})
    return out


def cfg_fingerprint():
    if not CFG.exists():
        return ""
    return hashlib.sha1(CFG.read_bytes()).hexdigest()


def backup_cfg():
    if not CFG.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUPS / ("pz_modlist_settings.%s.cfg" % stamp)
    shutil.copy2(CFG, dest)
    for old in sorted(BACKUPS.glob("pz_modlist_settings.*.cfg"))[:-40]:
        try:
            old.unlink()
        except Exception:
            pass
    return dest.name


def render_cfg(lines, sep=";"):
    """ModManager ends every non-empty line with a trailing separator. Match whatever
    the file already does, so a Save is not a gratuitous whole-file change."""
    out = []
    for l in lines:
        mods = ";".join(l["mods"])
        out.append("%s:%s%s" % (l["name"], mods, sep if mods else ""))
    return "\n".join(out) + "\n"


def write_cfg(lines, sep=";"):
    made = backup_cfg()
    body = render_cfg(lines, sep).rstrip("\n")
    CFG.parent.mkdir(parents=True, exist_ok=True)
    tmp = CFG.with_suffix(".cfg.tmp")
    tmp.write_text(body + "\n", encoding="utf-8")
    tmp.replace(CFG)
    return made


# --------------------------------------------------------------------------
# tags: the grouping model
# --------------------------------------------------------------------------
#
# A tag is a named, ordered list of mods. A mod may carry any number of tags.
# A config is not something the user fills in by hand; it is a synthetic tag -
# the user names an ordered list of tags and pzmods unions them in that order.

SCHEMA = 3


def empty_store():
    return {"schema": SCHEMA, "tagMods": {}, "tagOrder": [], "configs": {},
            "lineOrder": [], "passthrough": {}, "kinds": {}, "cfgFingerprint": "",
            "dirty": False, "conflict": None, "lastSeed": "", "trailingSep": ";"}


def seed_from_cfg(raw, kinds=None):
    """Read the whole grouping model out of the config file."""
    st = empty_store()
    kind = {l["name"]: line_kind(l["name"], kinds) for l in raw}
    st["kinds"] = kind
    st["tagMods"] = {l["name"]: l["mods"] for l in raw if kind[l["name"]] == "tag"}
    st["tagOrder"] = [l["name"] for l in raw if kind[l["name"]] == "tag"]
    st["passthrough"] = {l["name"]: l["mods"] for l in raw if kind[l["name"]] == "passthrough"}
    st["lineOrder"] = [l["name"] for l in raw]
    for c in [l for l in raw if kind[l["name"]] == "config"]:
        cs = set(c["mods"])
        # Which tags is this config made of? A tag counts if the config contains all
        # of it, and also if it contains nearly all of it - somebody adding one mod
        # to a tag by hand must not make the whole tag stop belonging to the config.
        picked, adds = [], {}
        for t, mods in st["tagMods"].items():
            if not mods:
                continue
            here = [m for m in mods if m in cs]
            if len(here) == len(mods):
                picked.append(t)
            elif len(mods) >= 3 and len(here) / len(mods) >= 0.75:
                picked.append(t)
                adds[t] = [m for m in mods if m not in cs]
        # load order matters, so order the tags by where their mods first appear
        pos = {m: i for i, m in enumerate(c["mods"])}
        picked.sort(key=lambda t: min((pos.get(m, 1 << 30) for m in st["tagMods"][t]),
                                      default=1 << 30))
        covered = set()
        for t in picked:
            covered |= set(st["tagMods"][t])
        st["configs"][c["name"]] = {
            "tags": picked,
            "extras": [m for m in c["mods"] if m not in covered],
            "adds": adds,
        }
    # remember the file's own punctuation
    body = [l.rstrip("\r\n") for l in
            (CFG.read_text(encoding="utf-8", errors="replace").splitlines() if CFG.exists() else [])
            if l.strip()]
    withmods = [l for l in body if l.partition(":")[2].strip()]
    st["trailingSep"] = ";" if withmods and sum(
        1 for l in withmods if l.rstrip().endswith(";")) * 2 > len(withmods) else ""
    st["cfgFingerprint"] = cfg_fingerprint()
    st["lastSeed"] = now()
    return st


def ensure_disabled(st):
    """The Disabled tag always exists, is never renamed and is never deleted.
    It is what makes "installed but deliberately switched off" a state pzmods can
    tell apart from "forgot to file it"."""
    if DISABLED not in st["tagMods"]:
        st["tagMods"][DISABLED] = []
    if DISABLED not in st["tagOrder"]:
        st["tagOrder"].append(DISABLED)
    st["kinds"][DISABLED] = "tag"
    for c in st["configs"].values():
        c["tags"] = [t for t in c.get("tags", []) if t != DISABLED]
    return st


def sanitize(st):
    """A passthrough marker must never be treated as a tag or a config."""
    for name in list(st["tagMods"]):
        if line_kind(name) != "tag":
            st["passthrough"].setdefault(name, st["tagMods"].pop(name))
    for name in list(st["configs"]):
        if line_kind(name) != "config":
            st["passthrough"].setdefault(name, [])
            st["configs"].pop(name)
    for c in st["configs"].values():
        # an older pzmods remembered each config's own mod order; the order is now a
        # function of the tags alone, so drop the leftover rather than carry it
        c.pop("orderHint", None)
    st["tagOrder"] = ([t for t in st["tagOrder"] if t in st["tagMods"]] +
                      [t for t in st["tagMods"] if t not in st["tagOrder"]])
    return ensure_disabled(st)


def load_tags():
    """The config file is the source of truth. Nothing else is ever trusted for
    what the tags contain - an older pzmods kept its own cache of the grouping, and
    a cache that drifts from the file invents mods that are not there and loses ones
    that are. On a schema change the cache is set aside and everything is re-read."""
    st = jread(TAGS_FILE, None)
    if st is not None and st.get("schema") != SCHEMA:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(TAGS_FILE, DATA / ("tags.%s.json" % stamp))
        print("  tags.json is from an older pzmods; kept a copy as tags.%s.json "
              "and re-reading everything from %s" % (stamp, CFG.name))
        st = None
    if st is None:
        st = seed_from_cfg(read_cfg(), (jread(TAGS_FILE, {}) or {}).get("kinds"))
        print("  read the tag model from %s" % CFG.name)
    for k, v in empty_store().items():
        st.setdefault(k, v)
    return sanitize(st)


def save_tags(st):
    jwrite(TAGS_FILE, st)


def reconcile_cfg(st, log):
    """The config file is editable by hand and by ModManager. Notice, and react."""
    fp = cfg_fingerprint()
    if fp == st.get("cfgFingerprint"):
        return st
    if not CFG.exists():
        log("the config file is gone from disk; keeping the model in memory")
        return st
    if st.get("dirty"):
        st["conflict"] = {"when": now(), "fingerprint": fp}
        log("the config file changed on disk AND you have unsaved tag edits - "
            "asking you which one wins")
        return st
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(TAGS_FILE, DATA / ("tags.%s.json" % stamp)) if TAGS_FILE.exists() else None
    new = seed_from_cfg(read_cfg(), st.get("kinds"))
    new["reloadedAt"] = now()
    log("the config file changed on disk - reloaded tags and configs from it")
    return new


def build_configs(st):
    """A config line is the ordered union of its tags, in the order the tags are
    listed - minus anything wearing the Disabled tag, which is the whole point of
    that tag: switched off everywhere at once, without losing how it was filed.

    A mod enters at the first tag of this config that holds it, at the position it
    holds inside that tag. The other tags it also wears change nothing: they reach
    it when it is already there. So the whole load order of a config is a function
    of two things you can see and edit - the order of its tags, and the order of
    the mods inside each tag - and of nothing else. Switching a mod off and on
    again cannot move it, because there is no remembered position to lose.
    """
    off = set(st["tagMods"].get(DISABLED, []))
    out = []
    for cname, cfg in st["configs"].items():
        seen, mods = set(), []
        for t in cfg.get("tags", []):
            if t == DISABLED:
                continue
            for m in st["tagMods"].get(t, []):
                if m not in seen and m not in off:
                    seen.add(m)
                    mods.append(m)
        # extras wear no tag, so the union has no place to put them: they follow it
        for m in cfg.get("extras", []):
            if m not in seen and m not in off:
                seen.add(m)
                mods.append(m)
        out.append({"name": cname, "mods": mods})
    return out


def cfg_lines(st):
    configs = {c["name"]: c for c in build_configs(st)}
    lines, placed = [], set()
    for name in st.get("lineOrder", []):
        if name in placed:
            continue
        placed.add(name)
        if name in configs:
            lines.append(configs[name])
        elif name in st["tagMods"]:
            lines.append({"name": name, "mods": st["tagMods"][name]})
        elif name in st["passthrough"]:
            lines.append({"name": name, "mods": st["passthrough"][name]})
    for name in st.get("tagOrder", []) + sorted(st["tagMods"]):
        if name not in placed and name in st["tagMods"]:
            placed.add(name)
            lines.append({"name": name, "mods": st["tagMods"][name]})
    for name, c in configs.items():
        if name not in placed:
            placed.add(name)
            lines.append(c)
    return lines


def mod_tags(st):
    out = {}
    for t in st.get("tagOrder", []) or sorted(st["tagMods"]):
        for m in st["tagMods"].get(t, []):
            out.setdefault(m, [])
            if t not in out[m]:
                out[m].append(t)
    for t, mods in st["tagMods"].items():          # any tag missing from tagOrder
        for m in mods:
            out.setdefault(m, [])
            if t not in out[m]:
                out[m].append(t)
    return out


# --------------------------------------------------------------------------
# sources 4 and 5: Steam
# --------------------------------------------------------------------------

UA = {"User-Agent": "pzmods/2.0 (local mod manager)"}


def steam_details(ids, progress=None):
    """Public GetPublishedFileDetails. No authentication, no credentials."""
    out, errors = {}, []
    ids = [str(i) for i in ids]
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        if progress:
            progress(i, len(ids))
        data = [("itemcount", str(len(chunk)))]
        for n, fid in enumerate(chunk):
            data.append(("publishedfileids[%d]" % n, fid))
        req = urllib.request.Request(
            "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
            data=urllib.parse.urlencode(data).encode(), headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                j = json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            errors.append(str(e))
            continue
        for d in (j.get("response", {}).get("publishedfiledetails") or []):
            fid = d.get("publishedfileid")
            if not fid:
                continue
            out[fid] = {
                "result": d.get("result"),
                "title": d.get("title", ""),
                "description": d.get("description", ""),
                "creator": d.get("creator", ""),
                "time_updated": d.get("time_updated", 0),
                "subscriptions": d.get("subscriptions", 0),
                "favorited": d.get("favorited", 0),
                "views": d.get("views", 0),
                "tags": [t.get("tag") for t in (d.get("tags") or [])],
                "banned": d.get("banned", 0),
                "fetched": int(time.time()),
            }
        time.sleep(0.25)
    steam_details.last_errors = errors
    return out


HTML_TAG_RE = re.compile(r"<[^>]+>")


def steam_comments(fileid, creator, count=30):
    url = ("https://steamcommunity.com/comment/PublishedFile_Public/render/%s/%s/"
           "?start=0&count=%d" % (creator, fileid, count))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            j = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"error": str(e), "comments": []}
    html = j.get("comments_html") or ""
    items = []
    for m in re.finditer(r'<div class="commentthread_comment_text"[^>]*>(.*?)</div>', html, re.S):
        txt = HTML_TAG_RE.sub("", m.group(1))
        txt = (txt.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<")
                  .replace("&gt;", ">").replace("&#39;", "'").strip())
        if txt:
            items.append(txt)
    return {"total": j.get("total_count", len(items)), "comments": items,
            "fetched": int(time.time())}


# --------------------------------------------------------------------------
# the one Update pass
# --------------------------------------------------------------------------

STATE_LOCK = threading.Lock()

JOB = {"running": False, "phase": "", "detail": "", "pct": 0, "log": [],
       "started": "", "finished": "", "error": "", "seq": 0}


def job_log(msg):
    JOB["log"].append(msg)
    print("  " + msg)


def job_set(phase, detail="", pct=None):
    JOB["phase"] = phase
    JOB["detail"] = detail
    if pct is not None:
        JOB["pct"] = int(pct)
    JOB["seq"] += 1


def run_update(deep=False, with_comments=None):
    """Read every source, in one pass. This is the only refresh the user needs."""
    if JOB["running"]:
        return
    JOB.update({"running": True, "log": [], "error": "", "pct": 0,
                "started": now(), "finished": ""})
    t0 = time.time()
    if with_comments is None:
        with_comments = bool(SET.get("fetchCommentsOnUpdate"))
    try:
        with STATE_LOCK:
            # first, because it decides which mod.info of each mod is the live one
            g = resolve_game_version()
            job_log("game build: %s, from %s" % (g["version"], g["source"]))

            job_set("workshop folder", str(CONTENT), 5)
            disk, err = scan_workshop()
            if err:
                job_log(err)
            job_log("workshop folder: %d items, %d mods"
                    % (len(disk), sum(len(d["mods"]) for d in disk.values())))

            job_set("your mods folder", str(LOCAL_MODS), 15)
            local = scan_local_mods()
            job_log("your mods folder: %d mods" % len(local))

            job_set("Steam manifest", ACF.name, 20)
            acf = parse_acf()
            job_log("Steam manifest: %d records, %d marked subscribed"
                    % (len(acf), sum(1 for v in acf.values() if v.get("subscribed"))))

            job_set("config file", CFG.name, 25)
            st = reconcile_cfg(load_tags(), job_log)
            save_tags(st)
            job_log("config file: %d tags, %d configs"
                    % (len(st["tagMods"]), len(st["configs"])))

            snap = {"disk": disk, "localMods": local, "acf": acf,
                    "scanned": now(), "workshopError": err or ""}
            jwrite(SNAP_FILE, snap)

        # ---- online, outside the lock so the UI stays responsive
        subs = read_subs()[0]
        ids = set(disk) | {s["id"] for s in subs}
        steam = jread(DATA / "steam.json", {})
        if deep:
            todo = sorted(ids)
        else:
            todo = sorted(i for i in ids
                          if i not in steam
                          or (acf.get(i, {}).get("timeupdated", 0)
                              > steam.get(i, {}).get("time_updated", 0)))
        if todo:
            job_set("Workshop metadata", "%d items to fetch" % len(todo), 30)
            got = steam_details(todo, progress=lambda i, n: job_set(
                "Workshop metadata", "%d of %d" % (i, n), 30 + 40 * i / max(n, 1)))
            steam.update(got)
            jwrite(DATA / "steam.json", steam)
            errs = getattr(steam_details, "last_errors", [])
            job_log("Workshop metadata: %d fetched%s"
                    % (len(got), (", %d batches failed (%s)" % (len(errs), errs[0])) if errs else ""))
        else:
            job_log("Workshop metadata: already current for %d items" % len(steam))
        JOB["pct"] = 70

        if with_comments:
            need = []
            for i in sorted(ids & set(disk)):
                cache = DATA / "comments" / ("%s.json" % i)
                c = jread(cache, None)
                if c is None or c.get("fetched", 0) < steam.get(i, {}).get("time_updated", 0):
                    need.append(i)
            job_set("user comments", "%d pages to read" % len(need), 70)
            done = 0
            for i in need:
                creator = steam.get(i, {}).get("creator")
                if creator:
                    d = steam_comments(i, creator)
                    jwrite(DATA / "comments" / ("%s.json" % i), d)
                done += 1
                job_set("user comments", "%d of %d" % (done, len(need)),
                        70 + 25 * done / max(len(need), 1))
                time.sleep(0.25)
            job_log("user comments: refreshed %d" % len(need))
        else:
            job_log("user comments: fetched per mod on demand "
                    "(turn on fetchCommentsOnUpdate in settings.json for all of them)")

        JOB["pct"] = 100
        job_set("done", "%.1fs" % (time.time() - t0), 100)
        job_log("update finished in %.1fs" % (time.time() - t0))
    except Exception as e:
        JOB["error"] = str(e)
        job_log("update failed: %s" % e)
    finally:
        JOB["running"] = False
        JOB["finished"] = now()


def start_update(deep=False, with_comments=None):
    if JOB["running"]:
        return False
    threading.Thread(target=run_update, args=(deep, with_comments), daemon=True).start()
    return True


# --------------------------------------------------------------------------
# consistency checks
# --------------------------------------------------------------------------

def compute_issues(state):
    disk = state["disk"]
    acf = state["acf"]
    # ---- who is actually subscribed ------------------------------------------
    # Two witnesses, and they age differently. Steam rewrites its manifest the
    # moment you subscribe or unsubscribe; the synced profile list is frozen at
    # the moment you took it. So the manifest decides wherever it has anything to
    # say, and the synced list only fills the gap it cannot cover: an item Steam
    # is not tracking at all. When the manifest is newer than the sync, even that
    # gap goes to the manifest - an entry Steam has since dropped is an
    # unsubscribe that happened after the snapshot was taken, not a subscription
    # waiting to download.
    live = {s["id"]: s.get("title", "") for s in state["subs"]}
    acf_subs = {k for k, v in acf.items() if v.get("subscribed")}
    acf_known = set(acf)
    stale_subs = []
    if live:
        sync_is_fresh = state.get("subsFetched", 0) >= state.get("acfMtime", 0)
        subs = {k: live.get(k, "") for k in acf_subs}
        for i, title in live.items():
            if i in acf_known:
                continue
            if sync_is_fresh:
                subs[i] = title          # subscribed, Steam has not fetched it yet
            else:
                stale_subs.append((i, title))
    else:
        subs = {k: "" for k in acf_subs}
    tags = state["tags"]
    steam = state["steam"]

    # Every id a folder declares counts as installed, not only the active one - a
    # mod folder may declare a different id in each version folder, and the config
    # file may legitimately name any of them.
    mod2ws = {}
    for ws, d in disk.items():
        for m in d["mods"]:
            for mid in (m.get("modIds") or [m["modId"]]):
                mod2ws.setdefault(mid, ws)
    for m in state["localMods"]:
        for mid in (m.get("modIds") or [m["modId"]]):
            mod2ws.setdefault(mid, "local")

    off = set(tags.get(DISABLED, []))
    live_mods = [m for ws, d in sorted(disk.items()) for m in d["mods"]
                 if m["modId"] not in off]

    tagged = set()
    for mods in tags.values():
        tagged |= set(mods)
    cfg_ids = set(tagged)
    for c in state["configs"].values():
        cfg_ids |= set(c.get("extras", []))

    issues = []

    def add(kind, severity, title, items, hint="", verb=""):
        if items:
            issues.append({"kind": kind, "severity": severity, "title": title,
                           "items": items, "hint": hint, "verb": verb})

    folders = set(disk)
    add("stale_subs", "info", "Your synced profile list has gone out of date",
        [{"id": i, "title": t or steam.get(i, {}).get("title", ""),
          "note": "unsubscribed since the sync"} for i, t in sorted(stale_subs, key=lambda x: int(x[0]))],
        "You synced your profile on %s, and Steam's manifest has been rewritten "
        "since. These were in that snapshot but Steam now has no record of them and "
        "no folder - you unsubscribed them after the snapshot was taken. pzmods is "
        "ignoring the snapshot for these and treating them as unsubscribed, which is "
        "what they are. Re-sync, or drop the live list on the Setup tab, and this "
        "card goes away. Any mod ids they left behind in your config file are listed "
        "under \"Named in the config file, but not installed\"."
        % (datetime.fromtimestamp(state.get("subsFetched", 0)).strftime("%Y-%m-%d %H:%M")
           if state.get("subsFetched") else "an unknown date"))

    # An entry the manifest knows about but has no folder for is the stale record
    # the acf_ghost card explains, whichever witness called it subscribed. Report
    # it once, not twice. What is left here is the genuine case: the synced list
    # names something Steam is not tracking at all and has not downloaded.
    dead = acf_known - folders
    missing = [i for i in sorted(subs, key=int) if i not in folders and i not in dead]
    def why(i):
        d = steam.get(i, {})
        if d.get("result") == 9:
            return "the Workshop API says it is gone (result 9)"
        if d.get("banned"):
            return "banned on the Workshop"
        if d.get("title"):
            return "still listed on the Workshop - Steam has not downloaded it"
        return "no Workshop metadata yet - press Update"
    add("sub_not_installed", "warn", "Subscribed but not on disk",
        [{"id": i, "title": subs[i] or steam.get(i, {}).get("title", ""), "note": why(i)}
         for i in missing],
        "Subscribed, per the source pzmods trusts, but there is no folder. The note "
        "on each row says which case it is: an item the author removed or made "
        "private can never download, while one that is still listed simply has not "
        "been fetched yet.")

    add("orphan_folder", "warn",
        "On disk but not subscribed" if live else "On disk but Steam's manifest does not mark them subscribed",
        [{"id": i, "title": steam.get(i, {}).get("title", ""),
          "mods": [m["modId"] for m in disk[i]["mods"]]}
         for i in sorted(folders, key=int) if subs and i not in subs],
        "Project Zomboid scans the folder, not Steam's manifest, so these still appear "
        "in the in-game mod list.")

    add("acf_ghost", "info", "In Steam's manifest, but there is no folder",
        [{"id": i, "title": steam.get(i, {}).get("title", ""),
          "note": "%.0f KB recorded" % (acf[i].get("size", 0) / 1024.0)
                  if acf.get(i, {}).get("size") else ""}
         for i in sorted(set(acf) - folders, key=int)] if acf else [],
        "Steam's own bookkeeping, not yours. When an item is delisted or unsubscribed, "
        "Steam deletes the folder but can leave the record behind in "
        "appworkshop_108600.acf, still marked installed and subscribed. That stale "
        "record is the only place pzmods sees this id. The game never loads it - it "
        "scans folders, and there is no folder. Harmless; Steam clears it on its own "
        "eventually, or a Verify Integrity of Game Files does it now.")

    add("acf_unknown", "info", "On disk, but Steam's manifest has no record",
        [{"id": i, "title": steam.get(i, {}).get("title", ""),
          "mods": [m["modId"] for m in disk[i]["mods"]]}
         for i in sorted(folders - set(acf), key=int)] if acf else [],
        "A folder Steam is not tracking - usually a manual copy, or an interrupted "
        "download. The game will still load it.")

    dupes = []
    for name, mods in tags.items():
        seen, d = set(), []
        for m in mods:
            if m in seen and m not in d:
                d.append(m)
            seen.add(m)
        if d:
            dupes.append({"set": name, "mods": d})
    add("duplicate_in_tag", "warn", "The same mod listed twice inside one tag", dupes,
        "Harmless once configs are generated as unions, but the tag itself should be clean.")

    add("empty_tag", "info", "Tag with no mods",
        [{"tag": t} for t in sorted(tags) if not tags[t] and t != DISABLED],
        "Either file something under it or delete it on the Tags tab.")

    # Where is each name in the file actually written? Say so, rather than making
    # the user grep the config to find out why pzmods is talking about a mod.
    def whereis(m):
        in_tags = [t for t in state["tagOrder"] if m in tags.get(t, [])]
        in_cfgs = [c for c in sorted(state["configs"])
                   if m in (state["configs"][c].get("extras") or [])]
        bits = []
        bits.append("tags " + ", ".join(in_tags) if in_tags else "no tag")
        if in_cfgs:
            bits.append("carried in " + ", ".join(in_cfgs))
        return "; ".join(bits)

    gone = [m for m in sorted(cfg_ids) if m not in mod2ws]
    add("unknown_mod", "warn", "Named in the config file, but not installed",
        [{"mod": m, "config": whereis(m)} for m in gone],
        "No mod.info anywhere on disk declares these ids, so the game ignores them. "
        "They are almost always leftovers: the mod was unsubscribed or deleted, but "
        "its name stayed behind in the lines it was written into. pzmods keeps "
        "carrying them so it never silently loses anything - press "
        "\"Forget the %d uninstalled\" on this card to strike them out of every tag "
        "and config at once." % len(gone))

    add("config_only", "warn", "Installed and in a config, but wearing no tag",
        [{"config": c, "mod": m} for c in sorted(state["configs"])
         for m in state["configs"][c].get("extras", []) if m in mod2ws],
        "A config should be nothing but a union of tags. These are carried along so "
        "nothing is lost, but give them a tag and the carry clears itself.")

    tagged_ws = {mod2ws[m] for m in tagged if m in mod2ws}
    add("untagged", "info", "Installed but carrying no tag",
        [{"id": i, "title": steam.get(i, {}).get("title", ""),
          "mods": [m["modId"] for m in disk[i]["mods"]]}
         for i in sorted(folders, key=int)
         if i not in tagged_ws and (not subs or i in subs)],
        "These can never appear in any config.")

    add("will_grow", "info", "Saving will add these to a config",
        [{"config": c, "tag": t, "mods": ms}
         for c in sorted(state["configs"])
         for t, ms in (state["configs"][c].get("adds") or {}).items()],
        "The tag is part of this config, but the config line on disk is missing a few of "
        "the tag's mods - somebody added them to the tag by hand. The next Save puts them in, "
        "which is what tagging is for. Remove the tag from the config if that is not what you want.")

    add("config_gap", "warn", "A config names a tag that does not exist",
        [{"config": c, "theme": t} for c in state["configs"]
         for t in state["configs"][c].get("tags", []) if t not in tags],
        "Rename or remove it on the Configs tab.")

    add("disabled_needed", "warn", "Disabled, but an enabled mod requires it",
        [{"mod": m["modId"], "themes": [r for r in m.get("require", []) if r in off]}
         for m in live_mods if any(r in off for r in m.get("require", []))],
        "You switched the dependency off but kept the mod that needs it on. The mod "
        "that needs it will not load. Either disable it too, or take the dependency "
        "back off the %s tag." % DISABLED, verb="needs")

    inc = []
    for m in live_mods:
        clash = [x for x in m.get("incompatible", []) if x in mod2ws and x not in off]
        if clash:
            inc.append({"mod": m["modId"], "themes": clash})
    add("incompatible", "warn", "Declares another installed mod incompatible", inc,
        "Read from mod.info incompatible=. Both are installed and neither is "
        "disabled, so any config holding both is asking for trouble. Putting one on "
        "the %s tag settles it." % DISABLED, verb="excludes")

    # Two maps that ship the same world cell are both trying to BE that cell, and
    # only one of them can: the game hands the cell to whichever mod the config line
    # names last, and the other map loses that piece of itself. Overlap with the
    # vanilla map is deliberately not reported - a mod that rebuilds a corner of
    # Louisville overlaps it on purpose, and saying so about nearly every map mod
    # would bury the case that actually needs a decision.
    owners = {}
    for m in live_mods + [x for x in state["localMods"] if x["modId"] not in off]:
        for mp in m.get("maps") or []:
            for cell in mp["cells"]:
                owners.setdefault(tuple(cell), []).append((m["modId"], mp["name"]))
    shared = {}
    for cell, who in owners.items():
        who = sorted(set(who))
        for i, a in enumerate(who):
            for b in who[i + 1:]:
                shared.setdefault((a, b), []).append(cell)

    overlaps = []
    for (a, b), cs in sorted(shared.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        # Which of the two the game would keep, decided the same way everything else
        # about load order is: by the config line. Different configs can order the
        # two tags differently, so the answer is only worth stating when it is the
        # same everywhere.
        last = {a[0] if mods.index(a[0]) > mods.index(b[0]) else b[0]
                for mods in state["configOrder"].values()
                if a[0] in mods and b[0] in mods}
        if len(last) == 1:
            note = "%s is loaded last, so it takes them" % last.pop()
        elif last:
            note = "which one takes them depends on the config"
        else:
            note = "no config loads both, so nothing is lost yet"
        cs.sort()
        overlaps.append({"mod": a[0], "map": a[1], "other": b[0], "otherMap": b[1],
                         "cells": len(cs), "note": note,
                         "at": " ".join("%d,%d" % c for c in cs[:8])
                               + (" ..." if len(cs) > 8 else "")})
    add("map_overlap", "warn", "Two modded maps cover the same ground", overlaps,
        "Read from the world_<x>_<y>.lotpack files each map ships, one per 300x300 "
        "world cell, numbered in the vanilla map's own grid - so this is where the "
        "maps really are, not where anyone said they were. A cell belongs to exactly "
        "one mod: the game gives it to whichever of the two the config line names "
        "last, and that much of the other map is simply not there. Move the tag on "
        "the Configs tab, or the mod inside its tag on the Mods tab, to choose which "
        "one wins; put one on the %s tag to settle it outright. Overlap with the "
        "vanilla map is not listed - a mod that rebuilds part of Louisville is "
        "supposed to sit on top of it." % DISABLED)

    build = GAME["version"]
    add("version_conflict", "warn", "Built for a different game version",
        [{"mod": m["modId"],
          "range": "%s - %s - %s" % (m.get("versionMin") or "any", build,
                                     m.get("versionMax") or "any"),
          "note": ("needs %s or newer" % m["versionMin"]) if m["versionFit"] == "too new"
                  else "was last built for %s" % m["versionMax"]}
         for m in live_mods if m.get("versionFit")],
        "versionMin= and versionMax= in mod.info say which builds the mod is for. The "
        "build they are compared against is %s, read from %s - the game writes its own "
        "version into its debug log every time it starts, so this cannot go stale the "
        "way a number typed into settings.json does. Set gameVersion in settings.json "
        "to a version instead of \"auto\" to override it. A bound that is not a version "
        "at all is ignored rather than guessed at." % (build, GAME["source"]))

    add("missing_require", "warn", "Requires a mod that is not installed",
        [{"mod": m["modId"],
          "themes": [r for r in m.get("require", []) if r not in mod2ws]}
         for m in live_mods
         if any(r not in mod2ws for r in m.get("require", []))],
        "Read from mod.info require=. The mod will not load without these. "
        "Leading backslashes and trailing commas, which most Build 42 mod.info files "
        "write, are stripped before the comparison - they are punctuation, not part "
        "of the id. Mods on the %s tag are skipped." % DISABLED, verb="needs")

    # A config line IS the load order - the game loads the mods in the order the
    # line names them - so any rule about which mod comes first is a rule about this
    # line. Three of them are readable from mod.info: require= names a dependency,
    # and loadModAfter= / loadModBefore= state the order outright (those two, with
    # incompatible=, are the only sorting rules Build 42 reads from a version
    # folder; loadAfter/loadBefore/loadFirst/loadLast are the older names and are
    # only read from common). A rule is checked only when both mods are in the same
    # line: one of them missing or disabled is another card's problem, not this one.
    by_id, alias = {}, {}
    for m in [x for d in disk.values() for x in d["mods"]] + state["localMods"]:
        by_id[m["modId"]] = m
        for mid in (m.get("modIds") or [m["modId"]]):
            alias.setdefault(mid, m["modId"])
    late = []
    for cname in sorted(state.get("configOrder", {})):
        at = {m: i for i, m in enumerate(state["configOrder"][cname])}
        for m, i in at.items():
            rec = by_id.get(m)
            if not rec:
                continue
            for field, verb in (("require", "requires"), ("loadAfter", "must load after"),
                                ("loadBefore", "must load before")):
                for named in rec.get(field, []):
                    other = alias.get(named)
                    if other is None or other == m or other not in at:
                        continue
                    wrong = at[other] < i if field == "loadBefore" else at[other] > i
                    if wrong:
                        late.append({"config": cname, "mod": m, "themes": [other],
                                     "rule": verb, "pos": i + 1, "otherPos": at[other] + 1})
    add("load_order", "warn", "Loaded in the wrong order for its own rules", late,
        "The config line is the load order, and in these lines a mod is named before "
        "something it declares it must follow - so the game reaches it too early. Read "
        "from require=, loadModAfter= and loadModBefore= in mod.info; the numbers are "
        "positions in that config's line. The fix is never on this tab: move the tag on "
        "the Configs tab, or move the mod inside its tag on the Mods tab, and this "
        "clears itself.")

    # There is deliberately no card listing what is on the Disabled tag. Switching a
    # mod off is a normal thing to do, not an inconsistency, and a tab meant for
    # things that need attention should not fill up with things that do not. The
    # cases that DO need attention are still reported: something enabled requiring a
    # disabled mod, above. The Mods tab has the "disabled only" filter for the list
    # itself.

    return issues


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------

def required_by(disk, local, off):
    """Which mods does something else actually depend on right now?

    Only requirers that are installed and not disabled count - a mod is not being
    held in place by something you have switched off, and knowing that is the point
    of the badge. A requirer may name any id the target's folder declares, so the
    lookup goes through the alias list and the answer is keyed by the active id.
    """
    alias = {}
    records = [m for d in disk.values() for m in d["mods"]] + list(local)
    for m in records:
        for mid in (m.get("modIds") or [m["modId"]]):
            alias.setdefault(mid, m["modId"])
    out = {}
    for m in records:
        if m["modId"] in off:
            continue
        for r in m.get("require", []):
            target = alias.get(r)
            if target and target != m["modId"]:
                out.setdefault(target, [])
                if m["modId"] not in out[target]:
                    out[target].append(m["modId"])
    return {k: sorted(v) for k, v in out.items()}


def load_state():
    snap = jread(SNAP_FILE, {"disk": {}, "localMods": [], "acf": {}, "scanned": ""})
    st = load_tags()
    steam = jread(DATA / "steam.json", {})
    state = {
        "paths": {"workshop": str(WORKSHOP), "zomboid": str(ZOMBOID), "cfg": str(CFG),
                  "localMods": str(LOCAL_MODS), "acf": str(ACF),
                  "cfgExists": CFG.exists(), "contentExists": CONTENT.is_dir()},
        "disabledTag": DISABLED,
        "settings": {"modImageSize": SET["modImageSize"],
                     "gameVersion": GAME["version"],
                     "gameVersionFrom": GAME["source"],
                     "gameVersionSetting": SET.get("gameVersion", "auto"),
                     "fetchCommentsOnUpdate": bool(SET.get("fetchCommentsOnUpdate")),
                     "updateOnStartup": bool(SET.get("updateOnStartup"))},
        "disk": snap.get("disk", {}),
        "localMods": snap.get("localMods", []),
        "acf": snap.get("acf", {}),
        "scanned": snap.get("scanned", ""),
        "workshopError": snap.get("workshopError", ""),
        "subs": read_subs()[0],
        "subsFetched": read_subs()[1],
        "acfMtime": int(ACF.stat().st_mtime) if ACF.exists() else 0,
        "steam": steam,
        "notes": jread(DATA / "notes.json", {}),
        # read fresh like every other source, never cached. None means the
        # discovery skill has never run against this folder
        "discoveries": jread(DISCOVERY / "discoveries.json", None),
        "verdicts": jread(DISCOVERY / "verdicts.json", {}),
        "tags": st["tagMods"],
        "tagOrder": st.get("tagOrder") or sorted(st["tagMods"]),
        "modTags": mod_tags(st),
        "configs": st["configs"],
        # the exact line each config would be written as. The Mods tab sorts by it,
        # so what you read there is what the file will say - not a second guess at it
        "configOrder": {c["name"]: c["mods"] for c in build_configs(st)},
        "passthrough": st["passthrough"],
        "dirty": bool(st.get("dirty")),
        "conflict": st.get("conflict"),
        "reloadedAt": st.get("reloadedAt", ""),
        "requiredBy": required_by(snap.get("disk", {}), snap.get("localMods", []),
                                  set(st["tagMods"].get(DISABLED, []))),
        "commentsCached": sorted(p.stem for p in (DATA / "comments").glob("*.json")),
        "backups": sorted([p.name for p in BACKUPS.glob("pz_modlist_settings.*.cfg")],
                          reverse=True)[:40],
    }
    state["issues"] = compute_issues(state)
    return state


# --------------------------------------------------------------------------
# sandbox: the option values a preset or a save carries
# --------------------------------------------------------------------------
#
# A mod that adds sandbox options declares them in media/sandbox-options.txt and
# names them in media/lua/shared/Translate/EN/Sandbox_EN.txt. The values live in two
# places, and pzmods edits both:
#
#   Zomboid\Sandbox Presets\*.cfg          text, read when a NEW game is started
#   Zomboid\Saves\<mode>\<save>\map_sand.bin   binary, what an EXISTING save runs on
#
# Neither is rewritten wholesale. A preset keeps its own comments, spacing and line
# order; a save keeps its header, its pair order and its trailing bytes. Only the
# values you actually changed are replaced, so a Save is never a whole-file diff.

PRESETS = ZOMBOID / "Sandbox Presets"
SAVES = ZOMBOID / "Saves"

OPTION_RE = re.compile(r"option\s+([\w.]+)\s*\{(.*?)\}", re.S)
FIELD_RE = re.compile(r"(\w+)\s*=\s*([^,\n}]+)")
TRANS_RE = re.compile(r'Sandbox_([\w.]+)\s*=\s*"((?:[^"\\]|\\.)*)"')
SAND_HEAD = 16  # "SAND", then three ints, the last of which is the pair count


def sandbox_folders(mod):
    """Build 42 loads a mod from common/ plus the one version folder it picked, and
    those two together are everything the game reads. The root media/ of a versioned
    mod is a leftover - it still declares options, under names nothing answers to."""
    base = Path(mod["path"])
    af = mod.get("activeFolder") or "(root)"
    return [base / "common", base if af == "(root)" else base / af]


def read_option_defs(disk, local):
    """option name -> what the mod declaring it says about it, and which mod that is."""
    defs = {}
    for mod in [m for rec in disk.values() for m in rec.get("mods", [])] + list(local):
        if not mod.get("path"):
            continue
        text, trans = "", {}
        for folder in sandbox_folders(mod):
            f = folder / "media" / "sandbox-options.txt"
            if f.is_file():
                text += "\n" + f.read_text(encoding="utf-8", errors="replace")
            t = folder / "media" / "lua" / "shared" / "Translate" / "EN" / "Sandbox_EN.txt"
            if t.is_file():
                for m in TRANS_RE.finditer(t.read_text(encoding="utf-8", errors="replace")):
                    trans[m.group(1)] = m.group(2)
        if not text.strip():
            continue
        # 14 mods here keep their Sandbox_EN.txt in the root media/ but their options in
        # a version folder. B42 never reads that root, so the game itself shows those
        # options untranslated - but a name exists only to be read, and an unread name
        # is worth nothing, so pzmods falls back to it. Nothing here is ever written.
        if not trans:
            t = Path(mod["path"]) / "media" / "lua" / "shared" / "Translate" / "EN" / "Sandbox_EN.txt"
            if t.is_file():
                for m in TRANS_RE.finditer(t.read_text(encoding="utf-8", errors="replace")):
                    trans[m.group(1)] = m.group(2)
        for m in OPTION_RE.finditer(text):
            body = dict((f.group(1), f.group(2).strip()) for f in FIELD_RE.finditer(m.group(2)))
            key = body.get("translation") or m.group(1)
            d = {"mod": mod["modId"], "modName": mod.get("name") or mod["modId"],
                 "type": body.get("type", ""), "default": body.get("default", ""),
                 "min": body.get("min", ""), "max": body.get("max", ""),
                 "label": trans.get(key, ""), "tip": trans.get(key + "_tooltip", ""),
                 "page": trans.get(body.get("page", ""), "") or body.get("page", "")}
            if d["type"] == "enum":
                try:
                    n = int(float(body.get("numValues") or 0))
                except ValueError:
                    n = 0
                d["choices"] = [trans.get("%s_option%d" % (key, i), str(i))
                                for i in range(1, n + 1)]
            defs[m.group(1)] = d
    return defs


def sandbox_targets():
    out = []
    for p in sorted(PRESETS.glob("*.cfg")):
        out.append({"id": "preset:" + p.stem, "kind": "preset", "label": p.stem,
                    "where": "every new game started from this preset",
                    "path": str(p), "mtime": int(p.stat().st_mtime)})
    for p in sorted(SAVES.glob("*/*/map_sand.bin")):
        out.append({"id": "save:%s/%s" % (p.parent.parent.name, p.parent.name), "kind": "save",
                    "label": "%s / %s" % (p.parent.parent.name, p.parent.name),
                    "where": "this save, the next time it loads",
                    "path": str(p), "mtime": int(p.stat().st_mtime)})
    return out


def sand_str(d, at):
    n = struct.unpack_from(">H", d, at)[0]
    return d[at + 2:at + 2 + n].decode("utf-8", "replace"), at + 2 + n


def sand_pairs(d):
    at, out = SAND_HEAD, []
    for _ in range(struct.unpack_from(">i", d, 12)[0]):
        k, at = sand_str(d, at)
        v, at = sand_str(d, at)
        out.append((k, v))
    return out, at


def read_target(t):
    """The values a target holds, in file order. Both formats are names and strings."""
    p = Path(t["path"])
    if t["kind"] == "save":
        d = p.read_bytes()
        if d[:4] != b"SAND":
            raise ValueError("%s does not begin with SAND" % p.name)
        return sand_pairs(d)[0]
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if s and not s.startswith(("#", "--")) and "=" in s:
            k, _, v = s.partition("=")
            # Version= is the file's own format stamp, not something the game reads
            # back as an option, and nothing good comes of offering it for editing
            if k.strip() != "Version":
                out.append((k.strip(), v.strip()))
    return out


def write_target(t, changes):
    p = Path(t["path"])
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^\w.-]", "_", t["label"])
    shutil.copy2(p, SAND_BACKUPS / ("%s.%s%s" % (safe, stamp, p.suffix)))
    # by age, not by name: this folder mixes presets and saves, and sorting the names
    # would throw away every backup of one file before touching the newest of another
    for old in sorted(SAND_BACKUPS.glob("*.*"), key=lambda f: f.stat().st_mtime)[:-60]:
        try:
            old.unlink()
        except OSError:
            pass

    left = dict(changes)
    if t["kind"] == "save":
        d = p.read_bytes()
        pairs, at = sand_pairs(d)
        body, seen = b"", set()
        for k, v in pairs:
            seen.add(k)
            body += utf_bytes(k) + utf_bytes(left.get(k, v))
        added = [k for k in left if k not in seen]
        for k in added:
            body += utf_bytes(k) + utf_bytes(left[k])
        out = d[:12] + struct.pack(">i", len(pairs) + len(added)) + body + d[at:]
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(out)
        tmp.replace(p)
        return len(changes), len(added)

    # newline="" or Python hands back every line ending as \n and the file loses the
    # CRLF the game wrote it with - a one-value edit would rewrite all 7242 lines
    with p.open("r", encoding="utf-8", errors="replace", newline="") as f:
        lines = f.read().splitlines(True)
    for i, line in enumerate(lines):
        s = line.strip()
        if s and not s.startswith(("#", "--")) and "=" in s:
            k = s.split("=", 1)[0].strip()
            if k in left:
                lines[i] = "%s=%s%s" % (k, left.pop(k), line[len(line.rstrip("\r\n")):])
    if left:
        # the game leaves the last line unterminated, so anything appended has to
        # close it first - and a write that appends nothing must not touch it at all
        nl = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += nl
        for k, v in left.items():
            lines.append("%s=%s%s" % (k, v, nl))
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        f.write("".join(lines))
    tmp.replace(p)
    return len(changes), len(left)


def utf_bytes(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def game_running():
    """A save rewrites map_sand.bin from memory when it saves, so an edit made while
    the game is up is an edit thrown away without a word."""
    try:
        out = subprocess.run(["tasklist", "/fi", "imagename eq ProjectZomboid*"],
                             capture_output=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return b"ProjectZomboid" in out.stdout
    except Exception:
        return False


def sandbox_view(tid):
    """One target's options, grouped under the mod that declares each one. Options a
    mod declares but the file has never held are listed too, showing the default the
    game would fall back to - those are exactly the ones worth setting."""
    t = next((x for x in sandbox_targets() if x["id"] == tid), None)
    if not t:
        return None
    snap = jread(SNAP_FILE, {"disk": {}, "localMods": []})
    defs = read_option_defs(snap.get("disk", {}), snap.get("localMods", []))
    vals = dict(read_target(t))
    off = set(load_tags()["tagMods"].get(DISABLED, []))

    groups = {}
    for name in sorted(set(vals) | set(defs), key=lambda s: s.lower()):
        d = defs.get(name) or {}
        row = {"name": name, "value": vals.get(name, d.get("default", "")),
               "inFile": name in vals, "type": d.get("type", ""),
               "default": d.get("default", ""), "min": d.get("min", ""),
               "max": d.get("max", ""), "label": d.get("label", ""),
               "tip": d.get("tip", ""), "page": d.get("page", "")}
        if d.get("choices"):
            row["choices"] = d["choices"]
        g = groups.setdefault(d.get("mod", ""), {
            "mod": d.get("mod", ""),
            "modName": d.get("modName") or "not declared by any installed mod",
            "off": d.get("mod", "") in off, "options": []})
        g["options"].append(row)

    known = sorted((g for g in groups.values() if g["mod"]),
                   key=lambda g: g["modName"].lower())
    return {"target": t, "groups": known + [g for g in groups.values() if not g["mod"]],
            "inFile": len(vals), "gameRunning": t["kind"] == "save" and game_running()}


# --------------------------------------------------------------------------
# http
# --------------------------------------------------------------------------

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "pzmods"

    def log_message(self, fmt, *args):
        p = self.path or ""
        if "/api/" in p and "progress" not in p:
            sys.stdout.write("  %s %s\n" % (self.command, p.split("?")[0]))

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        # Chrome refuses a request from a public page to a local server without this
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send(self, obj, code=200, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    # ---------------- GET ----------------
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)

        if u.path in ("/", "/index.html"):
            f = HERE / "ui.html"
            if not f.exists():
                return self._send(b"ui.html is missing next to pzmods.py", 500, "text/plain")
            return self._send(f.read_bytes(), 200, "text/html; charset=utf-8")

        if u.path == "/api/state":
            with STATE_LOCK:
                return self._send(load_state())

        if u.path == "/api/progress":
            return self._send(JOB)

        if u.path == "/api/comments":
            fid = (q.get("id") or [""])[0]
            cache = DATA / "comments" / ("%s.json" % fid)
            if not (q.get("refresh") or [""])[0] and cache.exists():
                return self._send(jread(cache, {}))
            steam = jread(DATA / "steam.json", {})
            creator = steam.get(fid, {}).get("creator")
            if not creator:
                got = steam_details([fid])
                creator = got.get(fid, {}).get("creator")
                if got:
                    steam.update(got)
                    jwrite(DATA / "steam.json", steam)
            if not creator:
                return self._send({"error": "no creator id known for %s" % fid, "comments": []})
            data = steam_comments(fid, creator)
            jwrite(cache, data)
            return self._send(data)

        if u.path == "/img":
            rel = (q.get("p") or [""])[0]
            local = (q.get("local") or [""])[0]
            try:
                p = (Path(local) if local else (CONTENT / rel)).resolve()
                roots = [CONTENT.resolve(), LOCAL_MODS.resolve()]
                if not any(str(p).startswith(str(r)) for r in roots) or not p.is_file():
                    raise ValueError("outside the mod folders")
                ctype = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                body = p.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "max-age=86400")
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
            return

        if u.path == "/api/bookmarklet":
            flat = " ".join(x.strip() for x in BOOKMARKLET.splitlines() if x.strip())
            return self._send(flat.encode("utf-8"), 200, "text/plain; charset=utf-8")

        if u.path == "/api/preview-cfg":
            with STATE_LOCK:
                st = load_tags()
            body = render_cfg(cfg_lines(st), st.get("trailingSep", ";"))
            return self._send(body.encode("utf-8"), 200, "text/plain; charset=utf-8")

        # kept out of /api/state: this is a few thousand options that only the Sandbox
        # tab wants, and every other tab asks for the state after every edit
        if u.path == "/api/sandbox":
            tid = (q.get("target") or [""])[0]
            if not tid:
                return self._send({"targets": sandbox_targets()})
            try:
                with STATE_LOCK:
                    view = sandbox_view(tid)
            except Exception as e:
                return self._send({"error": "%s: %s" % (type(e).__name__, e)}, 400)
            if not view:
                return self._send({"error": "no sandbox file called %s" % tid}, 404)
            return self._send(view)

        return self._send({"error": "not found"}, 404)

    # ---------------- POST ----------------
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8", "replace") or "{}")
        except Exception as e:
            return self._send({"error": "bad json: %s" % e}, 400)

        if u.path == "/api/update":
            started = start_update(deep=bool(payload.get("deep")),
                                   with_comments=payload.get("comments"))
            return self._send({"ok": True, "started": started, "running": JOB["running"]})

        if u.path == "/api/sandbox":
            tid = payload.get("target") or ""
            changes = payload.get("changes") or {}
            t = next((x for x in sandbox_targets() if x["id"] == tid), None)
            if not t:
                return self._send({"error": "no sandbox file called %s" % tid}, 404)
            if not changes:
                return self._send({"error": "nothing to write"}, 400)
            if t["kind"] == "save" and game_running() and not payload.get("anyway"):
                return self._send({"error": "Project Zomboid is running. It writes this "
                                            "file back from memory when the save saves, "
                                            "which would undo this."}, 409)
            try:
                with STATE_LOCK:
                    changed, added = write_target(t, changes)
                    view = sandbox_view(tid)
            except Exception as e:
                return self._send({"error": "%s: %s" % (type(e).__name__, e)}, 500)
            job_log("sandbox: wrote %d value(s) to %s, %d of them new"
                    % (changed, t["label"], added))
            return self._send({"ok": True, "changed": changed, "added": added, "view": view})

        if u.path == "/api/subs":
            if isinstance(payload, dict) and payload.get("clear"):
                jwrite(DATA / "subs.json", {"fetched": 0, "items": []})
                print("  live subscription list dropped; falling back to the Steam manifest")
                return self._send({"ok": True, "count": 0})
            items = payload.get("items") if isinstance(payload, dict) else payload
            if not isinstance(items, list):
                return self._send({"error": "expected a list"}, 400)
            clean = [{"id": str(i.get("id")), "title": i.get("title") or ""}
                     for i in items if isinstance(i, dict) and i.get("id")]
            jwrite(DATA / "subs.json", {"fetched": int(time.time()), "items": clean})
            print("  received %d subscriptions from the browser" % len(clean))
            return self._send({"ok": True, "count": len(clean)})

        if u.path == "/api/settings":
            changed = {}
            if "modImageSize" in payload:
                SET["modImageSize"] = max(16, min(96, int(payload["modImageSize"])))
                changed["modImageSize"] = SET["modImageSize"]
            for k in ("fetchCommentsOnUpdate", "updateOnStartup"):
                if k in payload:
                    SET[k] = bool(payload[k])
                    changed[k] = SET[k]
            save_settings(SET)
            return self._send({"ok": True, "changed": changed})

        if u.path == "/api/notes":
            notes = jread(DATA / "notes.json", {})
            mid = payload.get("key")
            if not mid:
                return self._send({"error": "key required"}, 400)
            note = payload.get("note") or {}
            # a note with nothing in it is not a note; keeping the key would leave
            # the mod wearing a "note" badge with no text behind it
            if (note.get("text") or "").strip():
                notes[mid] = note
            else:
                notes.pop(mid, None)
            jwrite(DATA / "notes.json", notes)
            return self._send({"ok": True})

        # your verdict on discovered items. Keyed by workshop id so it outlives
        # the run that found the item, and the next run can skip what you dismissed.
        # Takes "id" for one row or "ids" for a whole group - one read-modify-write
        # either way, so a group of 300 cannot half-succeed
        if u.path == "/api/verdict":
            raw = payload.get("ids") if isinstance(payload.get("ids"), list) \
                else [payload.get("id")]
            ids = [str(x) for x in raw if str(x or "")]
            verdict = (payload.get("verdict") or "").strip()
            if not ids:
                return self._send({"error": "id required"}, 400)
            if verdict not in ("", "interested", "dismissed"):
                return self._send({"error": "unknown verdict %r" % verdict}, 400)
            v = jread(DISCOVERY / "verdicts.json", {})
            if not isinstance(v, dict):
                v = {}
            stamp = now()
            for wid in ids:
                if verdict:
                    v[wid] = {"verdict": verdict, "at": stamp}
                else:
                    v.pop(wid, None)
            DISCOVERY.mkdir(parents=True, exist_ok=True)
            jwrite(DISCOVERY / "verdicts.json", v)
            return self._send({"ok": True, "verdicts": v})

        # ---- tag vocabulary: add / rename / delete, on the Tags tab only
        if u.path == "/api/tag":
            with STATE_LOCK:
                st = load_tags()
                act = payload.get("action")
                name = (payload.get("name") or "").strip()
                to = (payload.get("to") or "").strip()
                if act in ("rename", "delete") and name == DISABLED:
                    return self._send({"error": "%s is built in - it cannot be renamed "
                                                "or deleted" % DISABLED}, 400)
                if act == "add":
                    bad = valid_tag_name(name)
                    if bad:
                        return self._send({"error": bad}, 400)
                    if name in st["tagMods"]:
                        return self._send({"error": "that tag already exists"}, 400)
                    st["tagMods"][name] = []
                    st["tagOrder"].append(name)
                    st["kinds"][name] = "tag"
                elif act == "rename":
                    if name not in st["tagMods"]:
                        return self._send({"error": "no such tag"}, 400)
                    bad = valid_tag_name(to)
                    if bad:
                        return self._send({"error": bad}, 400)
                    if to in st["tagMods"]:
                        return self._send({"error": "that tag already exists"}, 400)
                    st["tagMods"][to] = st["tagMods"].pop(name)
                    st["tagOrder"] = [to if x == name else x for x in st["tagOrder"]]
                    st["lineOrder"] = [to if x == name else x for x in st["lineOrder"]]
                    st["kinds"].pop(name, None)
                    st["kinds"][to] = "tag"
                    for c in st["configs"].values():
                        c["tags"] = [to if x == name else x for x in c.get("tags", [])]
                elif act == "delete":
                    if st["tagMods"].get(name):
                        return self._send({"error": "that tag still has %d mods on it"
                                                    % len(st["tagMods"][name])}, 400)
                    st["tagMods"].pop(name, None)
                    st["tagOrder"] = [x for x in st["tagOrder"] if x != name]
                    st["lineOrder"] = [x for x in st["lineOrder"] if x != name]
                    st["kinds"].pop(name, None)
                    for c in st["configs"].values():
                        c["tags"] = [x for x in c.get("tags", []) if x != name]
                elif act == "move":
                    d = int(payload.get("delta") or 0)
                    o = st["tagOrder"]
                    if name in o:
                        i = o.index(name)
                        j = max(0, min(len(o) - 1, i + d))
                        o.insert(j, o.pop(i))
                elif act == "set-mods":
                    # the order of the mods inside a tag is load order, so it is
                    # reordered, never rewritten - refuse anything that is not a
                    # permutation of what the tag already holds
                    if name not in st["tagMods"]:
                        return self._send({"error": "no such tag"}, 400)
                    want = payload.get("mods") or []
                    if sorted(want) != sorted(st["tagMods"][name]):
                        return self._send({"error": "that is not a reordering of %s - it "
                                                    "must hold exactly the same mods" % name}, 400)
                    st["tagMods"][name] = list(want)
                else:
                    return self._send({"error": "unknown action"}, 400)
                st["dirty"] = True
                save_tags(st)
                return self._send({"ok": True, "state": load_state()})

        # ---- tag membership: set the tags on one mod, or bulk add/remove
        if u.path == "/api/mod-tags":
            with STATE_LOCK:
                st = load_tags()
                mods = payload.get("mods") or ([payload["mod"]] if payload.get("mod") else [])
                if not mods:
                    return self._send({"error": "no mods given"}, 400)
                act = payload.get("action") or "set"
                if act == "set":
                    want = payload.get("tags") or []
                    bad = [t for t in want if t not in st["tagMods"]]
                    if bad:
                        return self._send({"error": "unknown tag: %s" % bad[0]}, 400)
                    for t, lst in st["tagMods"].items():
                        keep = t in want
                        st["tagMods"][t] = [m for m in lst if m not in mods or keep]
                        if keep:
                            for m in mods:
                                if m not in st["tagMods"][t]:
                                    st["tagMods"][t].append(m)
                elif act in ("add", "remove"):
                    t = payload.get("tag")
                    if t not in st["tagMods"]:
                        return self._send({"error": "unknown tag"}, 400)
                    if act == "add":
                        for m in mods:
                            if m not in st["tagMods"][t]:
                                st["tagMods"][t].append(m)
                    else:
                        st["tagMods"][t] = [m for m in st["tagMods"][t] if m not in mods]
                elif act == "clear":
                    for t, lst in st["tagMods"].items():
                        st["tagMods"][t] = [m for m in lst if m not in mods]
                else:
                    return self._send({"error": "unknown action"}, 400)
                st["dirty"] = True
                save_tags(st)
                return self._send({"ok": True, "state": load_state()})

        # ---- configs: an ordered list of tags, nothing else
        if u.path == "/api/config":
            with STATE_LOCK:
                st = load_tags()
                act = payload.get("action")
                name = (payload.get("name") or "").strip()
                if act == "add":
                    if line_kind(name) != "config":
                        return self._send({"error": "a config name must look like "
                                                    "\"-4- Something\""}, 400)
                    if name in st["configs"]:
                        return self._send({"error": "that config already exists"}, 400)
                    st["configs"][name] = {"tags": [], "extras": []}
                    st["lineOrder"].append(name)
                elif act == "delete":
                    st["configs"].pop(name, None)
                    st["lineOrder"] = [x for x in st["lineOrder"] if x != name]
                elif act == "rename":
                    to = (payload.get("to") or "").strip()
                    if line_kind(to) != "config":
                        return self._send({"error": "a config name must look like "
                                                    "\"-4- Something\""}, 400)
                    if name not in st["configs"] or to in st["configs"]:
                        return self._send({"error": "bad rename"}, 400)
                    st["configs"][to] = st["configs"].pop(name)
                    st["lineOrder"] = [to if x == name else x for x in st["lineOrder"]]
                elif act == "set-tags":
                    if name not in st["configs"]:
                        return self._send({"error": "no such config"}, 400)
                    want = [t for t in (payload.get("tags") or [])
                            if t in st["tagMods"] and t != DISABLED]
                    st["configs"][name]["tags"] = want
                elif act == "move-tag":
                    c = st["configs"].get(name)
                    if not c:
                        return self._send({"error": "no such config"}, 400)
                    t, d = payload.get("tag"), int(payload.get("delta") or 0)
                    if t in c["tags"]:
                        i = c["tags"].index(t)
                        j = max(0, min(len(c["tags"]) - 1, i + d))
                        c["tags"].insert(j, c["tags"].pop(i))
                elif act == "clear-extras":
                    if name in st["configs"]:
                        st["configs"][name]["extras"] = []
                else:
                    return self._send({"error": "unknown action"}, 400)
                st["dirty"] = True
                save_tags(st)
                return self._send({"ok": True, "state": load_state()})

        if u.path == "/api/forget-missing":
            """Strike every id that no mod.info declares out of all tags and configs."""
            with STATE_LOCK:
                st = load_tags()
                snap = jread(SNAP_FILE, {"disk": {}, "localMods": []})
                known = {m["modId"] for d in snap.get("disk", {}).values() for m in d["mods"]}
                known |= {m["modId"] for m in snap.get("localMods", [])}
                gone = set()
                for t, mods in st["tagMods"].items():
                    for m in mods:
                        if m not in known:
                            gone.add(m)
                    st["tagMods"][t] = [m for m in mods if m in known]
                for c in st["configs"].values():
                    for m in c.get("extras", []):
                        if m not in known:
                            gone.add(m)
                    c["extras"] = [m for m in c.get("extras", []) if m in known]
                if payload.get("dryRun"):
                    return self._send({"ok": True, "would": sorted(gone)})
                if gone:
                    st["dirty"] = True
                    save_tags(st)
                    print("  forgot %d uninstalled mods: %s"
                          % (len(gone), ", ".join(sorted(gone))))
                return self._send({"ok": True, "forgot": sorted(gone),
                                   "state": load_state()})

        if u.path == "/api/open-folder":
            want = payload.get("path") or ""
            try:
                p = Path(want).resolve()
                roots = [CONTENT.resolve(), LOCAL_MODS.resolve(), HERE.resolve()]
                if not any(str(p).startswith(str(r)) for r in roots) or not p.exists():
                    return self._send({"error": "that path is not inside your mod folders"}, 400)
                if sys.platform.startswith("win"):
                    os.startfile(str(p))                     # noqa: S606
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(p)])
                else:
                    subprocess.Popen(["xdg-open", str(p)])
                return self._send({"ok": True, "path": str(p)})
            except Exception as e:
                return self._send({"error": str(e)}, 400)

        if u.path == "/api/write-cfg":
            with STATE_LOCK:
                st = load_tags()
                lines = cfg_lines(st)
                made = write_cfg(lines, st.get("trailingSep", ";"))
                for c in build_configs(st):
                    cfg = st["configs"].setdefault(c["name"], {"tags": [], "extras": []})
                    cfg["adds"] = {}                       # now on disk, nothing pending
                st["cfgFingerprint"] = cfg_fingerprint()
                st["lineOrder"] = [l["name"] for l in lines]
                st["dirty"] = False
                st["conflict"] = None
                st["reloadedAt"] = ""
                save_tags(st)
                return self._send({"ok": True, "backup": made, "lines": len(lines),
                                   "state": load_state()})

        if u.path == "/api/resolve-conflict":
            with STATE_LOCK:
                choice = payload.get("choice")
                if choice == "reload":
                    if TAGS_FILE.exists():
                        shutil.copy2(TAGS_FILE, DATA / ("tags.%s.json"
                                     % datetime.now().strftime("%Y%m%d-%H%M%S")))
                    st = seed_from_cfg(read_cfg(), load_tags().get("kinds"))
                    st["reloadedAt"] = now()
                elif choice == "keep":
                    st = load_tags()
                    st["conflict"] = None
                    st["cfgFingerprint"] = cfg_fingerprint()
                else:
                    return self._send({"error": "choice must be reload or keep"}, 400)
                save_tags(st)
                return self._send({"ok": True, "state": load_state()})

        if u.path == "/api/restore":
            name = payload.get("name") or ""
            src = BACKUPS / name
            if not src.exists() or src.parent != BACKUPS:
                return self._send({"error": "no such backup"}, 400)
            with STATE_LOCK:
                backup_cfg()
                shutil.copy2(src, CFG)
                st = seed_from_cfg(read_cfg(), load_tags().get("kinds"))
                st["reloadedAt"] = now()
                save_tags(st)
                return self._send({"ok": True, "state": load_state()})

        return self._send({"error": "not found"}, 404)


BOOKMARKLET = r"""
javascript:(async()=>{try{
var B=document.createElement('div');B.style.cssText='position:fixed;z-index:2147483647;right:16px;bottom:16px;background:#111;color:#fff;font:13px system-ui;padding:12px 16px;border-radius:9px;box-shadow:0 6px 24px rgba(0,0,0,.4);max-width:340px';document.body.appendChild(B);
var say=function(t,c){B.innerHTML=t;if(c)B.style.background=c;};
say('pzmods: reading page 1 ...');
if(!location.host.match(/steamcommunity\.com$/)){say('Open your Steam <b>Subscribed Items</b> page first, then click this again.','#a33');return;}
var base=location.href.split('#')[0].replace(/[&?]p=\d+/,'').replace(/[&?]numperpage=\d+/,'');
base+=(base.indexOf('?')<0?'?':'&')+'numperpage=30&p=';
var seen=new Map(),p=1;
for(;p<=80;p++){
 say('pzmods: reading page '+p+' ... found '+seen.size);
 var html=await (await fetch(base+p,{credentials:'include'})).text();
 var doc=new DOMParser().parseFromString(html,'text/html');
 var add=0;
 doc.querySelectorAll('a[href*="filedetails/?id="]').forEach(function(a){
  var m=a.href.match(/id=(\d+)/);if(!m)return;var id=m[1];
  var row=a.closest('.workshopItem')||(a.parentElement&&a.parentElement.parentElement&&a.parentElement.parentElement.parentElement);
  var t=row&&row.querySelector('.workshopItemTitle');
  if(!seen.has(id)){seen.set(id,t?t.textContent.trim():'');add++;}
  else if(!seen.get(id)&&t)seen.set(id,t.textContent.trim());});
 if(!add&&p>1)break;
}
var items=[];seen.forEach(function(v,k){items.push({id:k,title:v});});
if(!items.length){say('pzmods: found no items. Are you on the Subscribed Items page and signed in?','#a33');return;}
var payload=JSON.stringify({items:items});
try{
 var r=await fetch('http://127.0.0.1:PORT/api/subs',{method:'POST',headers:{'Content-Type':'application/json'},body:payload});
 if(!r.ok)throw new Error('HTTP '+r.status);
 say('pzmods: sent <b>'+items.length+'</b> subscriptions. Go back to pzmods and press <b>Update</b>.','#1b6b46');
 setTimeout(function(){B.remove();},9000);return;
}catch(e){
 try{await navigator.clipboard.writeText(payload);
  say('pzmods could not reach the local server ('+e.message+').<br><br><b>'+items.length+' subscriptions copied to your clipboard.</b><br>Paste them into the Sync box in pzmods.','#8a5a00');
 }catch(e2){
  var ta=document.createElement('textarea');ta.value=payload;ta.style.cssText='width:320px;height:90px;margin-top:8px';
  say('Could not reach the server and could not use the clipboard.<br>Copy this and paste it into pzmods:','#8a5a00');B.appendChild(ta);ta.select();
 }
}}catch(err){alert('pzmods bookmarklet failed: '+err.message);}})();
""".strip().replace("PORT", str(PORT))


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    no_open = "--no-open" in sys.argv
    print("pzmods")
    print("  workshop : %s" % CONTENT)
    print("  your mods: %s" % LOCAL_MODS)
    print("  config   : %s" % CFG)
    if SET.get("updateOnStartup", True):
        print("  running the startup update ...")
        start_update()
    url = "http://127.0.0.1:%d/" % PORT
    srv = Server(("127.0.0.1", PORT), Handler)
    print("  open %s" % url)
    print("  ctrl-c to stop")
    if not no_open:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  bye")


if __name__ == "__main__":
    main()
