# CODE THAT REMOVES UNECESSARY ARGUMENTS (cancel_if_invalid = yes, available_if_capitulated = no) AND EMPTY BYPASS BLOCKS
from pathlib import Path
import os
import re

# =========================
# CONFIG
# =========================

MOD_PATH = Path(__file__).resolve().parent.parent

TARGET_FOLDERS = ("common", "events", "history")
EXTENSIONS = (".txt", ".yml")

# =========================
# REMOVE RULES (ROBUST)
# =========================

REMOVE_LINE = re.compile(
    r'^\s*(available_if_capitulated|cancel_if_invalid)\s*=\s*(no|yes)\s*(#.*)?\s*$',
    re.MULTILINE
)

EMPTY_BYPASS = re.compile(
    r'bypass\s*=\s*{\s*}',
    re.IGNORECASE
)

# =========================
# BRACE SAFE FOCUS PARSER
# =========================

def extract_focus_blocks(text: str):
    blocks = []
    i = 0

    while True:
        start = text.find("focus", i)
        if start == -1:
            break

        brace_start = text.find("{", start)
        if brace_start == -1:
            break

        depth = 1
        j = brace_start + 1

        while j < len(text) and depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1

        blocks.append((brace_start, j))
        i = j

    return blocks

# =========================
# CLEAN FUNCTION
# =========================

def clean_focus(block: str) -> str:
    # remove unwanted key-value lines
    block = REMOVE_LINE.sub("", block)

    # remove empty bypass blocks (any formatting)
    block = re.sub(r'bypass\s*=\s*{\s*}', '', block)
    block = re.sub(r'bypass\s*=\s*{\s*\n\s*}', '', block)
    block = re.sub(r'bypass\s*=\s*{\s*\n\s*\n\s*}', '', block)

    return block

# =========================
# APPLY
# =========================

print("Running HOI4 focus cleanup...\n")

for root, _, files in os.walk(MOD_PATH):
    root_path = Path(root)

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

        blocks = extract_focus_blocks(content)

        if not blocks:
            continue

        new_content = content

        for start, end in reversed(blocks):
            block = content[start:end]
            cleaned = clean_focus(block)
            new_content = new_content[:start] + cleaned + new_content[end:]

        if new_content != content:
            path.write_text(new_content, encoding="utf-8")
            print("Updated:", path)

print("\nDone ✔")