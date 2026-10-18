# Country Master
Creator - Mike123
The country side of Revolution Realized, next to Culture Master: every tag, what it starts the game with, and how it
can appear. Edits are written into the normal mod files, so they show up in git like hand edits.

## Running it

- Double-click `CountryMaster.exe` (it finds the mod by itself when it sits in `tools/country_master/`). Culture
  Master's menu bar has **▸ Country Master** and this one has **▸ Culture Master** to open the other tool.
- From source: `python country_master.py [mod folder]` (needs `pip install pillow numpy`; it uses
  `../culture_master/culture_master.py` for the map and file code). Rebuild the exe with `build.bat`.
- The map comes from the same cache as Culture Master (`%LOCALAPPDATA%\CultureMaster`).
- Flags, portraits and country files the mod doesn't have are read from the base game
  (`C:\SteamLibrary\steamapps\common\Hearts of Iron IV` and the other usual Steam folders, or set `HOI4_GAME`).

## Any mod

Country Master works on any HOI4 mod, not just Revolution Realized:
- It opens the mod it sits in (a folder above it with `descriptor.mod`), the folder given on the command line, the last
  one opened, or asks for one (File > **Open another mod...**). The base game is found in the usual Steam folders, or
  it asks once (remembered in `%APPDATA%\CountryMaster\config.json`).
- Files are read like the game does: the mod's file when it has one, else the base game's, except in folders the mod
  replaces (`replace_path` in its `descriptor.mod`). A mod without its own map uses the base game's map.
- **Writes only ever go into the mod.** Changing something only the base game has first copies that file into the mod
  (same path, so it overrides the game's, as in the game); the base game folder is never written to. New localisation
  / sprites go to the mod's own file when it has the usual one (`countries_l_english.yml`, `parties_l_english.yml`,
  `rr_ideologies.gfx`), else to `localisation/english/country_master_l_english.yml` /
  `interface/country_master_ideologies.gfx`.
- Collapses / bombs: Revolution Realized's debug categories, or in any mod a decision category whose name has
  "collapse" or "bomb" in it (only decisions that make or break up countries are kept).
- The mod's own main ideologies are used everywhere (Pax Britannica's `ni`, `ds`, `rc`, `cn`, ...), not just the
  vanilla four: names rows, popularities, flags, the View box ("All <ideology name>") and the Sub-ideologies list. All
  files in `common/ideologies` are read; a sub-ideology's note can sit after its `{` or after a one-line `}`. Main
  ideologies without a colour of their own get a fixed colour.
- Characters with a `country_leader` role per ideology are read role by role (the leader of each ideology is found).
- Names in lists and titles are shown without colour codes / icons (`§O...§!`, `£GFX_...`); edit boxes keep them.
- The base game's DLC folders (`dlc/dlc028_la_resistance/...`) are read like the game does, under the base game:
  their sprites, pictures, flags and portrait lists count (generic operatives and such come from there).
- Uncompressed .dds pictures are read with numpy (PIL does those in slow Python): portraits load ~100x faster.
- The first start on a new mod builds its state map (about half a minute); after that it is cached.

## The list on the left

Every tag in `common/country_tags` (not the dynamic D01... ones), with its flag, its states on the map right now and
its **Est. pop** (the `manpower` of those states).

