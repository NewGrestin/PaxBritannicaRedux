from pathlib import Path
import os
import re


# =========================
# CONFIG
# =========================

SCRIPT_DIR = Path(__file__).resolve().parent
MOD_PATH = SCRIPT_DIR.parent

LOCALISATION_PATH = MOD_PATH / "localisation"

TARGET_FILE = "victory_points_l_english.yml"


# =========================
# REGEX
# =========================

# Correct:
#971 - GRAUBÜNDEN

HEADER_PARSE = re.compile(
    r'^#(\d+) - (.+)$'
)

VP_PATTERN = re.compile(
    r'^\s*(VICTORY_POINTS_\d+)\s*:\s*"([^"]+)"'
)


# =========================
# VALIDATION
# =========================

issues = 0


def valid_header(line):

    match = HEADER_PARSE.match(line)

    if not match:
        return False

    state_name = match.group(2)

    # Must be uppercase (Unicode safe)
    if state_name != state_name.upper():
        return False

    return True



def check_region(region_name, entries):

    global issues

    if len(entries) < 2:
        return


    names = [
        name for _, name in entries
    ]


    sorted_names = sorted(
        names,
        key=lambda x: x.casefold()
    )


    if names != sorted_names:

        issues += 1

        print("\n================================")
        print("INCORRECT VICTORY POINT ORDER")
        print(region_name)
        print("================================")

        print("\nCurrent:")
        for name in names:
            print(f"  {name}")


        print("\nExpected:")
        for name in sorted_names:
            print(f"  {name}")



# =========================
# SCAN
# =========================

print("Scanning victory point localisation...\n")


found_file = False


for root, _, files in os.walk(LOCALISATION_PATH):

    if TARGET_FILE not in files:
        continue


    found_file = True

    path = Path(root) / TARGET_FILE


    try:
        lines = path.read_text(
            encoding="utf-8"
        ).splitlines()

    except Exception as e:
        print(
            f"Could not read {path}: {e}"
        )
        continue



    current_region = None
    current_entries = []



    for line_number, line in enumerate(lines, start=1):


        # =====================
        # HEADER CHECK
        # =====================

        if line.startswith("#"):


            if not valid_header(line):

                issues += 1

                print("\n================================")
                print("BAD HEADER FORMAT")
                print("================================")

                print(
                    f"Line {line_number}: {line}"
                )



            # Check previous state

            check_region(
                current_region,
                current_entries
            )


            current_region = line
            current_entries = []

            continue



        # =====================
        # VICTORY POINT CHECK
        # =====================

        vp = VP_PATTERN.match(line)


        if vp:

            current_entries.append(
                (
                    vp.group(1),
                    vp.group(2)
                )
            )



    # Check final state

    check_region(
        current_region,
        current_entries
    )



# =========================
# RESULT
# =========================

if not found_file:

    print(
        "victory_points_l_english.yml not found."
    )


print(
    f"\nDone. Found {issues} issue(s)."
)