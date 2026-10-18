#################################################
#				Country Master - data
#
#	Reads the countries of Revolution Realized: tags, start history, leaders (characters),
#	national ideas, OOBs, colours, names, flags, cores, and the debug collapse / time bomb
#	decisions that release countries. The window is in country_master.py.
#
#	File helpers (TextFile, MapData...) come from ../culture_master/culture_master.py.
#################################################
import os
import re
import sys
import glob
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "culture_master"))
from culture_master import TextFile, strip_comment, RX_LOC, RX_LOC_VALUE  # noqa: E402

D_TAGS = "common/country_tags"
D_HISTORY = "history/countries"
D_STATES = "history/states"
D_UNITS = "history/units"
D_CHARACTERS = "common/characters"
D_IDEAS = "common/ideas"
D_LOC = "localisation/english"
D_DECISIONS = "common/decisions"
D_EVENTS = "events"
D_FOCUS = "common/national_focus"
F_COLORS = "common/countries/colors.txt"
F_COSMETIC = "common/countries/cosmetic.txt"
F_IDEOLOGIES = "common/ideologies/00_ideologies.txt"
F_DEBUG = "common/decisions/debug_decisions.txt"
F_COUNTRY_LOC = "localisation/english/countries_l_english.yml"
MAIN_IDEOLOGIES = ("democratic", "communism", "fascism", "neutrality")

# Debug decision categories: collapses, and the bombs (split by the decision name).
COLLAPSE_CATEGORIES = ("RR_debug_collapse", "RR_debug_collapse_america", "RR_debug_collapse_africa",
					   "RR_debug_collapse_asia", "RR_debug_collapse_oceania")
BOMB_CATEGORY = "rr_debug_time_bombs"
BOMB_KINDS = (("time_bomb_", "Time Bombs"), ("reality_bomb_", "Reality Bombs"), ("mythology_bomb_", "Myth Bombs"),
			  ("myth_bomb_", "Myth Bombs"))


#################################################
#	Paradox script parser
#################################################
class Entry:
	"""One `key = value` (value: a string, or a list of Entry for `{ ... }`). Plain values inside a block are
	Entry(key=None, value=str). first / last: line numbers (0-based) of the entry in its file."""
	__slots__ = ("key", "op", "value", "first", "last")

	def __init__(self, key, op, value, first, last):
		self.key, self.op, self.value, self.first, self.last = key, op, value, first, last

	@property
	def block(self):
		return isinstance(self.value, list)

	def get(self, key, default=None):
		"""The value of the LAST child with this key (later ones win in history files)."""
		if not self.block:
			return default
		hit = [e for e in self.value if e.key == key]
		return hit[-1].value if hit else default

	def all(self, key):
		return [e for e in self.value if e.key == key] if self.block else []

	def values(self):
		"""Plain values in a block (`{ a b c }`)."""
		return [e.value for e in self.value if e.key is None and not isinstance(e.value, list)] if self.block else []

	def __repr__(self):
		return f"Entry({self.key!r}, {'[...]' if self.block else self.value!r}, {self.first}-{self.last})"


RX_TOKEN = re.compile(r'"(?:[^"\\]|\\.)*"|[{}]|>=|<=|!=|[=<>]|[^\s{}=<>"#]+|#[^\n]*|\n')


def parse(text):
	"""Parses Paradox script into a list of Entry. Tolerant: unbalanced braces just end the block."""
	tokens = []
	line = 0
	for m in RX_TOKEN.finditer(text):
		t = m.group(0)
		if t == "\n":
			line += 1
		elif t[0] == "#":
			continue
		else:
			tokens.append((t, line))
	pos = 0

	def block(end_line_default):
		nonlocal pos
		out = []
		while pos < len(tokens):
			t, ln = tokens[pos]
			if t == "}":
				pos += 1
				return out, ln
			if t == "{":  # anonymous block
				pos += 1
				val, last = block(ln)
				out.append(Entry(None, None, val, ln, last))
				continue
			nxt = tokens[pos + 1][0] if pos + 1 < len(tokens) else None
			if nxt in ("=", "<", ">", ">=", "<=", "!="):
				op = nxt
				pos += 2
				if pos >= len(tokens):
					out.append(Entry(t, op, "", ln, ln))
					break
				v, vln = tokens[pos]
				if v == "{":
					pos += 1
					val, last = block(vln)
					out.append(Entry(unquote(t), op, val, ln, last))
				elif v in ("rgb", "hsv", "RGB", "HSV") and pos + 1 < len(tokens) and tokens[pos + 1][0] == "{":
					pos += 2
					val, last = block(vln)
					out.append(Entry(unquote(t), op, val, ln, last))
				else:
					pos += 1
					out.append(Entry(unquote(t), op, unquote(v), ln, vln))
			else:
				pos += 1
				out.append(Entry(None, None, unquote(t), ln, ln))
		return out, end_line_default

	result, _ = block(line)
	return result


def plain(text):
	"""Localisation as the player reads it: no colour codes (§Y...§!), icons (£GFX_...) or written-out new lines."""
	if not text:
		return text
	text = re.sub(r"§[!\w]?", "", text)
	text = re.sub(r"£[\w|]+£?", "", text)
	return re.sub(r"\s+", " ", text.replace("\\n", " ")).strip()


def unquote(s):
	return s[1:-1] if len(s) >= 2 and s[0] == '"' and s[-1] == '"' else s


def walk(entries):
	for e in entries:
		yield e
		if e.block:
			yield from walk(e.value)


def read_text(path):
	raw = open(path, "rb").read()
	if raw.startswith(b"\xef\xbb\xbf"):
		raw = raw[3:]
	return raw.decode("utf-8", errors="replace").replace("\r\n", "\n")


def block_text(lines, entry):
	"""The lines of an entry (as written in the file)."""
	return "\n".join(lines[entry.first:entry.last + 1])


#################################################
#	The data
#################################################
class Country:
	def __init__(self, tag):
		self.tag = tag
		self.country_file = None   # common/countries/... (graphics / colour fallback)
		self.history = None        # history/countries/TAG - Name.txt (relative)
		self.hist = []             # parsed history
		self.rgb = None
		self.characters = []       # character ids recruited in its history
		self.ideas = []            # add_ideas in its history
		self.oob = None
		self.cosmetic = None       # set_cosmetic_tag in its history (its names, flag and colour at start)
		self.states = set()        # owned at game start
		self.cores = set()         # states with add_core_of = TAG in history/states
		self.spawn = []            # how it can appear: ("collapse" / "bomb", decision) ...

	def get(self, key, default=None):
		hit = [e for e in self.hist if e.key == key]
		return hit[-1].value if hit else default