- **Show** picks what the list holds:
  - *All countries*
  - *On the map at start* (owns states in `history/states`)
  - *Collapses* (each debug collapse decision, `RR_debug_collapse*` in `common/decisions/debug_decisions.txt`,
    with the countries it makes)
  - *Time Bombs*, *Reality Bombs*, *Myth Bombs* (the `rr_debug_time_bombs` decisions, split by name)
  - *Can spawn by event* (an event option releases it, transfers states to it or gives it cores; the events the
    collapses / bombs fire are left out, they are under those)
  - *Can spawn by script or cores* (has cores in `history/states`, or a decision / event / focus / scripted effect /
    on_action releases it: `release`, `release_puppet`, `add_core_of`, `transfer_state` into it...)
  - *No way to spawn yet*
  - *Generics type*: every country grouped by where its generic portraits come from: **Has own** (a block of its
    own, or of its cosmetic tag, in `portraits/`), **Shared: Europe / Africa / ...** (none of its own: the game uses
    the continent block of its capital's continent), **No generics**.
- **Gap Finder** narrows it to the countries with a problem (bold amber rows, red count): no leader for every
  ideology (a recruited country leader for democratic, communism, fascism and neutrality), no collapse (on the map at
  start but no collapse decision breaks it up), no flag, a missing ideology flag (and no base flag to fall back on),
  no name, no map colour, a map colour out of range (over 255: PRM has 267), no national ideas, a recruited leader without a *large* portrait (a small one only doesn't count), a recruited character that isn't
  defined anywhere.
- **Sort by** *Name*, *Tag*, *States*, *Est. pop* or *Continent* (its capital's, else where most of its states are);
  ▲/▼ reverses it. The Country, Tag, States and Est. pop headers sort too.
- **Sub-ideologies** groups the countries by ruling party, then by the sub-ideology of the leader the game shows at
  start (social_conservatism, fascism_austrofascist...).

**Collapses and bombs:** click one in the list to **preview** it on the map; double-click it (or right-click) to keep
it **switched on**. Several can be on at once (Tools > Switch off all). States that changed hands are hatched and
country borders are drawn dark, so the new countries show even when their colours are close. A country's own
collapses are also in Overview > Collapses with a Switch on / off button, and in its right-click menu
("Collapse it: ..."). How a collapse is worked out:
- The decision and the events it fires are read: `STATE = { add_core_of = TAG }`, `TAG = { transfer_state = X }`,
  `X = { release = Y }` and `TAG = { collapse_nation_fail = yes }`.
- Like `collapse_nation_fail`, every country that doesn't exist yet and has a core on a state of the collapsing
  country gets that state. The collapse's own new cores go first.
- `if` / `else` branches are all read, so a state that depends on a condition shows its first outcome.

**Collapse types:** some collapse events have several options (England: Devolution / Complete / Anglo-Saxon
Heptarchy, the USSR's parade / stampede of nations...). Each option is its own row under the decision; only one type
of a decision is on at a time. **Collapse all** (button under the list, or Tools) switches on every collapse at once
(the first type of the ones with several); **Switch off all** undoes it. **Fold list / Unfold list** open or close
every row.

## Sub-ideologies layer

**Layer: Sub-ideologies** (top left) lists the types of `common/ideologies/00_ideologies.txt` like the religions in
Culture Master: Democratic / Communist / Nationalist / Autocratic, then (with **Sections** ticked) the banner sections
of the file (`####MAINLINE####`, `SPECIFICS`, `RELIGIOUS`...), then each sub-ideology with its colour, token, how many
countries on the map have it and their Est. pop.
- **Gap Finder**: no icon, no description, no map colour, no name, not used by any country's leader.
- **Sort by** File order (default), Name, Token, Countries, Est. pop (Reverse flips it).
- Clicking a row only changes what the current map mode shows (the mode itself stays):
  - **Sub-ideology** map: an ideology row (Fascism...) colours every country by its leader's sub-ideology for it
    (View becomes All Fascism); a sub-ideology row lights up the countries with it and greys the rest.
  - **Brush strength** map: an ideology row shows its popularity everywhere; a sub-ideology row its popularity
    where the leader for its ideology has it.
- The right side edits it like a religion: **icon** (69x74, `GFX_ideology_<token>` in `interface/rr_ideologies.gfx`,
  `gfx/interface/ideologies/<ideology>_<token>.dds`), **name**, token, **section** (moves its lines under another
  banner), **info** (the `# note` after `token = {`), **quote / quote by / description** (`<token>_desc` in
  `parties_l_english.yml`, written `§Y"quote"§! - by` then the text) and **map colour** (`color = { r g b }` in its
  type). Below it: every country with a leader of it.
- **Banner**: mods like Pax Britannica start descriptions with a picture (`£GFX_..._banner`) and write the quote
  `§Y“quote”§!` / `-§OBy§!` on its own line. The banner is shown (its sprite name can be changed, **Browse...** makes a
  new picture the size and folder of the mod's other banners, with its sprite), the quote goes in Quote / Quote by,
  and saving writes the description back in the mod's own layout (new lines, colours, curly quotes). A new
  description uses the layout of its ideology's other sub-ideologies.
- **Double-click** a sub-ideology (or right-click > **Edit...**, or **Edit in a window...**) edits it in its own window
  (several can be open). **New sub-ideology...** (button; right-click an ideology > *Add a new sub-ideology to X*, or a
  sub-ideology > *Add a new sub-ideology after this*) opens a window: ideology, name, token (numbered ones like
  `NI_VARIANT_15` are continued), section, note and colour (none = the ideology's). It is written after the last one of
  its section in the same style (one line `X = { ... } #NOTE` or a block), its name next to the others' names, and
  then opens in the edit window.

## Ideology view

The **View** box on the map bar picks which leader counts for each country: *On game start* (the ruler) or *All
Democratic / Communism / Fascism / Neutrality* (each country's leader of that ideology, as if it took over). It is
used by the **Ideology** map mode (with All X: which countries have a leader for X), the **Sub-ideology** map mode
(the colour of that leader's sub-ideology), the Sub-ideologies grouping of the country list and the countries
counts of the sub-ideology list.

## The map

Click a state to pick its owner; right-click for its owner, cores, the collapses / bombs that give it away
(switch them on or off from there), **Launch** the events that make a country with it, and **Open the state's file**. Wheel zooms, right / middle drag pans. Map modes:
- **Countries**: owners in their colours. The selected country stays bright and everyone else is dimmed.
- **Cores of the selected**: its cores, bright where it owns them.
- **Ideology**: each owner's ruling party (or, with View: All X, who has a leader for X).
- **Sub-ideology**: the colour of the sub-ideology of each owner's leader (View picks which leader). A
  sub-ideology without a `color` of its own (258 of them) uses its ideology's colour from `00_ideologies.txt`
  (Nationalist brown, Communist red...), so Italy's Classical Fascism shows brown. Clicking a state says which
  leader and sub-ideology it has; on the Sub-ideologies layer it also opens that sub-ideology on the right
  ("Clicked: Kingdom of Italy (ITA) - Benito Mussolini") without changing the map.
- **Brush strength**: the popularity of the sub-ideology / ideology picked in the Sub-ideologies list.
- **Continents**: the continent of each state.

## The country (right side)

The country side starts narrow (drag the divider to widen it). The map never moves or changes mode by itself: right-click an entry (country, collapse / bomb, ideology or
sub-ideology) > **Show on map** to highlight its states and zoom there; do it again (or **Clear Show on map**, also
in the map's right-click menu) to clear it.
Each tab has its own Save button. **Check recent changes** (small button under the list, or File; hover it for
the last one) lists everything saved this session with the time and the files it wrote; double-click one to go
back to that country / sub-ideology. Saving writes immediately; the old file is copied to
`tools/country_master/backups/<time>/` first (there is no undo, use the backup or git).

- **Cosmetic tags**: a country that starts with `set_cosmetic_tag = X` (130 of them, e.g. Ireland as `IRE_ENG`,
  France as `FRA_start`) shows X's name, flag and map colour (`common/countries/cosmetic.txt`) everywhere: the list,
  the title ("Irish Home Rule State (IRE as IRE_ENG)"), the map. When X has no names / flags of its own, the tag's
  are used, like the game does. Overview > **Cosmetic tag** edits it (empty = remove the line). Under the box are
  all of the country's **known cosmetic tags** (1,124 over 447 countries; the ones the base game has too - a vanilla flag, `_DEF`/`_ADJ` name or cosmetic.txt colour - are tinted blue and marked *vanilla*, and **Switch off vanilla cosmetic tags** above the list hides them, remembered between runs; the one in use always shows) with a tick, flag, name and where they were
  found: *flag* (gfx/flags), *name* (X_DEF / X_ADJ / X_<ideology> localisation), *colour* (cosmetic.txt), *set in
  script* (a `set_cosmetic_tag = X` in decisions / events / focuses / effects / history: X starting with TAG_ goes to
  that tag, others to the country whose block they're in) and *at start*. Tick one to start with it, untick it for
  none: the header, names, map colour and flags switch to it straight away ("not saved" until you press Save
  overview, which writes it; name / colour edits go to the tag being shown). While it has one,
  the names, colour and flags in the Overview are X's. Gap Finder: *Cosmetic tag at start* and *Cosmetic tag
  without a name / flag / colour*.
- **Overview** (scrolls; click a section title to fold it, or Fold all / Unfold all): names (`TAG`, `TAG_DEF`, `TAG_ADJ` and the `TAG_<ideology>` versions; new ones go to
  `countries_l_english.yml`), map colour (`common/countries/colors.txt`), its flags (base and each ideology, in a row that scrolls sideways; missing ones are marked), capital,
  stability, war support, research slots, ruling party, elections, popularities, the leader the game shows at
  start, and its **Collapses** (switch them on / off right there). History values change the line that sets them now (the last one: the game applies them in order) or get a
  new line.
- **Leaders**: every character it recruits at start plus every `TAG_` character, with portrait (the large one first; the ▶ arrow on the picture switches to the small one used on units / doctrines and to its other portraits (civilian / army / navy); a leader without a working large portrait is red in the list and in the Gap Finder). Name, leader ideology
  (all sub-ideologies), expire date, leader traits and "recruited at start" have fields; the box below edits the
  whole character (generals' skills, advisor roles, portraits...). **New character...** adds one to
  `common/characters/TAG.txt`, names it and recruits it (its `GFX_` portrait sprite still needs a picture).
- **National ideas**: the ideas it starts with plus every `TAG_` country idea, with picture. Name, description and
  "starts with it" (`add_ideas` in its history) have fields; the box below edits the whole idea. **Add an idea it
  starts with...** takes any idea token.
- **OOB**: which OOB file it uses (`oob = "..."`), how many templates / divisions / ships that file has, and the whole
  file to edit. Most countries share `generic`; **Make its own OOB file** copies it to `history/units/TAG.txt`.
- **History file**: the whole history file.
- **Generics**: its generic portraits (the random ones for generals, admirals, advisors, operatives...): where
  they come from (its own `TAG = { ... }` block and its files, or the shared continent block and how many other
  countries use it), then each group (Army - male, Navy, Political - communism - male...) with every portrait
  large, and for army / navy also its small one (`<sprite>_small`, used on units). Missing pictures are red.
  Pictures load in the background (a continent can have hundreds). Right-click a portrait > **Mark for rework** > *Needs Touchup* /
  *Needs Severe Recorrection* / *Something about it* (or *Not marked*) - see **Rework list** below. Gap Finder: *No generic portraits at all*,
  *No generic portraits of its own (shared)*, *Generic portrait without a picture (large, or small for army /
  navy)*.
- **Rework list**: right-click a generic (Generics tab) or the leader portrait on the Leaders tab (the one shown:
  large, small... switch with the arrow) > **Mark for rework** > one of three categories: *Needs Touchup* (orange),
  *Needs Severe Recorrection* (red), *Something about it* (purple), or *Not marked*. It goes into
  `tools/country_master/portraits_to_rework.txt` (`mod | sprite | category | used by | date`, every mod in one file;
  **Open the rework list** on the Generics tab opens it). Marked portraits get a frame and ⚑ in their category's
  colour; leaders with one get a ⚑ in the Leaders list. Gap Finder: *Portrait marked for rework (any)* and one per
  category list the countries that use a marked generic or leader portrait. (The older `generics_to_rework.txt` is
  read and moved into the new file as *Needs Touchup*.)
- **How it appears**: the **events that can make it** (each option that does something different is its own row,
  with how many states it gives it; double-click or right-click > **Launch** shows it on the map like a collapse,
  again switches it off; right-click also opens the event file), then its states at start, the collapses / bombs
  that make it (with how many states), the ones where it collapses, its cores, and the script files that can bring
  it in. Events are read from their effects: `release` / `release_puppet`, `TAG = { transfer_state = N }`,
  `N = { transfer_state_to = TAG / add_core_of = TAG }`, `every_state = { limit = { state = N / is_core_of = TAG }
  transfer_state_to = TAG }`; the event's country is the `tag = ` in its trigger when it has one. Right-click a
  country in the list > *Events that make it* launches them too.

## Notes

- A history file written with another case (`FLo - Florida.txt`) is read as that tag and listed in
  Tools > Problems found while loading. The tool never makes a second file for a tag that has one.
- Collapse results are a preview of the script, not the game: `if` limits and later events aren't evaluated.
