### SCRIPT FOR NORMALIZING FOCUSES, PB_GER_Example_Focus -> GER_example_focus
from pathlib import Path
import os
import re

# =========================
# CONFIG (SUBFOLDER SAFE)
# =========================

SCRIPT_DIR = Path(__file__).resolve().parent
MOD_PATH = SCRIPT_DIR.parent

NATIONAL_FOCUS_PATH = MOD_PATH / "common" / "national_focus"

TARGET_FOLDERS = ("common", "events", "history", "localisation")
EXTENSIONS = (".txt", ".yml")

# =========================
# REGEX
# =========================

FOCUS_BLOCK = re.compile(r'focus\s*=\s*{.*?}', re.DOTALL)
ID_PATTERN = re.compile(r'\bid\s*=\s*([A-Za-z0-9_]+)')

# =========================
# NORMALIZATION
# =========================

def normalize(fid):
    if fid.startswith("PB_"):
        fid = fid[3:]

    parts = fid.split("_")

    if not parts:
        return fid

    first = parts[0]

    # TAG case
    if len(first) == 3 and first.isupper():
        tag = first
        rest = [p.lower() for p in parts[1:]]
        return "_".join([tag] + rest) if rest else tag

    # generic fallback
    return "generic_" + "_".join([p.lower() for p in parts])


# =========================
# STEP 1: SCAN FOCUS FILES
# =========================

print("Scanning national_focus folder...\n")

focus_ids = set()

for root, _, files in os.walk(NATIONAL_FOCUS_PATH):
    for file in files:
        if not file.endswith(".txt"):
            continue

        path = Path(root) / file

        try:
            text = path.read_text(encoding="utf-8")
        except:
            continue

        for block in FOCUS_BLOCK.findall(text):
            for fid in ID_PATTERN.findall(block):
                focus_ids.add(fid)

print(f"Found {len(focus_ids)} focus IDs")

# =========================
# STEP 2: BUILD MAP
# =========================

id_map = {}

for fid in focus_ids:
    new = normalize(fid)
    if fid != new:
        id_map[fid] = new

print(f"IDs to change: {len(id_map)}\n")

if not id_map:
    print("Nothing to change.")
    exit()

# =========================
# STEP 3: BUILD REGEX
# =========================

sorted_keys = sorted(id_map.keys(), key=len, reverse=True)

base_pattern = re.compile(r'\b(' + '|'.join(map(re.escape, sorted_keys)) + r')\b')
desc_pattern = re.compile(r'\b(' + '|'.join(map(re.escape, sorted_keys)) + r')_desc\b')

def replace_base(match):
    return id_map.get(match.group(1), match.group(1))

def replace_desc(match):
    old = match.group(1)
    return id_map.get(old, old) + "_desc"

# =========================
# STEP 4: APPLY
# =========================

print("Applying changes across mod...\n")

for root, _, files in os.walk(MOD_PATH):
    root_path = Path(root)

    # filter target folders
    if not any(folder in root_path.parts for folder in TARGET_FOLDERS):
        continue

    for file in files:
        if not file.endswith(EXTENSIONS):
            continue

        path = root_path / file

        try:
            content = path.read_text(encoding="utf-8")
        except:
            continue

        new_content = base_pattern.sub(replace_base, content)

        if file.endswith(".yml"):
            new_content = desc_pattern.sub(replace_desc, new_content)

        if new_content != content:
            path.write_text(new_content, encoding="utf-8")
            print("Updated:", path)

print("\nDone ✔")