class Character:
	def __init__(self, cid, rel, entry):
		self.id, self.rel, self.entry = cid, rel, entry
		self.name_key = entry.get("name", cid)
		self.roles = [e.key for e in entry.value if e.block and e.key in ROLE_KEYS] if entry.block else []
		port = entry.get("portraits")
		self.portraits = []
		self.portrait_slots = []  # (civilian / army / navy, large / small, sprite or file)
		if isinstance(port, list):
			for p in port:
				if p.block:
					for q in p.value:
						if q.key in ("large", "small") and not q.block:
							self.portraits.append(q.value)
							self.portrait_slots.append((p.key, q.key, q.value))
		# Large first (the one the game shows for the leader); small ones (units, doctrines) after.
		self.portrait_slots.sort(key=lambda x: x[1] != "large")

	def leaders(self):
		"""(ideology, expire, traits) of each country_leader role (some mods give one person a role per ideology)."""
		out = []
		for e in self.entry.value:
			if e.key == "country_leader" and e.block:
				traits = next((t.values() for t in e.value if t.key == "traits"), [])
				out.append((e.get("ideology"), e.get("expire"), traits))
		return out

	def leader(self):
		"""(ideology, expire, traits) of its first country_leader role, or None."""
		roles = self.leaders()
		return roles[0] if roles else None


class SubIdeology:
	"""A type in common/ideologies/00_ideologies.txt (social_conservatism...)."""

	def __init__(self, token, main, entry):
		self.token, self.main, self.entry = token, main, entry
		self.rgb = None
		self.info = ""      # the '#...' note after 'token = {'
		self.section = None  # the ####MAINLINE#### banner above it
		self.rel = F_IDEOLOGIES  # the file it is in


def banner_name(line):
	"""'####MAINLINE####' / '# Democratic #' -> the name; anything else -> None (bars and notes too)."""
	t = line.strip()
	if not t.startswith("#") or not t.endswith("#") or len(t) < 3:
		return None
	name = t.strip("#").strip()
	return name if name and re.search(r"[A-Za-z]", name) else None


ROLE_KEYS = ("country_leader", "field_marshal", "corps_commander", "navy_leader", "advisor", "scientist")


class Idea:
	def __init__(self, name, rel, category, entry):
		self.name, self.rel, self.category, self.entry = name, rel, category, entry
		self.picture = entry.get("picture") if entry.block else None


class Decision:
	"""A debug collapse / bomb decision: what it gives to whom."""

	def __init__(self, name, category, kind, rel, entry):
		self.name, self.category, self.kind, self.rel, self.entry = name, category, kind, rel, entry
		self.key = name           # unique: name, or name#option for a variant
		self.variant = None       # (event id, option name) when its event has several options (collapse types)
		self.siblings = []        # the other variants of the same decision
		self.events = []          # event ids it fires
		self.collapsing = set()   # tags that collapse (collapse_nation_fail / release in its effect)
		self.core_adds = {}       # state -> tag (add_core_of in the decision / its events)
		self.transfers = {}       # state -> tag (transfer_state inside TAG = { })
		self.releases = defaultdict(set)  # releaser -> tags released directly (release = TAG)
		self.tags = set()         # every country it makes / touches
		self.title = None         # an event that makes countries: its title (localisation key)
		self.vague = set()        # tags given states it can't tell (every_state with an unclear limit)


class CountryData:
	"""Reads a mod the way HOI4 does: each file from the mod when it has it, else from the base game, except in
	folders the mod replaces (replace_path in its descriptor.mod). Writes always go into the mod."""

	def __init__(self, root, game=None):
		self.root = root
		self.game = game
		self.warnings = []
		self.replaced = self._read_replace_paths()
		self.load()

	def _read_replace_paths(self):
		out = set()
		for name in ("descriptor.mod",):
			p = os.path.join(self.root, name)
			if os.path.exists(p):
				for m in re.finditer(r'^\s*replace_path\s*=\s*"([^"]+)"', read_text(p), re.M):
					out.add(m.group(1).strip("/").replace("\\", "/"))
		return out

	@property
	def all_mains(self):
		"""The mod's main ideologies and the vanilla four (flag / name endings can use either)."""
		return tuple(dict.fromkeys(self.mains + MAIN_IDEOLOGIES))

	@property
	def mains(self):
		"""The mod's main ideologies in file order (democratic... in vanilla; ni, ds, rc... in other mods)."""
		return tuple(self.ideologies) if getattr(self, "ideologies", None) else MAIN_IDEOLOGIES

	@property
	def dlcs(self):
		"""The base game's DLC folders (dlc/dlc028_la_resistance...): the game reads their gfx / interface /
		portraits like its own files."""
		if not hasattr(self, "_dlcs"):
			self._dlcs = sorted(glob.glob(os.path.join(self.game, "dlc", "*", ""))) if self.game else []
			self._dlcs = [d.rstrip("\\/") for d in self._dlcs]
		return self._dlcs

	@property
	def bases(self):
		"""Where files are looked for, in order: the mod, the base game, its DLC folders."""
		return [self.root] + ([self.game] if self.game else []) + self.dlcs

	def mod_path(self, rel):
		"""Where a file goes in the mod (for writing)."""
		return os.path.join(self.root, rel)

	def in_mod(self, rel):
		return os.path.exists(self.mod_path(rel))

	def path(self, rel):
		"""Where a file is read from: the mod's, else the base game's (unless the mod replaces its folder)."""
		p = self.mod_path(rel)
		if os.path.exists(p) or not self.game:
			return p
		if os.path.dirname(rel).replace("\\", "/") in self.replaced:
			return p
		for base in [self.game] + self.dlcs:
			g = os.path.join(base, rel)
			if os.path.exists(g):
				return g
		return p

	def rel(self, path):
		"""A file's path inside the mod or the base game (the same for both: 'history/countries/AUS - Austria.txt')."""
		full = os.path.normcase(os.path.abspath(path))
		for base in sorted(self.bases, key=len, reverse=True):
			b = os.path.normcase(os.path.abspath(base))
			if full.startswith(b + os.sep):
				return os.path.relpath(os.path.abspath(path), os.path.abspath(base)).replace("\\", "/")
		return path.replace("\\", "/")

	def from_game(self, rel):
		return not self.in_mod(rel) and self.path(rel) != self.mod_path(rel)

	# ---------- loading ----------
	def load(self):
		self._load_tags()
		self._load_loc()
		self._load_colors()
		self._load_history()
		self._load_states()
		self._load_characters()
		self._load_ideas()
		self._load_ideologies()
		self._load_decisions()
		self._load_spawn_mentions()
		self._load_event_spawns()
		self._load_generics()
		self._load_continents()
		self._load_flag_files()
		self._load_cosmetics()
		self._add_released_tags()

	def _files(self, d, pattern="*.txt"):
		"""Every file in a folder (and below): the mod's first, then the base game's that the mod doesn't have
		(same path) or replace (replace_path)."""
		mod = sorted(glob.glob(os.path.join(self.root, d, "**", pattern), recursive=True))
		if not self.game:
			return mod
		have = {self.rel(f).lower() for f in mod}
		out = list(mod)
		for f in [f for base in [self.game] + self.dlcs for f in sorted(glob.glob(os.path.join(base, d, "**", pattern), recursive=True))]:
			r = self.rel(f)
			if r.lower() in have or os.path.dirname(r) in self.replaced:
				continue
			have.add(r.lower())
			out.append(f)
		return out

	def _load_tags(self):
		self.countries = {}
		self.tag_order = []
		for f in self._files(D_TAGS):
			dynamic = False
			for e in parse(read_text(f)):
				if e.key == "dynamic_tags":
					dynamic = True
					continue
				if dynamic or not e.key or e.block or not re.fullmatch(r"[A-Z0-9]{3}", e.key):
					continue
				c = self.countries.setdefault(e.key, Country(e.key))
				c.country_file = "common/" + e.value
				c.tags_file = self.rel(f)
				self.tag_order.append(e.key)

	def _load_loc(self):
		self.loc = {}        # key -> text
		self.loc_where = {}  # key -> (file, line)
		for f in self._files(D_LOC, "*.yml"):
			rel = self.rel(f)
			try:
				text = read_text(f)
			except OSError:
				continue
			for i, line in enumerate(text.split("\n")):
				m = RX_LOC.match(line)
				if m and m.group(1) not in self.loc:
					self.loc[m.group(1)] = m.group(2)
					self.loc_where[m.group(1)] = (rel, i)

	def name_key(self, tag):
		"""The key its names / flags / colour use: its cosmetic tag at start, else the tag."""
		c = self.countries.get(tag)
		return c.cosmetic if c is not None and c.cosmetic else tag

	def label(self, key, default=None):
		"""A localisation key's text for showing (colour codes and icons taken out); default when it has none."""
		return plain(self.loc[key]) if key in self.loc else default

	def name(self, tag, ideology=None, raw=False):
		"""Its name (the cosmetic tag's when it has one, unless raw)."""
		key = tag if raw else self.name_key(tag)
		if key != tag and not any(k in self.loc for k in (key, f"{key}_{ideology}")):
			key = tag  # a cosmetic tag without names: the game shows the tag's
		text = self.loc[f"{key}_{ideology}"] if ideology and f"{key}_{ideology}" in self.loc else self.loc.get(key, tag)
		if "$" in text:  # "$MONARCHY$ Yorkshire": fill in the other localisation key
			text = re.sub(r"\$(\w+)\$", lambda m: self.loc.get(m.group(1), m.group(1).replace("_", " ").title()), text)
		return plain(text) or tag

	def map_rgb(self, tag):
		"""Its map colour: the cosmetic tag's (cosmetic.txt) when it has one with a colour, else its own."""
		c = self.countries.get(tag)
		if c is None:
			return None
		return (self.cosmetic_rgb.get(c.cosmetic) if c.cosmetic else None) or c.rgb

	def _load_colors(self):
		self.cosmetic_entries, self.cosmetic_rgb = {}, {}
		if os.path.exists(self.path(F_COSMETIC)):
			for e in parse(read_text(self.path(F_COSMETIC))):
				if e.key and e.block:
					self.cosmetic_entries[e.key] = e
					col = next((c for c in e.value if c.key == "color" and c.block), None)
					nums = [float(v) for v in col.values() if re.fullmatch(r"-?[\d.]+", v)] if col else []
					if len(nums) >= 3:
						self.cosmetic_rgb[e.key] = tuple(int(min(255, max(0, n))) for n in nums[:3])
		self.colors_entries = {}
		self.bad_colors = {}  # tag -> its numbers when one is outside 0-255 (shown clamped)
		if os.path.exists(self.path(F_COLORS)):
			color_text = read_text(self.path(F_COLORS))
			color_lines = color_text.split("\n")
			for e in parse(color_text):
				if e.key in self.countries and e.block:
					self.colors_entries[e.key] = e
					for c in e.value:
						if c.key == "color" and c.block:
							nums = [float(v) for v in c.values() if re.fullmatch(r"-?[\d.]+", v)]
							if len(nums) >= 3:
								text = color_lines[c.first]
								if re.search(r"\bhsv\b", text, re.I):
									import colorsys
									nums = [x * 255 for x in colorsys.hsv_to_rgb(*[min(1, max(0, n)) for n in nums[:3]])]
								bad = [n for n in nums[:3] if n < 0 or n > 255]
								if bad:
									self.bad_colors[e.key] = nums[:3]
								self.countries[e.key].rgb = tuple(int(min(255, max(0, n))) for n in nums[:3])

	def _load_history(self):
		for f in self._files(D_HISTORY):
			tag = os.path.basename(f)[:3]
			if tag not in self.countries and tag.upper() in self.countries:
				# Windows doesn't care about case: "FLo - Florida.txt" is FLO's history.
				self.warnings.append(f"{self.rel(f)}: written as {tag}, read as {tag.upper()} (rename it to {tag.upper()} - ...)")
				tag = tag.upper()
			c = self.countries.get(tag)
			if c is None:
				c = self.countries[tag] = Country(tag)
				self.warnings.append(f"{self.rel(f)}: {tag} isn't in common/country_tags")
			c.history = self.rel(f)
			try:
				c.hist = parse(read_text(f))
			except Exception as ex:
				self.warnings.append(f"{c.history}: can't read ({ex})")
				continue
			c.characters = [e.value for e in c.hist if e.key == "recruit_character" and not e.block]
			c.ideas = []
			for e in c.hist:
				if e.key == "add_ideas":
					c.ideas += e.values() if e.block else [e.value]
			c.oob = c.get("oob")
			c.cosmetic = c.get("set_cosmetic_tag") or None

	def _load_states(self):
		self.state_owner = {}
		self.state_cores = defaultdict(set)
		self.state_files = {}  # state -> its history file
		self.state_names = {}
		self.state_pop = {}        # state -> manpower (the game's population)
		self.state_provinces = {}
		for f in self._files(D_STATES):
			try:
				top = parse(read_text(f))
			except Exception:
				continue
			for st in top:
				if st.key != "state" or not st.block:
					continue
				sid = st.get("id")
				if not sid or not sid.isdigit():
					continue
				sid = int(sid)
				self.state_names[sid] = st.get("name", str(sid))
				self.state_files[sid] = self.rel(f)
				mp = st.get("manpower")
				if mp and str(mp).isdigit():
					self.state_pop[sid] = int(mp)
				provs = next((e.values() for e in st.value if e.key == "provinces" and e.block), [])
				if provs:
					self.state_provinces[sid] = [int(p) for p in provs if p.isdigit()]
				for e in walk(st.value):
					if e.key == "owner" and not e.block and sid not in self.state_owner:
						self.state_owner[sid] = e.value
					elif e.key == "add_core_of" and not e.block:
						self.state_cores[sid].add(e.value)
		# Names come from localisation (STATE_4 -> Upper Austria); _load_loc runs first.
		self.state_names = {sid: self.loc.get(n, n) for sid, n in self.state_names.items()}
		for sid, tag in self.state_owner.items():
			if tag in self.countries:
				self.countries[tag].states.add(sid)
		for sid, tags in self.state_cores.items():
			for t in tags:
				if t in self.countries:
					self.countries[t].cores.add(sid)

	def _load_characters(self):
		self.characters = {}
		for f in self._files(D_CHARACTERS):
			rel = self.rel(f)
			try:
				top = parse(read_text(f))
			except Exception:
				continue
			for e in top:
				if e.key == "characters" and e.block:
					for ch in e.value:
						if ch.key and ch.block:
							self.characters[ch.key] = Character(ch.key, rel, ch)

	def _load_ideas(self):
		self.ideas = {}
		for f in self._files(D_IDEAS):
			rel = self.rel(f)
			try:
				top = parse(read_text(f))
			except Exception:
				continue
			for e in top:
				if e.key != "ideas" or not e.block:
					continue
				for cat in e.value:
					if not cat.block or not cat.key:
						continue
					for idea in cat.value:
						if idea.key and idea.block and idea.key not in ("designer", "law", "use_list_view"):
							self.ideas.setdefault(idea.key, Idea(idea.key, rel, cat.key, idea))

	def country_ideas(self, tag):
		"""National ideas of a country: the ones it starts with, plus every 'country' idea named TAG_..."""
		c = self.countries[tag]
		out = [i for i in c.ideas if i in self.ideas]
		out += sorted(n for n, i in self.ideas.items() if n.startswith(tag + "_") and n not in out and i.category == "country")
		return out

	def _load_ideologies(self):
		"""Main ideologies and their sub-ideologies (types): colour, the '#' note after the type, and the banner
		section it sits in (####MAINLINE####)."""
		self.ideologies = {}  # main ideology -> [sub types]
		self.subs = {}        # sub type -> SubIdeology
		self.ideo_sections = {}  # main ideology -> [section names in file order]
		self.main_entries = {}   # main ideology -> its Entry (for its types block)
		self.main_rgb = {}       # main ideology -> its colour (color = { } of the ideology itself)
		self.main_rel = {}       # main ideology -> the file it is in
		files = self._files("common/ideologies")
		if not files:
			self.sub_ideology = {}
			return
		for f in files:
			self._load_ideology_file(f)
		self.sub_ideology = {s: m for m, subs in self.ideologies.items() for s in subs}

	def _load_ideology_file(self, f):
		rel = self.rel(f)
		lines = read_text(f).split("\n")
		for e in parse("\n".join(lines)):
			if e.key != "ideologies" or not e.block:
				continue
			for ideo in e.value:
				if not ideo.key or not ideo.block or ideo.key in self.main_entries:
					continue
				self.main_entries[ideo.key] = ideo
				self.main_rel[ideo.key] = rel
				mcol = next((c for c in ideo.value if c.key == "color" and c.block), None)
				if mcol:
					nums = [float(v) for v in mcol.values() if re.fullmatch(r"-?[\d.]+", v)]
					if len(nums) >= 3:
						self.main_rgb[ideo.key] = tuple(int(min(255, max(0, n))) for n in nums[:3])
				types = next((t for t in ideo.value if t.key == "types" and t.block), None)
				self.ideologies[ideo.key] = []
				self.ideo_sections[ideo.key] = []
				if not types:
					continue
				inside = set()
				for t in types.value:
					if t.key and t.block:
						inside.update(range(t.first, t.last + 1))
				section_at = {}
				section = None
				for i in range(types.first + 1, types.last):
					if i in inside:
						section_at[i] = section
						continue
					name = banner_name(lines[i])
					if name:
						section = name
						if name not in self.ideo_sections[ideo.key]:
							self.ideo_sections[ideo.key].append(name)
				for t in types.value:
					if not t.key or not t.block:
						continue
					sub = SubIdeology(t.key, ideo.key, t)
					col = next((c for c in t.value if c.key == "color" and c.block), None)
					if col:
						nums = [float(v) for v in col.values() if re.fullmatch(r"-?[\d.]+", v)]
						if len(nums) >= 3:
							sub.rgb = tuple(int(min(255, max(0, n))) for n in nums[:3])
					head = lines[t.first]
					m = re.search(r"\{\s*#\s*(.*)$", head) or (re.search(r"\}\s*#\s*(.*)$", head) if t.first == t.last else None)
					sub.info = m.group(1).strip() if m else ""
					sub.section = section_at.get(t.first)
					sub.rel = rel
					self.subs[t.key] = sub
					self.ideologies[ideo.key].append(t.key)

	def sub_rgb(self, token):
		"""A sub-ideology's map colour; without one of its own, its ideology's (Communism red...)."""
		st = self.subs.get(token)
		if st is None:
			return None
		return st.rgb or self.main_rgb.get(st.main)

	def leader_for(self, tag, main):
		"""The recruited country leader of a main ideology (democratic...) in a country, or None."""
		for cid in self.countries[tag].characters:
			ch = self.characters.get(cid)
			if ch and self.lead_sub(ch, main):
				return ch
		return None

	def lead_sub(self, ch, main):
		"""The sub-ideology a character leads with under a main ideology (its role for it), or None."""
		return next((r[0] for r in ch.leaders() if self.sub_ideology.get(r[0], r[0]) == main), None)

	def popularity(self, tag, main):
		pops = self.countries[tag].get("set_popularities")
		if isinstance(pops, list):
			v = next((e.value for e in reversed(pops) if e.key == main and not e.block), None)
			try:
				return float(v)
			except (TypeError, ValueError):
				return 0.0
		return 0.0

	# ---------- collapses and bombs ----------
	def _load_decisions(self):
		"""Collapse and 'bomb' decisions: Revolution Realized's debug categories, or in any mod a decision category
		whose name has 'collapse' or 'bomb' in it (only the decisions that make or break up countries are kept)."""
		self.decisions = []
		cats = []
		for f in self._files(D_DECISIONS):
			try:
				text = read_text(f)
			except OSError:
				continue
			low = text.lower()
			if "collapse" not in low and "bomb" not in low:
				continue
			for cat in parse(text):
				if not cat.block or not cat.key:
					continue
				k = cat.key.lower()
				if cat.key in COLLAPSE_CATEGORIES or (cat.key not in (BOMB_CATEGORY,) and "collapse" in k):
					cats.append((cat, "Collapses", self.rel(f), cat.key in COLLAPSE_CATEGORIES))
				elif cat.key == BOMB_CATEGORY or "bomb" in k:
					cats.append((cat, None, self.rel(f), cat.key == BOMB_CATEGORY))
		events = self._event_index([c for c, _, _, _ in cats])
		for cat, kind, rel, known in cats:
			for d in cat.value:
				if not d.key or not d.block:
					continue
				k = kind or next((label for pre, label in BOMB_KINDS if d.key.startswith(pre)), "Other Bombs")
				eff = next((e for e in d.value if e.key == "complete_effect" and e.block), None)
				dec = Decision(d.key, cat.key, k, rel, d)
				if eff:
					self._read_effect(dec, eff.value, None, events)
				# A collapse event with several options (England a / b / c...) is several collapse types: one
				# decision per option, only one of them on at a time.
				multi = next((eid for eid in dec.events if len([o for o in events[eid][1].value if o.key == "option"]) > 1), None)
				if multi is None or not eff:
					self.decisions.append(dec)
					continue
				opts = [o for o in events[multi][1].value if o.key == "option"]
				variants = []
				for i, opt in enumerate(opts):
					v = Decision(d.key, cat.key, k, rel, d)
					oname = opt.get("name") or f"option {i + 1}"
					v.key = f"{d.key}#{i}"
					v.variant = (multi, oname)
					self._read_effect(v, eff.value, None, events, pick={multi: i})
					variants.append(v)
				for v in variants:
					v.siblings = [x for x in variants if x is not v]
				self.decisions += variants
		for dec in self.decisions:
			dec.tags = set(dec.core_adds.values()) | set(dec.transfers.values()) | dec.vague | {
				t for ts in dec.releases.values() for t in ts}
			dec.tags = {t for t in dec.tags if t in self.countries}
		# Categories found by name only keep decisions that do something to countries.
		known = {c.key for c, _, _, kn in cats if kn}
		self.decisions = [x for x in self.decisions if x.category in known or x.tags or x.collapsing or x.releases]

	def _add_released_tags(self):
		"""A collapse also releases countries through cores they already had (collapse_nation_fail): count every
		country that gains states when the decision is on alone."""
		for dec in self.decisions:
			if dec.collapsing or dec.releases:
				own = self.simulate([dec])
				dec.tags |= {t for s, t in own.items() if self.state_owner.get(s) != t and t in self.countries}

	def _event_index(self, cats):
		"""event id -> (file, Entry) for the events these decision categories fire (and the ones those fire)."""
		rx = re.compile(r"\b(?:country_event|news_event)\s*=\s*(?:\{[^{}]*?\bid\s*=\s*)?([\w.]+)")
		wanted = set()
		for cat in cats:
			for x in walk(cat.value):
				if x.key in ("country_event", "news_event"):
					eid = x.get("id") if x.block else x.value
					if eid:
						wanted.add(eid)
		idx = {}
		texts, parsed = {}, {}
		for f in self._files(D_EVENTS):
			try:
				texts[f] = read_text(f)
			except OSError:
				pass
		done = set()
		while wanted - done:
			todo = wanted - done
			done |= todo
			for f, text in texts.items():
				if not any(eid in text for eid in todo):
					continue
				if f not in parsed:
					parsed[f] = parse(text)
				for e in parsed[f]:
					if e.block and e.key in ("country_event", "news_event", "state_event"):
						eid = e.get("id")
						if eid and eid in todo and eid not in idx:
							idx[eid] = (self.rel(f), e)
							for m in rx.finditer("\n".join(texts[f].split("\n")[e.first:e.last + 1])):
								wanted.add(m.group(1))
		return idx

	def _read_effect(self, dec, entries, scope, events, depth=0, pick=None):
		"""Walks an effect: who gets cores / states, who collapses, which events fire (followed once).
		pick: {event id: option index} to follow only that option of an event."""
		if depth > 6:
			return
		pick = pick or {}

		def follow(eid):
			dec.events.append(eid)
			rel, ev = events[eid]
			opts = [o for o in ev.value if o.key == "option" and o.block]
			for o in ev.value:
				if o.key == "immediate" and o.block:
					self._read_effect(dec, o.value, scope, events, depth + 1, pick)
			chosen = [opts[pick[eid]]] if eid in pick and pick[eid] < len(opts) else opts
			for o in chosen:
				self._read_effect(dec, o.value, scope, events, depth + 1, pick)
		for e in entries:
			k = e.key
			if k is None:
				continue
			if e.block:
				if re.fullmatch(r"[A-Z0-9]{3}", k) and k in self.countries:
					self._read_effect(dec, e.value, k, events, depth, pick)
				elif k.isdigit():
					for x in walk(e.value):
						if x.key == "add_core_of" and not x.block:
							dec.core_adds.setdefault(int(k), x.value)
						elif x.key == "transfer_state_to" and not x.block and x.value in self.countries:
							dec.transfers[int(k)] = x.value
				elif k in ("country_event", "news_event"):
					eid = e.get("id")
					if eid and eid in events and eid not in dec.events:
						follow(eid)
				else:
					# every_state / random_state = { limit = { state = 123 / is_core_of = TAG } transfer_state_to = TAG }
					to = [x.value for x in e.value if x.key == "transfer_state_to" and not x.block and x.value in self.countries]
					if to:
						sids = set()
						for lim in e.all("limit"):
							for x in walk(lim.value):
								if x.block:
									continue
								if x.key in ("state", "id") and str(x.value).isdigit():
									sids.add(int(x.value))
								elif x.key == "is_core_of" and x.value in self.countries:
									sids |= {s_ for s_, ts in self.state_cores.items() if x.value in ts}
						for sid in sids:
							dec.transfers[sid] = to[-1]
						if not sids:
							dec.vague.add(to[-1])
					self._read_effect(dec, e.value, scope, events, depth, pick)
			else:
				if k == "country_event" or k == "news_event":
					eid = e.value
					if eid in events and eid not in dec.events:
						follow(eid)
				elif k == "collapse_nation_fail" and scope:
					dec.collapsing.add(scope)
				elif k in ("release", "release_puppet") and e.value in self.countries:
					dec.releases[scope].add(e.value)  # scope None: whoever owns its cores (the event's country)
				elif k == "transfer_state" and scope and e.value.isdigit():
					dec.transfers[int(e.value)] = scope
				elif k == "add_core_of" and e.value in self.countries:
					pass  # inside a state scope, handled above

	def simulate(self, active):
		"""State owners at game start with these decisions done (in order). Collapses work like
		collapse_nation_fail: every country that doesn't exist yet and has a core on a state of the collapsing
		country gets those states. Returns {state: owner}."""
		owner = dict(self.state_owner)
		cores = {s: set(t) for s, t in self.state_cores.items()}
		for dec in active:
			for sid, tag in dec.core_adds.items():
				cores.setdefault(sid, set()).add(tag)
			if dec.kind == "Event" and not (dec.transfers or dec.releases or dec.collapsing):
				# An event that only gives cores (the country is made from them elsewhere): show it with them.
				for sid, tag in dec.core_adds.items():
					owner[sid] = tag
			for sid, tag in dec.transfers.items():
				owner[sid] = tag
			for releaser, tags in dec.releases.items():
				for t in tags:
					for sid, o in list(owner.items()):
						if (o == releaser or (releaser is None and o != t)) and t in cores.get(sid, ()):
							owner[sid] = t
			for c in sorted(dec.collapsing):
				existing = set(owner.values())
				own = [s for s, o in owner.items() if o == c]
				for sid in own:
					# Event cores first (they are what the collapse adds), then old cores.
					# (A neighbour that already exists also takes the states it has a core on.)
					ev = dec.core_adds.get(sid)
					cand = [ev] if ev and ev != c and ev in self.countries else []
					cand += sorted(t for t in cores.get(sid, ()) if t != c and t not in existing and t in self.countries)
					if cand:
						owner[sid] = cand[0]
		return owner

	# ---------- how a tag can appear ----------
	def _load_event_spawns(self):
		"""Events whose effects make countries (release / release_puppet / transfer_state / add_core_of): one
		Decision each (kind 'Event'), or one per option when its options do different things. They can be
		switched on like collapses to see them on the map. The events the collapses / bombs fire are left out."""
		self.event_spawns = []
		used = {eid for x in self.decisions for eid in x.events}
		rx = re.compile(r"\b(?:release|release_puppet|transfer_state|transfer_state_to|add_core_of)\b")
		seen = set()
		for f in self._files(D_EVENTS):
			try:
				text = read_text(f)
			except OSError:
				continue
			if not rx.search(re.sub(r"#[^\n]*", "", text)):
				continue
			rel = self.rel(f)
			try:
				top = parse(text)
			except Exception:
				continue
			for ev in top:
				if not ev.block or ev.key not in ("country_event", "news_event", "state_event"):
					continue
				eid = ev.get("id")
				if not isinstance(eid, str) or eid in used or eid in seen:
					continue
				seen.add(eid)
				# The country it happens to, when its trigger says (tag = ENG / original_tag = ENG).
				root = None
				for trig in ev.all("trigger"):
					root = next((x.value for x in walk(trig.value) if x.key in ("tag", "original_tag") and not x.block
								 and x.value in self.countries), None) or root
				title = ev.get("title")
				title = title if isinstance(title, str) else None
				imm = [x for x in ev.value if x.key == "immediate" and x.block]
				opts = [x for x in ev.value if x.key == "option" and x.block]
				made = []
				for i, opt in enumerate(opts or [None]):
					dec = Decision(eid, None, "Event", rel, ev)
					dec.title = title
					for b in imm:
						self._read_effect(dec, b.value, root, {})
					if opt is not None:
						self._read_effect(dec, opt.value, root, {})
					dec.tags = {t for t in set(dec.core_adds.values()) | set(dec.transfers.values()) | dec.vague
								| {t for ts in dec.releases.values() for t in ts} if t in self.countries}
					if dec.tags:
						name = opt.get("name") if opt is not None else None
						made.append((i, isinstance(name, str) and name or f"option {i + 1}", dec))
				if not made:
					continue
				sig = {(tuple(sorted(x.core_adds.items())), tuple(sorted(x.transfers.items())),
						tuple(sorted((str(k), tuple(sorted(v))) for k, v in x.releases.items()))) for _, _, x in made}
				if len(sig) == 1:  # every option does the same: one entry
					self.event_spawns.append(made[0][2])
					continue
				variants = []
				for i, oname, x in made:
					x.key = f"{eid}#{i}"
					x.variant = (eid, oname)
					variants.append(x)
				for x in variants:
					x.siblings = [y for y in variants if y is not x]
				self.event_spawns += variants


	def _load_spawn_mentions(self):
		"""Tags that script can create: release / release_puppet / transfer_state into them / add_core_of them in
		decisions, events, focuses, scripted effects and on_actions."""
		self.scripted = defaultdict(set)  # tag -> files that can bring it in
		rx = re.compile(r"\b(?:release|release_puppet|release_autonomy|add_core_of|create_dynamic_country|"
						r"transfer_state_to|target)\s*=\s*([A-Z][A-Z0-9]{2})\b")
		rx_scope_transfer = re.compile(r"\b([A-Z][A-Z0-9]{2})\s*=\s*\{\s*transfer_state\b")
		for d in (D_DECISIONS, D_EVENTS, D_FOCUS, "common/scripted_effects", "common/on_actions"):
			for f in self._files(d):
				try:
					text = read_text(f)
				except OSError:
					continue
				text = re.sub(r"#[^\n]*", "", text)
				rel = self.rel(f)
				for m in rx.finditer(text):
					if m.group(1) in self.countries:
						self.scripted[m.group(1)].add(rel)
				for m in rx_scope_transfer.finditer(text):
					if m.group(1) in self.countries:
						self.scripted[m.group(1)].add(rel)

	def categories(self):
		"""[(category, [tags])] for the list on the left."""
		start = sorted({t for t in self.state_owner.values() if t in self.countries})
		by_dec = set()
		for d in self.decisions:
			by_dec |= d.tags
		has_cores = {t for t, c in self.countries.items() if c.cores}
		by_event = set()
		for x in getattr(self, "event_spawns", []):
			by_event |= x.tags
		by_event = sorted(by_event - set(start) - by_dec)
		other = sorted((set(self.scripted) | has_cores) - set(start) - by_dec - set(by_event))
		none = sorted(set(self.countries) - set(start) - by_dec - set(by_event) - set(other))
		return [("On the map at start", start), ("Can spawn by event", by_event), ("Can spawn by script or cores", other),
				("No way to spawn yet", none)]

	def _load_continents(self):
		"""state -> continent (of its first province, from map/definition.csv and map/continent.txt)."""
		self.state_continent_key = {}  # state -> continent key (europe...)
		self.state_continent = {}
		names = []
		cpath = self.file_path("map/continent.txt")
		if os.path.exists(cpath):
			for e in parse(read_text(cpath)):
				if e.key == "continents" and e.block:
					names = e.values()
		prov_cont = {}
		dpath = self.file_path("map/definition.csv")
		if os.path.exists(dpath):
			for line in read_text(dpath).splitlines():
				f = line.split(";")
				if len(f) >= 8 and f[0].isdigit() and f[7].strip().isdigit():
					prov_cont[int(f[0])] = int(f[7])
		for sid, provs in self.state_provinces.items():
			idx = next((prov_cont[p] for p in provs if prov_cont.get(p)), 0)
			if 0 < idx <= len(names):
				key = names[idx - 1]
				self.state_continent[sid] = self.loc.get(key, key.replace("_", " ").title())
				self.state_continent_key[sid] = key

	def continent(self, tag, owner):
		"""A country's continent: its capital's when it owns it, else where most of its states are."""
		c = self.countries[tag]
		cap = c.get("capital")
		if cap and str(cap).isdigit() and owner.get(int(cap)) == tag and int(cap) in self.state_continent:
			return self.state_continent[int(cap)]
		counts = defaultdict(int)
		for sid, t in owner.items():
			if t == tag and sid in self.state_continent:
				counts[self.state_continent[sid]] += 1
		if counts:
			return max(counts, key=counts.get)
		if cap and str(cap).isdigit():
			return self.state_continent.get(int(cap), "")
		return ""

	def _load_flag_files(self):
		"""One listing of gfx/flags (mod first, then the base game): checking files one by one is slow on OneDrive."""
		self.flag_files = set()
		self.flag_map = {}       # lower-case file name -> full path (the mod's when both have it)
		self.flag_stems = set()  # flag names without .tga / the ideology ending, as written
		for base in self.bases:
			d = os.path.join(base, "gfx", "flags")
			if os.path.isdir(d):
				for f in os.listdir(d):
					self.flag_files.add(f.lower())
					self.flag_map.setdefault(f.lower(), os.path.join(d, f))
					if f.lower().endswith(".tga"):
						stem = f[:-4]
						for i in self.all_mains:
							if stem.endswith("_" + i):
								stem = stem[:-len(i) - 1]
								break
						self.flag_stems.add(stem)

	def _load_cosmetics(self):
		"""Every cosmetic tag the mod knows, by country: set_cosmetic_tag anywhere in the script (with the country
		whose scope it is in), cosmetic.txt colours, flags and country-style names (X with X_DEF / X_ADJ or an
		ideology version). Tags are matched by their TAG_ start, script uses also by scope."""
		self.cosmetics = defaultdict(lambda: defaultdict(set))  # tag -> cosmetic -> {where it was found}
		self.cosmetic_files = defaultdict(set)                  # cosmetic -> files that set it
		rx_set = re.compile(r"\bset_cosmetic_tag\s*=\s*([A-Za-z0-9_]+)")
		rx_scope = re.compile(r"\b([A-Z][A-Z0-9]{2})\s*=\s*\{")

		def owner_of(key):
			return key[:3] if len(key) > 4 and key[3] == "_" and key[:3] in self.countries else None

		for top in ("common", "events", "history/countries"):
			for f in self._files(top):
				try:
					text = read_text(f)
				except OSError:
					continue
				if "set_cosmetic_tag" not in text:
					continue
				text = re.sub(r"#[^\n]*", "", text)
				rel = self.rel(f)
				hist_tag = os.path.basename(f)[:3].upper() if rel.startswith(D_HISTORY) else None
				for m in rx_set.finditer(text):
					cos = m.group(1)
					if cos in ("yes", "no"):
						continue
					self.cosmetic_files[cos].add(rel)
					tags = {owner_of(cos)} if owner_of(cos) else {hist_tag}
					if not owner_of(cos):  # no TAG_ start (France_collapse): the country whose block it is in
						scope = [x.group(1) for x in rx_scope.finditer(text, max(0, m.start() - 1500), m.start())
								 if x.group(1) in self.countries]
						if scope:
							tags.add(scope[-1])
					for t in tags - {None}:
						self.cosmetics[t][cos].add("set in script")
		for cos in self.cosmetic_rgb:
			t = owner_of(cos)
			if t:
				self.cosmetics[t][cos].add("colour")
		for stem in self.flag_stems:
			t = owner_of(stem)
			if t:
				self.cosmetics[t][stem].add("flag")
		for k in self.loc:
			if not k.endswith(("_DEF", "_ADJ")):
				continue
			base = k[:-4]
			for i in self.all_mains:
				if base.endswith("_" + i):
					base = base[:-len(i) - 1]
					break
			t = owner_of(base)
			if t and base != t:
				self.cosmetics[t][base].add("name")
		for t, c in self.countries.items():
			if c.cosmetic:
				self.cosmetics[t][c.cosmetic].add("at start")
		self._load_vanilla_cosmetics()

	def _load_vanilla_cosmetics(self):
		"""Cosmetic tags the base game has too (a flag in its gfx/flags, X_DEF / X_ADJ in its English localisation,
		or a colour in its cosmetic.txt), even when the mod has its own copy of them."""
		self.vanilla_cosmetics = set()
		if not self.game:
			return
		known = {c for t in self.cosmetics for c in self.cosmetics[t]}
		lower = {c.lower(): c for c in known}
		suffixes = tuple("_" + i for i in set(MAIN_IDEOLOGIES) | set(self.mains))
		game = set()
		fd = os.path.join(self.game, "gfx", "flags")
		if os.path.isdir(fd):
			for f in os.listdir(fd):
				if f.lower().endswith(".tga"):
					stem = f[:-4]
					game.add(stem.lower())
					for sfx in suffixes:
						if stem.lower().endswith(sfx.lower()):
							game.add(stem[:-len(sfx)].lower())
		rx = re.compile(r"^\s*([A-Za-z0-9_.]+?)_(?:DEF|ADJ):", re.M)
		for f in glob.glob(os.path.join(self.game, "localisation", "**", "*.yml"), recursive=True):
			if "english" not in f.lower():
				continue
			try:
				text = read_text(f)
			except OSError:
				continue
			for m in rx.finditer(text):
				base = m.group(1)
				game.add(base.lower())
				for sfx in suffixes:
					if base.endswith(sfx):
						game.add(base[:-len(sfx)].lower())
		cp = os.path.join(self.game, "common", "countries", "cosmetic.txt")
		if os.path.exists(cp):
			try:
				game |= {e.key.lower() for e in parse(read_text(cp)) if e.key}
			except Exception:
				pass
		self.vanilla_cosmetics = {lower[g] for g in game if g in lower}

	# ---------- generic portraits (portraits/*.txt) ----------
	def _load_generics(self):
		"""Generic portraits: a block per tag / cosmetic tag (ENG = { army = { male = { ... } } }) or per continent
		(continent = { name = europe ... }). Blocks with the same name in several files add up."""
		self.generic_tags = defaultdict(list)    # tag / cosmetic tag -> [(category, detail, sprite)]
		self.generic_conts = defaultdict(list)   # continent -> [(category, detail, sprite)]
		self.generic_files = defaultdict(set)    # tag or 'continent:name' -> files

		def items(entries, path, out):
			for x in entries:
				if not x.block or not x.key or x.key == "name":
					continue
				if x.key in ("male", "female"):
					cat = path[0] if path else "leader"
					detail = " / ".join(path[1:] + [x.key])
					for v in x.values():
						if (cat, detail, v) not in out:
							out.append((cat, detail, v))
				else:
					items(x.value, path + [x.key], out)

		for f in self._files("portraits"):
			try:
				top = parse(read_text(f))
			except Exception:
				continue
			rel = self.rel(f)
			for e in top:
				if not e.block or not e.key or e.key == "default":
					continue
				if e.key == "continent":
					name = e.get("name")
					if not isinstance(name, str):
						continue
					items(e.value, [], self.generic_conts[name])
					self.generic_files["continent:" + name].add(rel)
				else:
					items(e.value, [], self.generic_tags[e.key])
					self.generic_files[e.key].add(rel)

	def generic_source(self, tag):
		"""('own', key) when it (or its cosmetic tag) has a block, ('continent', name) when it uses its capital's
		continent's, ('none', None) when neither has any."""
		for key in (self.name_key(tag), tag):
			if self.generic_tags.get(key):
				return "own", key
		# The continent of its capital (else of most of its states, else of its cores).
		ck = self.state_continent_key
		cap = self.countries[tag].get("capital")
		cont = ck.get(int(cap), "") if cap and str(cap).isdigit() else ""
		for pool in ([s for s, t in self.state_owner.items() if t == tag], list(self.countries[tag].cores)):
			if cont:
				break
			keys = [ck[s] for s in pool if s in ck]
			cont = max(set(keys), key=keys.count) if keys else ""
		if cont and self.generic_conts.get(cont):
			return "continent", cont
		return "none", cont or None

	@staticmethod
	def needs_small(category, sprite):
		"""Army / navy generics are shown on units too: their sprite_small must exist (political, operative and
		scientist ones have no small version)."""
		return category in ("army", "navy") and sprite.startswith("GFX_")

	def generic_missing(self, category, sprite):
		"""(large missing, small missing) for one generic portrait."""
		return not self.portrait_path(sprite), self.needs_small(category, sprite) and not self.portrait_path(sprite + "_small")

	def generics_of(self, tag):
		kind, key = self.generic_source(tag)
		return self.generic_tags[key] if kind == "own" else self.generic_conts[key] if kind == "continent" else []

	def cosmetic_flag(self, key, ideology=None):
		"""Flag file of any tag or cosmetic tag (ideology version first)."""
		names = ([f"{key}_{ideology}.tga"] if ideology else []) + [f"{key}.tga"] + [f"{key}_{i}.tga" for i in self.mains]
		return next((self.flag_map[n.lower()] for n in names if n.lower() in self.flag_map), None)

	def has_flag(self, tag, ideology=None):
		return f"{tag}_{ideology}.tga".lower() in self.flag_files if ideology else f"{tag}.tga".lower() in self.flag_files

	# ---------- files ----------
	def flag_path(self, tag, ideology=None, raw=False):
		"""Its flag (.tga): its cosmetic tag's first (unless raw), the ruling ideology's version first, mod before
		the base game."""
		names = []
		for key in ([] if raw or tag not in self.countries else [self.name_key(tag)]) + [tag]:
			names += ([f"{key}_{ideology}.tga"] if ideology else []) + [f"{key}.tga"] + [f"{key}_{i}.tga" for i in self.mains]
		names = list(dict.fromkeys(names))
		return next((self.flag_map[n.lower()] for n in names if n.lower() in self.flag_map), None)

	def portrait_path(self, value):
		"""A portrait's picture: a GFX_ sprite's texture or a file path; None when it isn't there."""
		if not value:
			return None
		path = self.sprite_texture(value) if value.startswith("GFX_") else self.file_path(value)
		return path if path and os.path.exists(path) else None

	def has_large_portrait(self, ch):
		return any(size == "large" and self.portrait_path(v) for _, size, v in ch.portrait_slots)

	def sprite_texture(self, name):
		"""texturefile of a spriteType (portraits, idea pictures), as a full path, or None."""
		if not hasattr(self, "_sprites"):
			self._sprites = {}
			# Every .gfx under interface/ (subfolders too: interface/portraits/GER_portraits.gfx), the mod's first;
			# other lines may sit between name and texturefile.
			rx = re.compile(r'\bname\s*=\s*"?([\w.\-]+)"?((?:(?!\bname\s*=)[\s\S]){0,400}?)\btexturefile\s*=\s*"([^"]+)"', re.I)
			for f in self._files("interface", "*.gfx"):
				try:
					text = read_text(f)
				except OSError:
					continue
				for m in rx.finditer(text):
					self._sprites.setdefault(m.group(1), m.group(3))
			self._sprites_lower = {}
			for k, v in self._sprites.items():
				self._sprites_lower.setdefault(k.lower(), v)
		tex = self._sprites.get(name) or self._sprites_lower.get(name.lower())  # sprite names ignore case in the game
		if not tex:
			return None
		for base in self.bases:
			p = os.path.join(base, tex)
			if os.path.exists(p):
				return p
		return None

	def file_path(self, rel):
		"""A mod file, or the base game's when the mod doesn't have it."""
		return self.path(rel)

	def new_file(self, kind):
		"""Where new lines of a kind go when the mod has no file of its own for them yet."""
		return {"loc": "localisation/english/country_master_l_english.yml",
				"gfx": "interface/country_master_ideologies.gfx"}[kind]


def find_game(root):
	"""The base game folder (for vanilla flags, portraits and country files)."""
	cands = [os.environ.get("HOI4_GAME", "")]
	for drive in "CDEFG":
		cands += [f"{drive}:/SteamLibrary/steamapps/common/Hearts of Iron IV",
				  f"{drive}:/Program Files (x86)/Steam/steamapps/common/Hearts of Iron IV",
				  f"{drive}:/Steam/steamapps/common/Hearts of Iron IV"]
	for c in cands:
		if c and os.path.isfile(os.path.join(c, "hoi4.exe")):
			return c
	return None
