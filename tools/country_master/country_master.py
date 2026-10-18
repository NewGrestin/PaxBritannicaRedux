#!/usr/bin/env python3
#################################################
#				Country Master
#
#	The country side of Revolution Realized: every tag, what it starts with (names, colour, flag,
#	capital, politics, popularities, leaders, national ideas, OOB) and how it can appear (on the map at
#	start, debug collapses, time / reality / myth bombs, script or cores, or not at all yet).
#	Collapses and bombs can be switched on to see the countries they make on the map.
#
#	Edits are written straight into the mod files when you press a Save button (old files are copied to
#	tools/country_master/backups/<time>/ first). The data side is in cm_data.py.
#
#	Run from source: python country_master.py [mod folder]. Build the exe with build.bat.
#################################################
import os
import re
import sys
import time
import shutil
import subprocess
import colorsys
import struct
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, simpledialog

import numpy as np
from PIL import Image, ImageTk

import cm_data as cd
from cm_data import CountryData, parse, read_text, MAIN_IDEOLOGIES  # noqa: F401
import json
import glob
from tkinter import filedialog
from culture_master import TextFile, MapData, strip_comment, RX_LOC_VALUE, split_desc, join_desc, fit_icon, Tooltip

APP_NAME = "Country Master"
VERSION = "1.0"
WATER = (40, 62, 92)
NO_STATE = (70, 70, 70)
UNOWNED = (120, 120, 120)
CATEGORY_ORDER = ["On the map at start", "Collapses", "Time Bombs", "Reality Bombs", "Myth Bombs", "Other Bombs",
				  "Can spawn by event", "Can spawn by script or cores", "No way to spawn yet"]
SHOW_ALL = "All countries"
SHOW_GENERICS = "Generics type"
SHOW_OPTIONS = [SHOW_ALL] + CATEGORY_ORDER + [SHOW_GENERICS]
GAP_ALL = "Show everything"
VANILLA_BG = "#dbe7fb"  # cosmetic tags the base game has too
GAP_OPTIONS = {  # Gap Finder: label -> key
	"No leader for every ideology": "leaders",
	"No collapse (on the map at start)": "collapse",
	"No flag": "flag",
	"Missing an ideology flag": "ideo_flag",
	"No name": "name",
	"No map colour": "colour",
	"Map colour out of range (over 255)": "badcolour",
	"Cosmetic tag at start (all of them)": "cosmetic",
	"Cosmetic tag without a name / flag / colour": "cosmetic_gap",
	"No national ideas": "ideas",
	"Leader without a large portrait": "portrait",
	"Not recruited / undefined leaders": "undefined",
	"No generic portraits at all": "generics_none",
	"No generic portraits of its own (shared)": "generics_shared",
	"Generic portrait without a picture (large, or small for army / navy)": "generics_missing",
	"Portrait marked for rework (any)": "rework:",
	"Portrait marked: Needs Touchup": "rework:Needs Touchup",
	"Portrait marked: Needs Severe Recorrection": "rework:Needs Severe Recorrection",
	"Portrait marked: Something about it": "rework:Something about it",
}
SORT_OPTIONS = ["Name", "Tag", "States", "Est. pop", "Continent"]
SUB_SORT_OPTIONS = ["File order", "Name", "Token", "Countries", "Est. pop"]
SUB_GAP_OPTIONS = {"No icon": "icon", "No description": "desc", "No map colour": "colour", "No name": "name",
				   "Not used by any country": "unused"}
VIEW_START = "On game start"

F_PARTIES_LOC = "localisation/english/parties_l_english.yml"
F_IDEO_GFX = "interface/rr_ideologies.gfx"
IDEO_ICON = (69, 74)
IDEOLOGY_COLORS = {"democratic": "#3a6fc4", "communism": "#b02020", "fascism": "#6e5030", "neutrality": "#707070"}


def append_line(tf, line):
	"""Adds a line at the end of a TextFile, before its final empty line (keeps the file ending as it was)."""
	if tf.lines and tf.lines[-1] == "":
		tf.lines.insert(len(tf.lines) - 1, line)
		tf.ends.insert(len(tf.ends) - 1, tf.nl)
	else:
		tf.lines.append(line)
		tf.ends[-1:] = [tf.nl, ""]


def random_hue():
	import random
	return random.random()


def tag_color(tag, rgb):
	if rgb:
		return tuple(int(c) for c in rgb)
	h = (hash(tag) % 360) / 360
	r, g, b = colorsys.hsv_to_rgb(h, 0.45, 0.8)
	return int(r * 255), int(g * 255), int(b * 255)


# A sub-ideology's _desc, as Revolution Realized writes it: §Y"quote"§! - by\n\ntext.
# Other mods (Pax Britannica) start with a banner picture and colour the quote: \n\n£GFX_..._banner\n\n\n\n§Y“quote”§!\n-§OBy§!\n\ntext
DESC_LAYOUT = dict(lead="", banner_post="", gap_banner="\\n\\n", q_open='§Y"', q_close='"§!', gap_by=" ", by_open="- ",
				   by_close="", gap_body="\\n\\n")
RX_DESC_BANNER = re.compile(r'^((?:\\n|\s)*)£([\w.\-]+)((?:\|\d+)?£?)')
RX_DESC_QUOTE2 = re.compile(r'^((?:\\n|\s)*)(§Y\s*[“"]|[“"])(.*?)([”"]\s*§!|[”"])', re.S)
RX_DESC_BY = re.compile(r'^((?:\\n|[ \t])*)(-+[ \t]*|—[ \t]*)(§\w)?(.*?)(§!)?([ \t]*)(?=\\n|$)')
RX_DESC_GAP = re.compile(r'^(?:\\n|\s)*')


def parse_desc(raw):
	"""-> (banner sprite, quote, quote by, text with real new lines, layout). The layout keeps how the mod wraps them
	(new lines, colours, curly quotes) so build_desc writes them back the same way."""
	lay = dict(DESC_LAYOUT)
	rest = raw or ""
	banner = quote = by = ""
	m = RX_DESC_BANNER.match(rest)
	if m:
		lay["lead"], banner, lay["banner_post"] = m.group(1), m.group(2), m.group(3)
		rest = rest[m.end():]
	m = RX_DESC_QUOTE2.match(rest)
	if m:
		lay["gap_banner" if banner else "lead"] = m.group(1)
		lay["q_open"], quote, lay["q_close"] = m.group(2), m.group(3), m.group(4)
		rest = rest[m.end():]
		m = RX_DESC_BY.match(rest)
		if m and m.group(4).strip():
			lay["gap_by"], lay["by_open"], by, lay["by_close"] = m.group(1), m.group(2) + (m.group(3) or ""), m.group(4), (m.group(5) or "") + m.group(6)
			rest = rest[m.end():]
	gap = RX_DESC_GAP.match(rest).group(0)
	if banner or quote:
		if gap and rest[len(gap):]:
			lay["gap_body"] = gap
	elif gap:
		lay["lead"] = gap
	body = rest[len(gap):].replace("\\n", "\n").strip()
	return banner, quote, by.strip(), body, lay


def build_desc(banner, quote, by, body, lay):
	"""The other way round (new lines written as \\n, the way localisation files have them)."""
	if not (banner or quote or body):
		return ""
	out = lay["lead"]
	if banner:
		out += "£" + banner + lay["banner_post"]
	if quote:
		out += (lay["gap_banner"] if banner else "") + lay["q_open"] + quote + lay["q_close"]
		if by:
			out += lay["gap_by"] + lay["by_open"] + by + lay["by_close"]
	if body:
		out += (lay["gap_body"] if banner or quote else "") + body.replace("\r", "").replace("\n", "\\n")
	return out


TOOL_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
REWORK_FILE = os.path.join(TOOL_DIR, "portraits_to_rework.txt")
OLD_REWORK_FILE = os.path.join(TOOL_DIR, "generics_to_rework.txt")  # before leader portraits could be marked
REWORK_CATS = {"Needs Touchup": "#e8890c", "Needs Severe Recorrection": "#c62828", "Something about it": "#7b52c7"}
REWORK_DEFAULT = "Needs Touchup"
REWORK_COLOUR = REWORK_CATS[REWORK_DEFAULT]


def load_rework():
	"""portraits_to_rework.txt -> {mod folder name: {sprite: (category, used by, marked on)}}."""
	out = {}
	path = REWORK_FILE if os.path.exists(REWORK_FILE) else OLD_REWORK_FILE
	try:
		lines = open(path, encoding="utf-8").read().splitlines()
	except OSError:
		return out
	for line in lines:
		if not line.strip() or line.lstrip().startswith("#"):
			continue
		parts = [p.strip() for p in line.split(" | ")]
		if len(parts) < 2:
			continue
		if len(parts) > 2 and parts[2] in REWORK_CATS:  # mod | sprite | category | used by | date
			cat, rest = parts[2], parts[3:]
		else:  # the old generics file: mod | sprite | used by | date
			cat, rest = REWORK_DEFAULT, parts[2:]
		out.setdefault(parts[0], {})[parts[1]] = (cat, rest[0] if rest else "", rest[1] if len(rest) > 1 else "")
	return out


def save_rework(marks):
	lines = ["# Portraits marked for rework in Country Master: generics (Generics tab) and leader portraits (Leaders",
			 "# tab), right-click a portrait. Categories: " + ", ".join(REWORK_CATS) + ".",
			 "# Gap Finder > 'Portrait marked for rework...' lists the countries using them. One per line, any mod:",
			 "# mod folder | sprite | category | used by | marked on"]
	for mod in sorted(marks):
		for sprite in sorted(marks[mod], key=lambda k: (list(REWORK_CATS).index(marks[mod][k][0]), k.lower())):
			cat, used, when = marks[mod][sprite]
			lines.append(f"{mod} | {sprite} | {cat} | {used} | {when}")
	with open(REWORK_FILE, "w", encoding="utf-8", newline="\r\n") as f:
		f.write("\n".join(lines) + "\n")
	if os.path.exists(OLD_REWORK_FILE):
		os.remove(OLD_REWORK_FILE)  # its lines are in the new file now


def fast_dds(path):
	"""Uncompressed .dds (A8R8G8B8, R5G6B5...) read with numpy: PIL decodes those in Python, ~0.15s each.
	None for any other kind (compressed ones PIL does quickly)."""
	try:
		with open(path, "rb") as f:
			data = f.read()
	except OSError:
		return None
	if data[:4] != b"DDS " or len(data) < 128:
		return None
	h, w = struct.unpack_from("<II", data, 12)
	flags, fourcc, bits, rm, gm, bm, am = struct.unpack_from("<I4sIIIII", data, 80)
	bpp = bits // 8
	if not flags & 0x40 or bpp not in (2, 3, 4) or len(data) < 128 + w * h * bpp:  # 0x40: DDPF_RGB
		return None
	raw = np.frombuffer(data, dtype=np.uint8, count=w * h * bpp, offset=128)
	if bpp == 3:
		px = raw.reshape(-1, 3).astype(np.uint32)
		px = px[:, 0] | (px[:, 1] << 8) | (px[:, 2] << 16)
	else:
		px = raw.view("<u4" if bpp == 4 else "<u2").astype(np.uint32)

	def channel(mask, default=255):
		if not mask:
			return np.full(px.shape, default, np.uint8)
		shift = (mask & -mask).bit_length() - 1
		top = mask >> shift
		return (((px & mask) >> shift) * 255 // top).astype(np.uint8)
	a = channel(am) if flags & 0x1 else channel(0)  # 0x1: has alpha
	rgba = np.stack([channel(rm), channel(gm), channel(bm), a], axis=-1).reshape(h, w, 4)
	return Image.fromarray(rgba, "RGBA")


def load_image(path, size):
	try:
		im = (fast_dds(path) if str(path).lower().endswith(".dds") else None) or Image.open(path).convert("RGBA")
		im.thumbnail(size, Image.LANCZOS)
		return im
	except Exception:
		return None


class LayeredMap(MapData):
	"""Culture Master's state map, read like the game: the mod's map / state files, else the base game's."""

	def __init__(self, data, cache_dir, status):
		self.data = data
		has_map = os.path.exists(os.path.join(data.root, "map", "provinces.bmp"))
		self.map_root = data.root if has_map or not data.game else data.game
		super().__init__(data.root, cache_dir, status)

	def _state_files(self):
		return self.data._files(cd.D_STATES)

	def _cache_key(self, root):
		parts = [str(MapData.CACHE_VERSION), self.map_root]
		for rel in ("map/provinces.bmp", "map/definition.csv"):
			st = os.stat(os.path.join(self.map_root, rel))
			parts.append(f"{st.st_size}:{st.st_mtime_ns}")
		files = self._state_files()
		parts.append(str(max((os.stat(f).st_mtime_ns for f in files), default=0)))
		parts.append(str(len(files)))
		return "|".join(parts)

	def _read_state_history(self, root):
		prov_state, land, seen = {}, set(), set()
		for f in self._state_files():
			try:
				text = "\n".join(strip_comment(l) for l in TextFile(f).lines)
			except OSError:
				continue
			m = re.search(r"\bid\s*=\s*(\d+)", text)
			if not m or int(m.group(1)) in seen:
				continue
			sid = int(m.group(1))
			seen.add(sid)
			pm = re.search(r"\bprovinces\s*=\s*\{([^}]*)\}", text)
			if pm:
				for p in pm.group(1).split():
					if p.isdigit():
						prov_state[int(p)] = sid
			om = re.search(r"\bowner\s*=\s*(\w+)", text)
			if om:
				self.owners[sid] = om.group(1)
			mm = re.search(r"\bmanpower\s*=\s*(\d+)", text)
			if mm:
				self.population[sid] = int(mm.group(1))
				self.state_file[sid] = self.data.rel(f)
			if not re.search(r"impassable\s*=\s*yes", text):
				land.add(sid)
		return prov_state, land

	def _build(self, root, prov_state):
		super()._build(self.map_root, prov_state)


class ScrollFrame(ttk.Frame):
	"""A frame that scrolls up / down (mouse wheel over it too). Put widgets in .inner."""

	def __init__(self, parent):
		super().__init__(parent)
		self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
		self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
		self.inner = ttk.Frame(self.canvas)
		self.inner.bind("<Configure>", lambda ev: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
		self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
		self.canvas.bind("<Configure>", lambda ev: self.canvas.itemconfig(self.win, width=ev.width))
		self.canvas.configure(yscrollcommand=self.bar.set)
		self.canvas.pack(side="left", fill="both", expand=True)
		self.bar.pack(side="left", fill="y")
		for w in (self.canvas, self.inner):
			w.bind("<Enter>", lambda ev: self.canvas.bind_all("<MouseWheel>", self._wheel))
			w.bind("<Leave>", lambda ev: self.canvas.unbind_all("<MouseWheel>"))

	def _wheel(self, ev):
		# Over a list / text box that can scroll itself (the cosmetic tags, a description...): that one scrolls, not the page.
		w = ev.widget
		if w is not self.canvas and isinstance(w, (ttk.Treeview, tk.Text, tk.Listbox)):
			top, bottom = w.yview()
			if top > 0 or bottom < 1:
				if not w.bind_class(w.winfo_class(), "<MouseWheel>"):
					w.yview_scroll(-1 if ev.delta > 0 else 1, "units")
				return
		if self.canvas.winfo_height() < self.inner.winfo_reqheight():
			self.canvas.yview_scroll(-1 if ev.delta > 0 else 1, "units")


class SubForm(ttk.Frame):
	"""The sub-ideology form: in the right panel, and in the window that double-click / right-click > Edit opens."""

	def __init__(self, parent, app, window=False):
		super().__init__(parent)
		self.app, self.window = app, window
		self.editing = None
		sc = ScrollFrame(self)
		sc.pack(fill="both", expand=True)
		f = sc.inner
		top = ttk.Frame(f)
		top.pack(fill="x")
		self.icon = tk.Label(top, text="(no icon)", width=10, height=5, relief="groove")
		self.icon.pack(side="left")
		tb = ttk.Frame(top)
		tb.pack(side="left", padx=8, fill="x", expand=True)
		if window:
			self.title = ttk.Label(tb, text="", font=("Segoe UI", 12, "bold"))
			self.title.pack(anchor="w")
		ttk.Button(tb, text=f"Browse icon... ({IDEO_ICON[0]}x{IDEO_ICON[1]})", command=self.pick_icon).pack(anchor="w")
		self.icon_src = None
		self.main_label = ttk.Label(tb, text="", foreground="#555")
		self.main_label.pack(anchor="w", pady=(4, 0))
		g = ttk.Frame(f)
		g.pack(fill="x", pady=6)
		self.vars = {k: tk.StringVar() for k in ("name", "token", "section", "info", "banner", "quote", "quote_by")}
		rows = (("name", "Name:"), ("token", "Token:"), ("section", "Section:"), ("info", "Info (# note):"),
				("quote", "Quote:"), ("quote_by", "Quote by:"), ("banner", "Banner (£):"))
		for r, (k, label) in enumerate(rows):
			ttk.Label(g, text=label).grid(row=r, column=0, sticky="w")
			if k == "section":
				self.section_box = ttk.Combobox(g, textvariable=self.vars[k], width=30)
				self.section_box.grid(row=r, column=1, sticky="we", pady=1)
			elif k == "banner":
				bf = ttk.Frame(g)
				bf.grid(row=r, column=1, sticky="we", pady=1)
				ttk.Entry(bf, textvariable=self.vars[k], width=30).pack(side="left", fill="x", expand=True)
				ttk.Button(bf, text="Browse...", command=self.pick_banner).pack(side="left", padx=(4, 0))
				self.banner_pic = tk.Label(g, text="", relief="flat")
			else:
				e = ttk.Entry(g, textvariable=self.vars[k], width=32, state="readonly" if k == "token" else "normal")
				e.grid(row=r, column=1, sticky="we", pady=1)
		# The banner picture goes on its own row under its name.
		self.banner_pic.grid(row=len(rows), column=1, sticky="w", pady=(0, 4))
		self.banner_src = None
		self.vars["banner"].trace_add("write", lambda *_: self.show_banner())
		r = len(rows) + 1
		ttk.Label(g, text="Map colour:").grid(row=r, column=0, sticky="w")
		cf = ttk.Frame(g)
		cf.grid(row=r, column=1, sticky="w")
		self.swatch = tk.Label(cf, width=8, relief="solid", bg="#808080")
		self.swatch.pack(side="left")
		ttk.Button(cf, text="Pick...", command=self.pick_color).pack(side="left", padx=4)
		self.colour_note = ttk.Label(cf, text="", foreground="#777")
		self.colour_note.pack(side="left")
		r += 1
		ttk.Label(g, text="Description:").grid(row=r, column=0, sticky="nw")
		self.desc = tk.Text(g, width=40, height=10 if window else 8, wrap="word", font=("Segoe UI", 9))
		self.desc.grid(row=r, column=1, sticky="we", pady=2)
		g.columnconfigure(1, weight=1)
		ttk.Label(f, text="Name, banner, quote and description are saved where the mod already has them (`<token>` /\n"
						  "`<token>_desc`, in the mod's own layout). Colour and note go into the sub-ideology's ideologies\n"
						  "file, the icon to GFX_ideology_<token>. Banner: a picture (£GFX_...) at the top of the description.",
				  foreground="#777").pack(anchor="w")
		bf = ttk.Frame(f)
		bf.pack(fill="x", pady=6)
		ttk.Button(bf, text="Save sub-ideology", command=self.save).pack(side="left")
		if window:
			ttk.Button(bf, text="Close", command=self.winfo_toplevel().destroy).pack(side="left", padx=4)
		else:
			ttk.Button(bf, text="Edit in a window...", command=lambda: self.editing and app.edit_sub_window(self.editing)).pack(side="left", padx=4)
			ttk.Button(bf, text="New sub-ideology...", command=lambda: app.new_sub()).pack(side="left", padx=4)
		self.users = ttk.Label(f, text="", foreground="#333", wraplength=430, justify="left")
		self.users.pack(anchor="w", fill="x")

	def show_banner(self):
		d = self.app.data
		name = self.vars["banner"].get().strip()
		path = self.banner_src or (d.sprite_texture(name) if name else None)
		im = load_image(path, (300, 80)) if path else None
		self._banner_photo = ImageTk.PhotoImage(im) if im else None
		if im:
			self.banner_pic.config(image=self._banner_photo, text="")
		else:
			self.banner_pic.config(image="", text="(no picture found for it)" if name else "", foreground="#a00")

	def fill(self, token):
		app, d = self.app, self.app.data
		st = d.subs[token]
		self.editing = token
		if self.window:
			self.title.config(text=f"{d.label(token, token)}  ({token})")
			self.winfo_toplevel().title(f"Sub-ideology - {d.label(token, token)}")
		else:
			app.head_title.config(text=f"{d.label(token, token)}  ({token})")
		self.main_label.config(text=f"Ideology: {d.label(st.main, st.main.title())}")
		banner, quote, by, body, self.layout = parse_desc(d.loc.get(token + "_desc", "").replace('\\"', '"'))
		if not d.loc.get(token + "_desc"):
			# No description yet: write it the way its ideology's others are written (banner, curly quotes...).
			for t in d.ideologies.get(st.main, []):
				other = parse_desc(d.loc.get(t + "_desc", "").replace('\\"', '"'))
				if other[0] or other[1]:
					self.layout = other[4]
					break
		vals = dict(name=d.loc.get(token, ""), token=token, section=st.section or "", info=st.info, banner=banner,
					quote=quote, quote_by=by)
		self.banner_src = None
		for k, v in vals.items():
			self.vars[k].set(v)
		self.section_box.config(values=[""] + d.ideo_sections.get(st.main, []))
		self.desc.delete("1.0", "end")
		self.desc.insert("1.0", body)
		self.loaded = dict(vals, body=body)
		self.new_rgb = None
		self.icon_src = None
		self.swatch.config(bg="#%02x%02x%02x" % (d.sub_rgb(token) or (128, 128, 128)))
		self.colour_note.config(text="" if st.rgb else f"(none of its own: uses {d.label(st.main, st.main)}'s)")
		path = d.sprite_texture(f"GFX_ideology_{token}")
		im = load_image(path, (96, 96)) if path else None
		self._photo = ImageTk.PhotoImage(im) if im else None
		self.icon.config(image=self._photo or "", text="" if im else "(no icon)", width=96 if im else 10, height=96 if im else 5)
		picked = getattr(app, "picked_country", None)
		if picked and d.countries.get(picked):
			lead = d.leader_for(picked, st.main)
			if lead and d.lead_sub(lead, st.main) == token:
				self.main_label.config(text=f"Ideology: {d.label(st.main, st.main.title())}\nClicked: {d.name(picked, app.ruling(picked))} "
											f"({picked}) - {d.label(lead.name_key, lead.id)}")
		users = []
		for tag in sorted(d.countries):
			lead = d.leader_for(tag, st.main)
			if lead and d.lead_sub(lead, st.main) == token:
				users.append(f"{d.name(tag)} ({tag})" + (" - rules at start" if app.ruling(tag) == st.main else ""))
		self.users.config(text=(f"Leaders with it ({len(users)}): " + "; ".join(users[:60]) + (" ..." if len(users) > 60 else ""))
						  if users else "No country has a leader with it.")

	def pick_color(self):
		c = colorchooser.askcolor(color=self.swatch.cget("bg"), parent=self.winfo_toplevel())
		if c and c[0]:
			self.new_rgb = tuple(int(x) for x in c[0])
			self.swatch.config(bg=c[1])

	def _ask_image(self, title):
		p = filedialog.askopenfilename(parent=self.winfo_toplevel(), title=title,
									   filetypes=[("Images", "*.png *.dds *.jpg *.jpeg *.tga *.bmp *.webp"), ("All files", "*.*")])
		if not p:
			return None
		try:
			Image.open(p).load()
		except Exception as ex:
			messagebox.showerror(APP_NAME, f"Can't read that image:\n{ex}", parent=self.winfo_toplevel())
			return None
		return p

	def pick_icon(self):
		p = self._ask_image("Pick an icon")
		if p:
			self.icon_src = p
			self._photo = ImageTk.PhotoImage(fit_icon(p, IDEO_ICON))
			self.icon.config(image=self._photo, text="", width=IDEO_ICON[0], height=IDEO_ICON[1])

	def pick_banner(self):
		p = self._ask_image("Pick a banner picture")
		if p:
			self.banner_src = p
			if not self.vars["banner"].get().strip():
				self.vars["banner"].set(f"GFX_ideology_{self.editing}_banner")
			self.show_banner()

	def save(self):
		t = self.editing
		if not t:
			return
		app, d = self.app, self.app.data
		st = d.subs[t]
		now = {k: v.get().strip() for k, v in self.vars.items()}
		now["body"] = self.desc.get("1.0", "end").strip()
		was = self.loaded
		done = []
		loc_file = app.sub_loc_file(st.main)
		if self.banner_src:
			app.save_banner(now["banner"], self.banner_src, st.main)
			done.append("banner picture")
		if now["name"] != was["name"]:
			app.set_loc_in(t, now["name"], loc_file)
			done.append("name")
		if any(now[k] != was[k] for k in ("banner", "quote", "quote_by", "body")):
			# Quote marks need escaping for the file (curly ones don't).
			text = build_desc(now["banner"], now["quote"].strip('"'), now["quote_by"], now["body"], self.layout).replace('"', '\\"')
			app.set_loc_in(t + "_desc", text, loc_file)
			done.append("description")
		if self.new_rgb or now["info"] != was["info"]:
			app.edit_type_block(t, rgb=self.new_rgb, info=now["info"] if now["info"] != was["info"] else None)
			done.append("colour / note")
		if now["section"] != was["section"]:
			app.move_type_to_section(t, now["section"] or None)
			done.append("section")
		if self.icon_src:
			app.save_sub_icon(t, st.main, self.icon_src)
			done.append("icon")
		app.after_sub_saved(t)
		app.set_status(f"Saved {t}: {', '.join(done)}." if done else "Nothing changed.")


class Section(ttk.Frame):
	"""A titled part of a page that folds away (click its title). Put widgets in .body."""

	def __init__(self, parent, title, open_=True):
		super().__init__(parent)
		self.title, self.open = title, open_
		self.head = tk.Label(self, text="", anchor="w", font=("Segoe UI", 9, "bold"), fg="#1f3f6f", cursor="hand2")
		self.head.pack(fill="x")
		self.head.bind("<Button-1>", lambda ev: self.toggle())
		self.body = ttk.Frame(self, padding=(10, 2, 0, 6))
		self._show()

	def _show(self):
		self.head.config(text=("▾ " if self.open else "▸ ") + self.title)
		if self.open:
			self.body.pack(fill="x")
		else:
			self.body.pack_forget()

	def toggle(self, open_=None):
		self.open = (not self.open) if open_ is None else open_
		self._show()


class HScroll(ttk.Frame):
	"""A row that scrolls sideways (for the flags). Put widgets in .inner (pack side=left)."""

	def __init__(self, parent, height):
		super().__init__(parent)
		self.canvas = tk.Canvas(self, height=height, highlightthickness=0, borderwidth=0)
		self.bar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
		self.inner = ttk.Frame(self.canvas)
		self.inner.bind("<Configure>", lambda ev: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
		self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
		self.canvas.configure(xscrollcommand=self.bar.set)
		self.canvas.pack(fill="x")
		self.bar.pack(fill="x")


class RawEditor(ttk.Frame):
	"""A text box for a block of a mod file, with Save. get_target() -> (file, first, last line) or None."""

	def __init__(self, parent, app, height=14, on_saved=None):
		super().__init__(parent)
		self.app, self.on_saved, self.target = app, on_saved, None
		bar = ttk.Frame(self)
		bar.pack(fill="x")
		self.title = ttk.Label(bar, text="", foreground="#555")
		self.title.pack(side="left")
		ttk.Button(bar, text="Open file", command=self.open_file).pack(side="right")
		self.save_btn = ttk.Button(bar, text="Save text", command=self.save)
		self.save_btn.pack(side="right", padx=4)
		box = ttk.Frame(self)
		box.pack(fill="both", expand=True)
		self.text = tk.Text(box, height=height, wrap="none", font=("Consolas", 9), undo=True)
		ys = ttk.Scrollbar(box, command=self.text.yview)
		xs = ttk.Scrollbar(box, orient="horizontal", command=self.text.xview)
		self.text.config(yscrollcommand=ys.set, xscrollcommand=xs.set)
		self.text.grid(row=0, column=0, sticky="nsew")
		ys.grid(row=0, column=1, sticky="ns")
		xs.grid(row=1, column=0, sticky="ew")
		box.rowconfigure(0, weight=1)
		box.columnconfigure(0, weight=1)

	def show(self, rel, first=None, last=None):
		"""Shows a whole file (first is None) or lines first..last of it."""
		self.target = (rel, first, last) if rel else None
		self.text.delete("1.0", "end")
		if not rel:
			self.title.config(text="(nothing)")
			return
		path = self.app.data.path(rel)
		if not os.path.exists(path):
			self.title.config(text=f"{rel} (not in the mod)")
			return
		lines = TextFile(path).lines
		chunk = lines if first is None else lines[first:last + 1]
		self.text.insert("1.0", "\n".join(chunk))
		self.text.edit_reset()
		self.title.config(text=f"{rel}" + (f"  lines {first + 1}-{last + 1}" if first is not None else ""))

	def get(self):
		return self.text.get("1.0", "end-1c")

	def save(self):
		if not self.target:
			return
		rel, first, last = self.target
		self.app.write_lines(rel, first, last, self.get().split("\n"))
		if self.on_saved:
			self.on_saved()
		self.app.set_status(f"Saved the text of {rel}" + (f" (lines {first + 1}-{last + 1})" if first is not None else "") + ".")

	def open_file(self):
		if self.target:
			self.app.open_path(self.app.data.path(self.target[0]))


class App:
	def __init__(self, root, mod_root):
		self.root = root
		self.mod_root = mod_root
		self.backup_root = os.path.join(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)), "backups")
		root.title(f"{APP_NAME} {VERSION} - {mod_root}")
		root.geometry("1600x950")
		self.status = ttk.Label(root, text="Loading...", anchor="w", relief="sunken")
		self.status.pack(side="bottom", fill="x")
		root.update()
		self.data = CountryData(mod_root, find_game_dir(mod_root))
		cache = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "CultureMaster")
		self.map = LayeredMap(self.data, cache, lambda s: (self.set_status(s), root.update()))
		self.active = []          # decisions switched on (collapses / bombs)
		self.preview = None       # a collapse / bomb clicked in the list (shown until another click)
		self.change_log = []      # (time, what was saved, files, target) - Check recent changes
		self.highlight, self.highlight_key, self.highlight_label = set(), None, ""  # Show on map
		self.selected = None      # tag
		self.selected_state = None
		self.zoom = None
		self.ox = self.oy = 0.0
		self.map_mode = tk.StringVar(value="owner")
		self._flags = {}
		self._render_pending = False
		self._build_ui()
		self.recompute()
		self.rebuild_tree()
		root.after(100, self.fit_map)
		self.set_status(f"{len(self.data.countries)} tags, {len(self.data.characters)} characters, {len(self.data.ideas)} ideas. "
						"Double-click a collapse or bomb to switch it on.")

	# ---------- helpers ----------
	def set_status(self, text):
		"""The status line. After files were written, the message that says what was saved goes in the change log."""
		self.status.config(text=text)
		written = getattr(self, "_written", [])
		if written and text.startswith(("Saved", "Made", "Added")):
			target = ("sub", self.sub_editing) if self.layer.get() == "subs" and getattr(self, "sub_editing", None) \
				else ("tag", self.selected) if self.selected else None
			self.change_log.append((time.strftime("%H:%M:%S"), text, list(written), target))
			self._written = []

	def touched(self, rel):
		"""Remembers a file written for the change log."""
		if not hasattr(self, "_written"):
			self._written = []
		if rel not in self._written:
			self._written.append(rel)

	def last_change_text(self):
		if not self.change_log:
			return "Nothing saved yet this session (Country Master writes to the files when you press a Save button)."
		when, text, files, _ = self.change_log[-1]
		return f"Last change ({when}): {text}\nFiles: " + ", ".join(files)

	def open_path(self, path):
		try:
			os.startfile(path)
		except Exception as ex:
			messagebox.showerror(APP_NAME, f"Can't open {path}:\n{ex}")

	def into_mod(self, rel):
		"""Before a file is changed: a base-game file is copied into the mod first (the mod's copy then overrides
		it, as in the game). Returns the mod path."""
		d = self.data
		dst = d.mod_path(rel)
		if not os.path.exists(dst):
			src = d.path(rel)
			if os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
				os.makedirs(os.path.dirname(dst), exist_ok=True)
				shutil.copy2(src, dst)
				self.set_status(f"Copied {rel} from the base game into the mod to change it.")
		return dst

	def check_in_mod(self, path):
		"""Nothing is ever written outside the mod folder."""
		if not os.path.normcase(os.path.abspath(path)).startswith(os.path.normcase(os.path.abspath(self.data.root)) + os.sep):
			raise RuntimeError(f"Not writing outside the mod: {path}")

	def new_lines_file(self, preferred, kind):
		"""The file new lines go to: the preferred one if the mod has it, else the tool's own file in the mod."""
		d = self.data
		if d.in_mod(preferred):
			return preferred
		rel = d.new_file(kind)
		path = d.mod_path(rel)
		if not os.path.exists(path):
			os.makedirs(os.path.dirname(path), exist_ok=True)
			with open(path, "w", encoding="utf-8-sig", newline="\r\n") as f:
				f.write("l_english:\n" if kind == "loc" else "spriteTypes = {\n}\n")
		return rel

	def backup(self, rel):
		self.touched(rel)
		self.into_mod(rel)
		src = self.data.path(rel)
		if not os.path.exists(src):
			return
		dst = os.path.join(self.backup_root, time.strftime("%Y-%m-%d_%H-%M-%S"), rel)
		if not os.path.exists(dst):
			os.makedirs(os.path.dirname(dst), exist_ok=True)
			shutil.copy2(src, dst)

	def write_lines(self, rel, first, last, new_lines):
		"""Replaces lines first..last (the whole file when first is None) and saves, keeping BOM / line ends."""
		self.backup(rel)
		path = self.data.mod_path(rel)
		self.check_in_mod(path)
		tf = TextFile(path)
		if first is None:
			first, last = 0, len(tf.lines) - 1
		tf.lines[first:last + 1] = new_lines
		tf.ends[first:last + 1] = [tf.nl] * len(new_lines)
		if tf.ends:
			tf.ends[-1] = ""
		tf.save()
		self.reload_file(rel)
		self.status.config(text=f"Saved {rel} (backup in tools/country_master/backups).")

	def reload_file(self, rel):
		"""Re-reads what a saved file holds."""
		d = self.data
		if rel.startswith(cd.D_HISTORY):
			tag = os.path.basename(rel)[:3]
			c = d.countries.get(tag)
			if c:
				c.hist = parse(read_text(d.path(rel)))
				c.characters = [e.value for e in c.hist if e.key == "recruit_character" and not e.block]
				c.ideas = []
				for e in c.hist:
					if e.key == "add_ideas":
						c.ideas += e.values() if e.block else [e.value]
				c.oob = c.get("oob")
				c.cosmetic = c.get("set_cosmetic_tag") or None
		elif rel.startswith(cd.D_CHARACTERS):
			for e in parse(read_text(d.path(rel))):
				if e.key == "characters" and e.block:
					for ch in e.value:
						if ch.key and ch.block:
							d.characters[ch.key] = cd.Character(ch.key, rel, ch)
		elif rel.startswith(cd.D_IDEAS):
			for e in parse(read_text(d.path(rel))):
				if e.key == "ideas" and e.block:
					for cat in e.value:
						if cat.block and cat.key:
							for idea in cat.value:
								if idea.key and idea.block:
									d.ideas[idea.key] = cd.Idea(idea.key, rel, cat.key, idea)
		elif rel.startswith(cd.D_LOC):
			d._load_loc()
		elif rel in (cd.F_COLORS, cd.F_COSMETIC):
			d._load_colors()
			self.recompute()

	def flag(self, tag, size=(24, 16), ideology=None):
		key = (tag, size, ideology)
		if key not in self._flags:
			p = self.data.flag_path(tag, ideology)
			im = load_image(p, size) if p else None
			if im is None:
				im = Image.new("RGBA", size, (90, 90, 90, 255))
			canvas = Image.new("RGBA", size, (0, 0, 0, 0))
			canvas.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
			self._flags[key] = ImageTk.PhotoImage(canvas)
		return self._flags[key]

	def ruling(self, tag):
		c = self.data.countries.get(tag)
		pol = c.get("set_politics") if c else None
		if isinstance(pol, list):
			for e in pol:
				if e.key == "ruling_party":
					return e.value
		return None

	# ---------- UI ----------
	def _build_ui(self):
		menu = tk.Menu(self.root)
		fm = tk.Menu(menu, tearoff=0)
		fm.add_command(label="Open another mod...", command=self.open_other_mod)
		fm.add_command(label="Reload from disk", command=self.reload_all)
		fm.add_command(label="Check recent changes", command=self.show_changes)
		fm.add_command(label="Open Culture Master", command=self.open_culture_master)
		fm.add_separator()
		fm.add_command(label="Quit", command=self.root.destroy)
		menu.add_cascade(label="File", menu=fm)
		tm = tk.Menu(menu, tearoff=0)
		tm.add_command(label="Collapse all (every collapse on)", command=self.collapse_all)
		tm.add_command(label="Switch off all collapses / bombs", command=self.clear_active)
		tm.add_command(label="Problems found while loading...", command=self.show_warnings)
		menu.add_cascade(label="Tools", menu=tm)
		menu.add_command(label="  ▸ Culture Master", command=self.open_culture_master)
		self.root.config(menu=menu)

		pw = self.pw = ttk.PanedWindow(self.root, orient="horizontal")
		pw.pack(fill="both", expand=True)

		# Left: tags by how they appear (or the sub-ideologies).
		left = ttk.Frame(pw, padding=4)
		lf = ttk.Frame(left)
		lf.pack(fill="x", pady=(0, 4))
		ttk.Label(lf, text="Layer:").pack(side="left")
		self.layer = tk.StringVar(value="countries")
		for key, label in (("countries", "Countries"), ("subs", "Sub-ideologies")):
			ttk.Radiobutton(lf, text=label, value=key, variable=self.layer, command=self.switch_layer).pack(side="left", padx=4)
		sf = ttk.Frame(left)
		sf.pack(fill="x")
		ttk.Label(sf, text="Search:").pack(side="left")
		self.search_var = tk.StringVar()
		ttk.Entry(sf, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=4)
		self.search_var.trace_add("write", lambda *a: self._schedule_tree())
		self._tree_job = None
		grid = self.country_controls = ttk.Frame(left)
		grid.pack(fill="x", pady=(4, 0))
		ttk.Label(grid, text="Show:").grid(row=0, column=0, sticky="w")
		self.show_var = tk.StringVar(value=SHOW_ALL)
		box = ttk.Combobox(grid, textvariable=self.show_var, values=SHOW_OPTIONS, state="readonly", width=30)
		box.grid(row=0, column=1, sticky="w", padx=4, pady=1)
		box.bind("<<ComboboxSelected>>", lambda ev: self.rebuild_tree())
		self.show_count = ttk.Label(grid, text="", foreground="#555")
		self.show_count.grid(row=0, column=2, sticky="w")
		ttk.Label(grid, text="Gap Finder:").grid(row=1, column=0, sticky="w")
		self.gap_var = tk.StringVar(value=GAP_ALL)
		box = ttk.Combobox(grid, textvariable=self.gap_var, values=[GAP_ALL] + list(GAP_OPTIONS), state="readonly", width=30)
		box.grid(row=1, column=1, sticky="w", padx=4, pady=1)
		box.bind("<<ComboboxSelected>>", lambda ev: self.rebuild_tree())
		self.gap_count = tk.Label(grid, text="", fg="#ffffff", bg="#c0392b", font=("Segoe UI", 9, "bold"), padx=6)
		ttk.Label(grid, text="Sort by:").grid(row=2, column=0, sticky="w")
		sortf = ttk.Frame(grid)
		sortf.grid(row=2, column=1, columnspan=2, sticky="w", padx=4, pady=1)
		self.sort_var = tk.StringVar(value="Name")
		box = ttk.Combobox(sortf, textvariable=self.sort_var, values=SORT_OPTIONS, state="readonly", width=12)
		box.pack(side="left")
		box.bind("<<ComboboxSelected>>", lambda ev: self.set_sort(self.sort_var.get()))
		self.sort_reverse = False
		self.sort_dir = ttk.Button(sortf, text="▲", width=3, command=lambda: self.set_sort(self.sort_var.get(), flip=True))
		self.sort_dir.pack(side="left", padx=2)
		self.subideo_var = tk.BooleanVar(value=False)
		ttk.Checkbutton(sortf, text="Sub-ideologies", variable=self.subideo_var, command=self.rebuild_tree).pack(side="left", padx=6)
		self._build_sub_controls(left)
		tf = ttk.Frame(left)
		tf.pack(fill="both", expand=True, pady=4)
		self.tree = ttk.Treeview(tf, columns=("tag", "states", "pop"), selectmode="browse")
		self.tree.heading("#0", text="Country", command=lambda: self.set_sort("Name", flip=self.sort_var.get() == "Name"))
		self.tree.heading("tag", text="Tag", command=lambda: self.set_sort("Tag", flip=self.sort_var.get() == "Tag"))
		self.tree.heading("states", text="States", command=lambda: self.set_sort("States", flip=self.sort_var.get() == "States"))
		self.tree.heading("pop", text="Est. pop", command=lambda: self.set_sort("Est. pop", flip=self.sort_var.get() == "Est. pop"))
		self.tree.column("#0", width=220)
		self.tree.column("tag", width=42, anchor="center")
		self.tree.column("states", width=44, anchor="e")
		self.tree.column("pop", width=58, anchor="e")
		self.tree.tag_configure("gap", background="#ffd27a", foreground="#3d2600", font=("Segoe UI", 9, "bold"))
		self.tree.tag_configure("section", foreground="#1f3f6f", font=("Segoe UI", 9, "bold italic"))
		ys = ttk.Scrollbar(tf, command=self.tree.yview)
		self.tree.config(yscrollcommand=ys.set)
		self.tree.pack(side="left", fill="both", expand=True)
		ys.pack(side="left", fill="y")
		self.tree.tag_configure("category", font=("Segoe UI", 9, "bold"))
		self.tree.tag_configure("decision", foreground="#5a3d00")
		self.tree.tag_configure("active", background="#c9f0c0", font=("Segoe UI", 9, "bold"))
		self.tree.tag_configure("nospawn", foreground="#999")
		self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
		self.tree.bind("<Double-1>", self.on_tree_double)
		self.tree.bind("<Button-3>", self.on_tree_menu)
		lb = ttk.Frame(left)
		lb.pack(fill="x")
		ttk.Button(lb, text="Collapse all", command=self.collapse_all).pack(side="left")
		style = ttk.Style()
		style.configure("Small.TButton", font=("Segoe UI", 7), padding=(2, 0))
		rc = ttk.Button(left, text="Check recent changes", style="Small.TButton", command=self.show_changes)
		rc.pack(side="bottom", fill="x", pady=(2, 0))
		Tooltip(rc, self.last_change_text)
		ttk.Button(lb, text="Switch off all", command=self.clear_active).pack(side="left", padx=4)
		ttk.Button(lb, text="Fold list", command=lambda: [self.tree.item(i, open=False) for i in self._all_items()]).pack(side="right")
		ttk.Button(lb, text="Unfold list", command=lambda: [self.tree.item(i, open=True) for i in self._all_items()]).pack(side="right", padx=4)
		self.left_hint = ttk.Label(left, text="Click a collapse / bomb to preview it on the map; double-click (or right-click) to keep\n"
											  "it switched on. 'Collapse all' switches on every collapse.", foreground="#666")
		self.left_hint.pack(anchor="w")
		pw.add(left, weight=0)

		# Centre: map.
		centre = ttk.Frame(pw)
		mb = ttk.Frame(centre)
		mb.pack(fill="x")
		ttk.Label(mb, text="Map:").pack(side="left", padx=(4, 2))
		for key, label in (("owner", "Countries"), ("cores", "Cores"), ("ideology", "Ideology"), ("subideology", "Sub-ideology"),
						   ("strength", "Brush strength"), ("continent", "Continents")):
			ttk.Radiobutton(mb, text=label, value=key, variable=self.map_mode, command=self.rebuild_lut).pack(side="left", padx=2)
		ttk.Label(mb, text="  View:").pack(side="left")
		self.view_var = tk.StringVar(value=VIEW_START)
		self.view_mains = {self.view_label(m): m for m in self.data.mains}
		vb = ttk.Combobox(mb, textvariable=self.view_var, values=[VIEW_START] + list(self.view_mains), state="readonly", width=18)
		vb.pack(side="left")
		vb.bind("<<ComboboxSelected>>", lambda ev: self.on_view_change())
		self.active_label = ttk.Label(mb, text="", foreground="#2a6a2a")
		self.active_label.pack(side="left", padx=10)
		self.canvas = tk.Canvas(centre, bg="#1d2633", highlightthickness=0, cursor="crosshair")
		self.canvas.pack(fill="both", expand=True)
		self.canvas_img = self.canvas.create_image(0, 0, anchor="nw")
		c = self.canvas
		c.bind("<Configure>", lambda ev: self.schedule_render())
		c.bind("<MouseWheel>", self.on_wheel)
		c.bind("<ButtonPress-1>", self.on_click)
		for b in ("<ButtonPress-2>", "<ButtonPress-3>"):
			c.bind(b, self.on_pan_start)
		for b in ("<B2-Motion>", "<B3-Motion>"):
			c.bind(b, self.on_pan)
		c.bind("<ButtonRelease-3>", self.on_right_release)
		c.bind("<Motion>", self.on_motion)
		self.pan_start = None
		pw.add(centre, weight=1)

		# Right: the selected country.
		right = ttk.Frame(pw, padding=6)
		head = ttk.Frame(right)
		head.pack(fill="x")
		self.head_flag = tk.Label(head)
		self.head_flag.pack(side="left")
		self.head_title = ttk.Label(head, text="Pick a country", font=("Segoe UI", 12, "bold"))
		self.head_title.pack(side="left", padx=8)
		self.head_info = ttk.Label(right, text="", foreground="#555", wraplength=430, justify="left")
		self.head_info.pack(fill="x", pady=(2, 4))
		self.tabs = ttk.Notebook(right)
		self.tabs.pack(fill="both", expand=True)
		self._build_overview()
		self.rework = load_rework()
		self._gen_cells = {}
		self._build_leaders()
		self._build_generics()
		self._build_ideas()
		self._build_oob()
		self._build_history()
		self._build_spawn()
		self.right = right
		self._build_sub_panel(right)
		pw.add(right, weight=0)

	# ---------- the list ----------
	def _schedule_tree(self):
		if self._tree_job:
			self.root.after_cancel(self._tree_job)
		self._tree_job = self.root.after(250, self.rebuild_tree)

	def set_sort(self, key, flip=False):
		self.sort_reverse = (not self.sort_reverse) if flip else False
		self.sort_var.set(key)
		numeric = key in ("States", "Est. pop")
		self.sort_dir.config(text="▼" if numeric != self.sort_reverse else "▲")
		self.rebuild_tree()

	def tag_pop(self, tag):
		return self.pops.get(tag, 0)

	def ordered_tags(self, tags):
		d = self.data
		key = self.sort_var.get()
		name = lambda t: d.name(t, self.ruling(t)).lower()
		if key == "Tag":
			k = lambda t: t
		elif key == "States":
			k = lambda t: (-self.counts.get(t, 0), name(t))
		elif key == "Est. pop":
			k = lambda t: (-self.tag_pop(t), name(t))
		elif key == "Continent":
			k = lambda t: (d.continent(t, self.owner) or "~", name(t))
		else:
			k = name
		return sorted(tags, key=k, reverse=self.sort_reverse)

	def gap_test(self):
		"""Gap Finder: a function tag -> True when it has that gap, or None."""
		key = GAP_OPTIONS.get(self.gap_var.get())
		d = self.data
		if key is None:
			return None
		if key == "leaders":
			def test(t):
				have = set()
				for cid in d.countries[t].characters:
					ch = d.characters.get(cid)
					for lead in (ch.leaders() if ch else []):
						have.add(d.sub_ideology.get(lead[0], lead[0]))
				return not set(self.data.mains) <= have
			return test
		if key == "collapse":
			collapsing = {t for x in d.decisions for t in x.collapsing} | {t for x in d.decisions for t in x.releases}
			start = set(d.state_owner.values())
			return lambda t: t in start and t not in collapsing
		if key == "flag":
			return lambda t: not d.has_flag(t) and not any(d.has_flag(t, i) for i in self.data.mains)
		if key == "ideo_flag":
			return lambda t: not d.has_flag(t) and not all(d.has_flag(t, i) for i in self.data.mains)
		if key == "name":
			return lambda t: t not in d.loc
		if key == "colour":
			return lambda t: d.countries[t].rgb is None
		if key == "badcolour":
			return lambda t: t in d.bad_colors
		if key == "cosmetic":
			return lambda t: bool(d.countries[t].cosmetic)
		if key == "cosmetic_gap":
			def test(t):
				cos = d.countries[t].cosmetic
				if not cos:
					return False
				named = any(k in d.loc for k in [cos] + [f"{cos}_{i}" for i in self.data.mains])
				flagged = d.has_flag(cos) or any(d.has_flag(cos, i) for i in self.data.mains)
				return not named or not flagged or cos not in d.cosmetic_rgb
			return test
		if key == "ideas":
			return lambda t: not d.country_ideas(t)
		if key == "portrait":
			def test(t):
				for cid in d.countries[t].characters:
					ch = d.characters.get(cid)
					if ch and not d.has_large_portrait(ch):  # the small one (units, doctrines) doesn't count
						return True
				return False
			return test
		if key == "generics_none":
			return lambda t: d.generic_source(t)[0] == "none"
		if key == "generics_shared":
			return lambda t: d.generic_source(t)[0] != "own"
		if key.startswith("rework:"):
			cat = key.split(":", 1)[1]
			marked = {sp for sp, m in self.rework_marks().items() if not cat or m[0] == cat}

			def test(t):
				if any(sp in marked for _, _, sp in d.generics_of(t)):
					return True
				return any(v in marked for cid in d.countries[t].characters if cid in d.characters
						   for _, _, v in d.characters[cid].portrait_slots)
			return test
		if key == "generics_missing":
			return lambda t: any(any(d.generic_missing(cat, sp)) for cat, _, sp in d.generics_of(t))
		if key == "undefined":
			return lambda t: any(cid not in d.characters for cid in d.countries[t].characters)
		return None

	def main_color(self, main):
		"""An ideology's colour from 00_ideologies.txt (the fixed ones only if the file has none)."""
		rgb = self.data.main_rgb.get(main)
		if rgb:
			return rgb
		if main in IDEOLOGY_COLORS:
			hx = IDEOLOGY_COLORS[main]
			return tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))
		return tag_color(str(main), None)

	def view_main(self, tag):
		"""The main ideology the Ideology view uses for a country: its ruling party, or the one picked (All X)."""
		v = self.view_var.get() if hasattr(self, "view_var") else VIEW_START
		return self.ruling(tag) if v == VIEW_START else self.view_mains.get(v)

	def view_label(self, main):
		"""'All Democratic' / 'All Nationalist' (the ideology's name from localisation)."""
		return f"All {self.data.label(main, main.replace('_', ' ').title())}"

	def sub_ideology_of(self, tag):
		"""(main ideology, the sub-ideology of its leader) in the Ideology view (on game start: the ruler)."""
		main = self.view_main(tag)
		lead = self.data.leader_for(tag, main) if main else None
		return main or "(no ruling party)", (self.data.lead_sub(lead, main) if lead else "(no leader for it)")

	def on_view_change(self):
		self.rebuild_lut()
		self.rebuild_tree()
		self.set_status(f"Ideology view: {self.view_var.get()} - the Ideology and Sub-ideology map modes, the Sub-ideologies "
						"grouping and the sub-ideology counts use " + ("each country's ruler at game start." if self.view_var.get() == VIEW_START
																	 else f"each country's {self.view_main('GER') or ''} leader."))

	def rebuild_tree(self):
		self._tree_job = None
		if getattr(self, "layer", None) is not None and self.layer.get() == "subs":
			return self.rebuild_sub_tree()
		d = self.data
		q = self.search_var.get().strip().lower()
		open_items = {i for i in self._all_items() if self.tree.item(i, "open")}
		sel = self.tree.selection()
		self.tree.delete(*self.tree.get_children())
		counts = self.counts
		gap = self.gap_test()
		found = 0
		show = self.show_var.get()

		def match(tag):
			return not q or q in tag.lower() or q in d.name(tag).lower() or q in d.name(tag, self.ruling(tag)).lower()

		def short(n):
			return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e4 else (str(n) if n else "")

		def add_tag(parent, tag, prefix):
			nonlocal found
			hit = gap is not None
			found += hit
			self.tree.insert(parent, "end", iid=f"{prefix}|{tag}", text=" " + d.name(tag, self.ruling(tag)),
							 values=(tag, counts.get(tag, ""), short(self.tag_pop(tag))), image=self.flag(tag),
							 tags=("gap",) if hit else ())

		def wanted(tags):
			return [t for t in tags if match(t) and (gap is None or gap(t))]

		def add_list(parent, tags, prefix):
			tags = wanted(tags)
			if not self.subideo_var.get():
				for t in self.ordered_tags(tags):
					add_tag(parent, t, prefix)
				return
			groups = {}
			for t in tags:
				main, sub = self.sub_ideology_of(t)
				groups.setdefault(main, {}).setdefault(sub, []).append(t)
			mains = sorted(groups, key=lambda m: (m not in self.data.mains, self.data.mains.index(m) if m in self.data.mains else 0, m))
			for main in mains:
				miid = f"ideo:{prefix}:{main}"
				n = sum(len(v) for v in groups[main].values())
				self.tree.insert(parent, "end", iid=miid, text=f"{main.title()} ({n})", open=miid in open_items or bool(q) or gap is not None,
								 tags=("section",))
				for sub in sorted(groups[main], key=lambda s: (-len(groups[main][s]), s)):
					siid = f"sub:{prefix}:{main}:{sub}"
					self.tree.insert(miid, "end", iid=siid, text=f"{sub} ({len(groups[main][sub])})",
									 open=siid in open_items or bool(q) or gap is not None, tags=("section",))
					for t in self.ordered_tags(groups[main][sub]):
						add_tag(siid, t, prefix)

		cats = dict(d.categories())
		if show == SHOW_ALL:
			add_list("", list(d.countries), "all")
			total = len(d.countries)
		elif show in cats:
			add_list("", cats[show], show)
			total = len(cats[show])
		elif show == SHOW_GENERICS:
			groups = {}
			for t in d.countries:
				kind, key = d.generic_source(t)
				g = "Has own" if kind == "own" else f"Shared: {d.label(key, key.replace('_', ' ').title())}" if kind == "continent" \
					else "No generics" + (f" ({d.label(key, key)} has none)" if key else "")
				groups.setdefault(g, []).append(t)
			total = len(d.countries)
			order = sorted(groups, key=lambda g: (not g.startswith("Has own"), g.startswith("No generics"), g))
			for g in order:
				tags = wanted(groups[g])
				if not tags and (q or gap is not None):
					continue
				giid = f"gen:{g}"
				self.tree.insert("", "end", iid=giid, text=f"{g} ({len(tags)})", tags=("section",),
								 open=giid in open_items or bool(q) or gap is not None)
				for t in self.ordered_tags(tags):
					add_tag(giid, t, "gen-" + g)
		else:
			decs = [x for x in d.decisions if x.kind == show]
			total = len(decs)
			for dec in decs:
				tags = wanted(dec.tags)
				if (q or gap) and not tags and not (q and q in self.dec_label(dec).lower() + dec.name.lower()):
					continue
				on = dec in self.active
				did = f"dec:{dec.key}"
				parent = ""
				if dec.siblings:
					# A collapse with several types: one row for the decision, one per type under it.
					gid = f"decgrp:{dec.name}"
					if not self.tree.exists(gid):
						on_any = any(x in self.active for x in [dec] + dec.siblings)
						self.tree.insert("", "end", iid=gid, text=self.dec_label(dec, base=True) + f"  ({len(dec.siblings) + 1} types)",
										 values=("", "", ""), open=gid in open_items or bool(q) or gap is not None or on_any,
										 tags=("decision",))
					parent = gid
				label = self.dec_label(dec, type_only=bool(dec.siblings))
				self.tree.insert(parent, "end", iid=did, text=("☑ " if on else "☐ ") + label, values=("", len(dec.tags), ""),
								 open=did in open_items or bool(q) or gap is not None, tags=("active",) if on else ("decision",))
				for t in self.ordered_tags(tags):
					add_tag(did, t, dec.key)
		self.show_count.config(text=f"{total}")
		if gap is None:
			self.gap_count.grid_remove()
		else:
			self.gap_count.config(text=f"{found} found")
			self.gap_count.grid(row=1, column=2, sticky="w")
		for i in sel:
			if self.tree.exists(i):
				self.tree.selection_set(i)
				self.tree.see(i)

	def _all_items(self, parent=""):
		for i in self.tree.get_children(parent):
			yield i
			yield from self._all_items(i)

	def row_tag(self, iid):
		if "|" in iid and not iid.startswith(("dec:", "ideo:", "sub:", "decgrp:")):
			return iid.rsplit("|", 1)[1]
		return None

	def row_decision(self, iid):
		if iid.startswith("dec:"):
			key = iid[4:]
			return next((x for x in self.data.decisions if x.key == key), None)
		return None

	def dec_label(self, dec, base=False, type_only=False):
		"""'Austrian Collapse Debug', or for a collapse type 'British Collapse Debug - Devolution Collapse'."""
		d = self.data
		name = d.label(dec.name, dec.name.replace("_", " "))
		if dec.kind == "Event":
			name = f"Event {dec.name}" + (f" \"{d.label(dec.title)}\"" if dec.title and d.label(dec.title) else "")
		if base or not dec.variant:
			return name
		typ = d.label(dec.variant[1], dec.variant[1])
		return typ if type_only else f"{name} - {typ}"

	def on_tree_select(self, ev=None):
		sel = self.tree.selection()
		if not sel:
			return
		if sel[0].startswith(("ityp:", "main:")):
			self.sub_selected = sel[0].split(":", 1)[1]
			if sel[0].startswith("ityp:"):
				self.fill_sub(self.sub_selected)
			self.apply_sub_selection()
			return
		tag = self.row_tag(sel[0])
		dec = self.row_decision(sel[0])
		was = self.preview
		self.preview = dec if dec and dec not in self.active else None
		if tag:
			if was is not None:
				self.recompute()
			self.select(tag, from_tree=True)
		elif dec:
			self.recompute()
			self.set_status(f"Preview of {self.dec_label(dec)}: makes {', '.join(sorted(dec.tags)) or 'no countries'}"
							+ (f"; collapses {', '.join(sorted(dec.collapsing))}" if dec.collapsing else "")
							+ (". Double-click to keep it switched on." if dec not in self.active else ". It is switched on (double-click: off)."))
		else:
			self.recompute()

	def on_tree_double(self, ev):
		row = self.tree.identify_row(ev.y)
		if row and row.startswith("ityp:"):
			self.edit_sub_window(row.split(":", 1)[1])
			return "break"
		dec = self.row_decision(row) if row else None
		if dec:
			self.toggle_decision(dec)
			return "break"

	def _show_on_map_items(self, menu, key, states_fn, label):
		"""'Show on map' (highlight + zoom; again on the same entry clears it) and 'Clear Show on map'."""
		if self.highlight and self.highlight_key == key:
			menu.add_command(label="Clear Show on map", command=self.clear_highlight)
			return
		menu.add_command(label="Show on map", command=lambda: self.show_on_map(key, states_fn(), label))
		if self.highlight:
			menu.add_command(label=f"Clear Show on map ({self.highlight_label})", command=self.clear_highlight)

	def show_on_map(self, key, states, label):
		if self.highlight and self.highlight_key == key:
			return self.clear_highlight()
		self.highlight, self.highlight_key, self.highlight_label = set(states), key, label
		pts = [self.map.centroids[s] for s in self.highlight if s in self.map.centroids]
		if not pts:
			self.set_status(f"{label} isn't on the map.")
			self.render()
			return
		self.zoom_to_points(pts)
		self.set_status(f"{label}: {len(self.highlight)} states highlighted. Right-click > Clear Show on map to clear it.")

	def clear_highlight(self):
		if self.highlight:
			self.set_status(f"Show on map cleared ({self.highlight_label}).")
		self.highlight, self.highlight_key, self.highlight_label = set(), None, ""
		self.render()

	def on_tree_menu(self, ev):
		row = self.tree.identify_row(ev.y)
		if not row:
			return
		self.tree.selection_set(row)
		menu = tk.Menu(self.root, tearoff=0)
		if row.startswith(("ityp:", "main:")):
			tok = row.split(":", 1)[1]

			def states():
				out = set()
				for s_, t in self.owner.items():
					if t in self.data.countries:
						main, sub = self.sub_ideology_of(t)
						if (sub == tok) if row.startswith("ityp:") else (self.data.leader_for(t, tok) is not None):
							out.add(s_)
				return out
			if row.startswith("ityp:"):
				menu.add_command(label="Edit...", command=lambda: self.edit_sub_window(tok))
				menu.add_command(label="Add a new sub-ideology after this...", command=lambda: self.new_sub(after=tok))
			else:
				menu.add_command(label=f"Add a new sub-ideology to {self.data.label(tok, tok)}...", command=lambda: self.new_sub(main=tok))
			menu.add_separator()
			self._show_on_map_items(menu, ("sub", tok), states, self.data.label(tok, tok))
			menu.tk_popup(ev.x_root, ev.y_root)
			return
		dec = self.row_decision(row)
		tag = self.row_tag(row)
		if dec:
			on = dec in self.active
			menu.add_command(label=("Switch off " if on else "Switch on ") + self.dec_label(dec), command=lambda: self.toggle_decision(dec))
			self._show_on_map_items(menu, ("dec", dec.key), lambda: {s for s, t in self.owner.items() if t in dec.tags},
									self.dec_label(dec))
			menu.add_command(label="Open the decision file", command=lambda: self.open_path(self.data.path(dec.rel)))
		if tag:
			self._show_on_map_items(menu, ("tag", tag), lambda: {s for s, t in self.owner.items() if t == tag},
									self.data.name(tag, self.ruling(tag)))
			for x in self.data.decisions:
				if tag in x.collapsing:
					on = x in self.active
					menu.add_command(label=f"{'Switch off' if on else 'Collapse it:'} {self.dec_label(x)}", command=lambda x=x: self.toggle_decision(x))
			evs = self.events_making(tag)
			if evs:
				sub = tk.Menu(menu, tearoff=0)
				for x in evs:
					sub.add_command(label=("Switch off " if x in self.active else "Launch ") + self.dec_label(x),
									command=lambda x=x: self.toggle_decision(x))
				menu.add_cascade(label=f"Events that make it ({len(evs)})", menu=sub)
			c = self.data.countries[tag]
			if c.history:
				menu.add_command(label="Open its history file", command=lambda: self.open_path(self.data.path(c.history)))
		if menu.index("end") is not None:
			menu.tk_popup(ev.x_root, ev.y_root)

	def toggle_decision(self, dec):
		if dec in self.active:
			self.active.remove(dec)
		else:
			# Only one type of a collapse at a time.
			self.active = [x for x in self.active if x not in dec.siblings]
			self.active.append(dec)
		self.preview = None
		self.recompute()
		self.rebuild_tree()
		names = ", ".join(self.dec_label(x) for x in self.active[:3]) + (f" and {len(self.active) - 3} more" if len(self.active) > 3 else "")
		self.active_label.config(text=f"Switched on: {names}" if self.active else "")
		if self.selected:
			self.fill_collapses()
			self.fill_spawn()
		self.set_status(f"{self.dec_label(dec)} switched {'on' if dec in self.active else 'off'}: "
						f"{', '.join(sorted(t for t in dec.tags if self.counts.get(t)))} on the map.")

	def collapse_all(self):
		"""Switches on every collapse (the first type of the ones with several)."""
		self.active = [x for x in self.data.decisions if x.kind == "Collapses" and (not x.siblings or x.key.endswith("#0"))]
		self.preview = None
		self.recompute()
		self.rebuild_tree()
		self.active_label.config(text=f"Switched on: all {len(self.active)} collapses")
		if self.selected:
			self.fill_collapses()
		self.set_status(f"Every collapse switched on ({len(self.active)}; the ones with several types use their first). "
						"Switch types in Show: Collapses, or Tools > Switch off all.")

	def clear_active(self):
		self.active = []
		self.preview = None
		self.active_label.config(text="")
		self.recompute()
		self.rebuild_tree()

	# ---------- select a country ----------
	def select(self, tag, from_tree=False):
		self.selected = tag
		if not from_tree:
			for iid in self._all_items():
				if self.row_tag(iid) == tag:
					self.tree.selection_set(iid)
					self.tree.see(iid)
					break
		d = self.data
		c = d.countries[tag]
		ruling = self.ruling(tag)
		self.head_flag.config(image=self.flag(tag, (82, 52), ruling))
		self.head_title.config(text=f"{d.name(tag, ruling)}  ({tag}" + (f" as {c.cosmetic})" if c.cosmetic else ")"))
		info = []
		if self.counts.get(tag):
			info.append(f"{self.counts[tag]} states on the map" + (" (with the switched-on collapses / bombs)" if self.active else ""))
		if c.history:
			info.append(c.history)
		else:
			info.append("No history file: it starts with nothing (Overview edits make one).")
		self.head_info.config(text="   ".join(info))
		self.fill_overview()
		self.fill_leaders()
		self._generics_for = None
		if self.tabs.select() == str(self.generics_tab):
			self.fill_generics()
		self.fill_ideas()
		self.fill_oob()
		self.fill_history()
		self.fill_spawn()
		self.rebuild_lut()

	# ---------- Sub-ideologies layer ----------
	def _build_sub_controls(self, left):
		g = self.sub_controls = ttk.Frame(left)
		ttk.Label(g, text="Gap Finder:").grid(row=0, column=0, sticky="w")
		self.sub_gap_var = tk.StringVar(value=GAP_ALL)
		box = ttk.Combobox(g, textvariable=self.sub_gap_var, values=[GAP_ALL] + list(SUB_GAP_OPTIONS), state="readonly", width=30)
		box.grid(row=0, column=1, sticky="w", padx=4, pady=1)
		box.bind("<<ComboboxSelected>>", lambda ev: self.rebuild_tree())
		self.sub_gap_count = tk.Label(g, text="", fg="#ffffff", bg="#c0392b", font=("Segoe UI", 9, "bold"), padx=6)
		ttk.Label(g, text="Sort by:").grid(row=1, column=0, sticky="w")
		sf = ttk.Frame(g)
		sf.grid(row=1, column=1, columnspan=2, sticky="w", padx=4, pady=1)
		self.sub_sort_var = tk.StringVar(value="File order")
		box = ttk.Combobox(sf, textvariable=self.sub_sort_var, values=SUB_SORT_OPTIONS, state="readonly", width=12)
		box.pack(side="left")
		box.bind("<<ComboboxSelected>>", lambda ev: self.rebuild_tree())
		self.sub_sort_rev = tk.BooleanVar(value=False)
		ttk.Checkbutton(sf, text="Reverse", variable=self.sub_sort_rev, command=self.rebuild_tree).pack(side="left", padx=4)
		self.sub_sections = tk.BooleanVar(value=True)
		ttk.Checkbutton(sf, text="Sections", variable=self.sub_sections, command=self.rebuild_tree).pack(side="left", padx=4)


	def apply_sub_selection(self):
		"""Map for the row picked in the Sub-ideologies list: a sub-ideology shows its Brush strength; an ideology
		row shows either every country's sub-ideology colour for that ideology (View: All X) or its popularity."""
		sel = getattr(self, "sub_selected", None)
		view_was = self.view_var.get()
		if getattr(self, "_keep_map", False):  # picked from the map: keep the map as it is
			self._keep_map = False
			return
		self.sub_highlight = None
		mode = self.map_mode.get()
		# The map mode stays what it is; the row only changes what that mode shows.
		if sel in self.data.mains and mode == "subideology":
			self.view_var.set(self.view_label(sel))
			self.set_status(f"Each country coloured by the sub-ideology of its {sel} leader (dark: it has none).")
		elif sel in self.data.mains and mode == "strength":
			self.set_status(f"Brush strength: how popular {sel} is in every country.")
		elif sel and mode == "subideology":
			# Stay on the sub-ideology colours; the countries with this one stay bright, the rest dim.
			st = self.data.subs.get(sel)
			if st and self.view_var.get() != VIEW_START:
				self.view_var.set(self.view_label(st.main))
			self.sub_highlight = sel
			n = sum(1 for t in set(self.owner.values()) if t in self.data.countries and self.sub_ideology_of(t)[1] == sel)
			self.set_status(f"{self.data.label(sel, sel)}: {n} countries on the map ({self.view_var.get()}). "
							"Brush strength (map bar) shows its popularity instead.")
		elif sel and mode == "strength":
			self.set_status(f"Brush strength: how popular {self.data.label(sel, sel)} is where the leader for its ideology has it.")
		self.rebuild_lut()
		if self.layer.get() == "subs" and self.view_var.get() != view_was:
			self.rebuild_tree()  # the country counts follow the view (only when it changed: no select loop)

	def switch_layer(self):
		subs = self.layer.get() == "subs"
		if subs:
			self.country_controls.pack_forget()
			self.sub_controls.pack(fill="x", pady=(4, 0), after=self.country_controls.master.winfo_children()[1])
			self.tree.heading("#0", text="Sub-ideology")
			self.tree.heading("tag", text="Token")
			self.tree.heading("states", text="Countries")
			self.tree.column("tag", width=150)
			self.tabs.pack_forget()
			self.head_info.pack_forget()
			self.sub_panel.pack(fill="both", expand=True)
			self.head_title.config(text="Pick a sub-ideology")
			self.head_flag.config(image="")
			self.left_hint.config(text="Sections: the ####MAINLINE#### banners of 00_ideologies.txt. On the Sub-ideology map a\n"
									   "picked one lights up; on Brush strength you see its popularity. Right-click: Show on map.")
		else:
			self.sub_controls.pack_forget()
			self.country_controls.pack(fill="x", pady=(4, 0), after=self.country_controls.master.winfo_children()[1])
			self.tree.heading("#0", text="Country")
			self.tree.heading("tag", text="Tag")
			self.tree.heading("states", text="States")
			self.tree.column("tag", width=42)
			self.sub_panel.pack_forget()
			self.head_info.pack(fill="x", pady=(2, 4))
			self.tabs.pack(fill="both", expand=True)
			self.head_title.config(text="Pick a country")
			self.left_hint.config(text="Click a collapse / bomb to preview it on the map; double-click (or right-click) to keep\n"
									   "it switched on. 'Collapse all' switches on every collapse.")
		self.rebuild_tree()
		self.rebuild_lut()

	def swatch(self, rgb, size=(14, 14)):
		key = ("sw", rgb, size)
		if key not in self._flags:
			self._flags[key] = ImageTk.PhotoImage(Image.new("RGBA", size, tuple(rgb) + (255,)))
		return self._flags[key]

	def sub_counts(self):
		"""sub-ideology -> (countries, est. pop) in the Ideology view, among countries on the map."""
		out = {}
		for tag in set(self.owner.values()):
			if tag not in self.data.countries:
				continue
			_, sub = self.sub_ideology_of(tag)
			n, p = out.get(sub, (0, 0))
			out[sub] = (n + 1, p + self.tag_pop(tag))
		return out

	def sub_gap_test(self):
		key = SUB_GAP_OPTIONS.get(self.sub_gap_var.get())
		d = self.data
		if key is None:
			return None
		if key == "icon":
			return lambda t: not d.sprite_texture(f"GFX_ideology_{t}")
		if key == "desc":
			return lambda t: not d.label(t + "_desc")
		if key == "colour":
			return lambda t: d.subs[t].rgb is None
		if key == "name":
			return lambda t: t not in d.loc
		if key == "unused":
			used = set()
			for c in d.countries.values():
				for cid in c.characters:
					ch = d.characters.get(cid)
					for lead in (ch.leaders() if ch else []):
						used.add(lead[0])
			return lambda t: t not in used
		return None

	def rebuild_sub_tree(self):
		d = self.data
		q = self.search_var.get().strip().lower()
		open_items = {i for i in self._all_items() if self.tree.item(i, "open")}
		sel = self.tree.selection()
		self.tree.delete(*self.tree.get_children())
		counts = self.sub_counts()
		gap = self.sub_gap_test()
		found = 0
		short = lambda n: f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e4 else (str(n) if n else "")
		key = self.sub_sort_var.get()

		def order(toks):
			if key == "Name":
				k = lambda t: d.label(t, t).lower()
			elif key == "Token":
				k = lambda t: t
			elif key == "Countries":
				k = lambda t: -counts.get(t, (0, 0))[0]
			elif key == "Est. pop":
				k = lambda t: -counts.get(t, (0, 0))[1]
			else:
				return list(reversed(toks)) if self.sub_sort_rev.get() else list(toks)
			return sorted(toks, key=k, reverse=self.sub_sort_rev.get())

		def wanted(t):
			return (not q or q in t.lower() or q in d.loc.get(t, "").lower()) and (gap is None or gap(t))

		def add_sub(parent, t):
			nonlocal found
			st = d.subs[t]
			found += gap is not None
			n, p = counts.get(t, (0, 0))
			self.tree.insert(parent, "end", iid=f"ityp:{t}", text=" " + d.label(t, t), values=(t, n or "", short(p)),
							 image=self.swatch(d.sub_rgb(t) or (128, 128, 128)), tags=("gap",) if gap is not None else ())

		for main in self.data.mains:
			toks = [t for t in d.ideologies.get(main, []) if wanted(t)]
			if not toks and (q or gap is not None):
				continue
			miid = f"main:{main}"
			n = sum(counts.get(t, (0, 0))[0] for t in d.ideologies.get(main, []))
			col = self.main_color(main)
			self.tree.insert("", "end", iid=miid, text=" " + d.label(main, main.title()), values=(main, n or "", ""),
							 image=self.swatch(col), open=miid in open_items or bool(q) or gap is not None, tags=("section",))
			if self.sub_sections.get():
				secs = [None] + d.ideo_sections.get(main, [])
				for sec in secs:
					in_sec = [t for t in toks if d.subs[t].section == sec]
					if not in_sec:
						continue
					if sec is None:
						for t in order(in_sec):
							add_sub(miid, t)
						continue
					siid = f"isec:{main}:{sec}"
					self.tree.insert(miid, "end", iid=siid, text=f"# {sec}", values=("", sum(counts.get(t, (0, 0))[0] for t in in_sec) or "", ""),
									 open=siid in open_items or bool(q) or gap is not None, tags=("section",))
					for t in order(in_sec):
						add_sub(siid, t)
			else:
				for t in order(toks):
					add_sub(miid, t)
		self.show_count.config(text="")
		if gap is None:
			self.sub_gap_count.grid_remove()
		else:
			self.sub_gap_count.config(text=f"{found} found")
			self.sub_gap_count.grid(row=0, column=2, sticky="w")
		for i in sel:
			if self.tree.exists(i):
				self.tree.selection_set(i)
				self.tree.see(i)

	def _build_sub_panel(self, right):
		p = self.sub_panel = ttk.Frame(right)
		self.sub_form = SubForm(p, self)
		self.sub_form.pack(fill="both", expand=True)
		self.sub_windows = []

	@property
	def sub_editing(self):
		return self.sub_form.editing if hasattr(self, "sub_form") else None

	def fill_sub(self, token):
		self.sub_form.fill(token)

	def edit_sub_window(self, token):
		"""Its own window to edit a sub-ideology (double-click, or right-click > Edit)."""
		for form in self.sub_windows:
			if form.editing == token and form.winfo_exists():
				form.winfo_toplevel().lift()
				return form
		win = tk.Toplevel(self.root)
		win.geometry("660x780")
		win.transient(self.root)
		form = SubForm(win, self, window=True)
		form.pack(fill="both", expand=True, padx=6, pady=6)
		form.fill(token)
		self.sub_windows.append(form)
		win.bind("<Destroy>", lambda ev: ev.widget is win and form in self.sub_windows and self.sub_windows.remove(form))
		return form

	def after_sub_saved(self, token):
		"""Reloads, then shows the new values in the panel and every window of that sub-ideology."""
		self.data._load_ideologies()
		self.rebuild_tree()
		for form in [self.sub_form] + self.sub_windows:
			if form.editing == token and form.winfo_exists():
				form.fill(token)
		self.rebuild_lut()

	def sub_loc_file(self, main):
		"""Where new names / descriptions of a main ideology's sub-ideologies go: the mod file its others are in."""
		d = self.data
		for t in d.ideologies.get(main, []):
			for k in (t, t + "_desc"):
				if k in d.loc_where and d.in_mod(d.loc_where[k][0]):
					return d.loc_where[k][0]
		return F_PARTIES_LOC

	def save_banner(self, sprite, src, main):
		"""A banner picture for a sub-ideology description: the same size and folder as the mod's other banners."""
		d = self.data
		existing = d.sprite_texture(sprite)
		size, folder = (300, 70), "gfx/interface/ideologies"
		for t in d.ideologies.get(main, []):
			other = parse_desc(d.loc.get(t + "_desc", ""))[0]
			p = d.sprite_texture(other) if other and other != sprite else None
			if p:
				im = load_image(p, (4096, 4096))
				if im:
					size = im.size
				folder = os.path.dirname(d.rel(p)).replace("\\", "/")
				break
		if existing:
			size = (load_image(existing, (4096, 4096)) or Image.new("RGBA", size)).size
		tex = f"{folder}/{sprite.removeprefix('GFX_')}.dds"
		path = existing if existing and os.path.abspath(existing).startswith(os.path.abspath(d.root)) else d.mod_path(tex)
		self.check_in_mod(path)
		if existing and os.path.exists(existing):
			self.backup(d.rel(existing))
		os.makedirs(os.path.dirname(path), exist_ok=True)
		self.touched(d.rel(path))
		fit_icon(src, size).save(path, "DDS")
		if not existing:
			rel = self.new_lines_file(F_IDEO_GFX, "gfx")
			self.backup(rel)
			tf = TextFile(d.mod_path(rel))
			lines = list(tf.lines)
			close = max(i for i, l in enumerate(lines) if l.strip() == "}")
			lines[close:close] = ["\tspriteType = {", f"\t\tname = \"{sprite}\"", f"\t\ttexturefile = \"{tex}\"", "\t}"]
			self.write_lines(rel, None, None, lines)
			if hasattr(d, "_sprites"):
				del d._sprites

	def set_loc_in(self, key, text, new_file):
		"""Like set_loc, but new keys go to new_file (or the tool's own file when the mod doesn't have it)."""
		d = self.data
		if key in d.loc_where or not text:
			return self.set_loc(key, text)
		new_file = self.new_lines_file(new_file, "loc")
		self.backup(new_file)
		tf = TextFile(d.mod_path(new_file))
		self.check_in_mod(tf.path)
		esc = (text if '\\"' in text else text.replace('"', '\\"')).replace("\n", "\\n")
		append_line(tf, f" {key}:0 \"{esc}\"")
		tf.save()
		d._load_loc()

	def edit_type_block(self, token, rgb=None, info=None):
		d = self.data
		st = d.subs[token]
		rel = st.rel
		tf = TextFile(d.path(rel))
		lines = list(tf.lines)
		first, last = st.entry.first, st.entry.last
		if info is not None:
			head = re.sub(r"\s*#.*$", "", lines[first]).rstrip()  # the note is the comment at the end of its first line
			lines[first] = head + (f" #{info}" if info else "")
		if rgb is not None:
			col = next((c for c in st.entry.value if c.key == "color" and c.block), None)
			if col is not None:
				lines[col.first] = re.sub(r"(color\s*=\s*)\{[^}]*\}", lambda m: m.group(1) + "{ %d %d %d }" % rgb, lines[col.first], count=1)
			else:
				indent = re.match(r"\s*", lines[first]).group(0)
				if first == last:  # 'token = { ... }' on one line
					lines[first] = re.sub(r"=\s*\{\s*", lambda m: "= { color = { %d %d %d } " % rgb, lines[first], count=1)
				else:
					lines.insert(first + 1, f"{indent}color = {{ {rgb[0]} {rgb[1]} {rgb[2]} }}")
		self.write_lines(rel, None, None, lines)

	def move_type_to_section(self, token, section):
		"""Moves a type's lines under another ####SECTION#### banner of its ideology (after its last type)."""
		d = self.data
		st = d.subs[token]
		others = [d.subs[t] for t in d.ideologies[st.main] if t != token and d.subs[t].section == section]
		if not others:
			messagebox.showinfo(APP_NAME, f"The section {section or '(top)'} has no other sub-ideology to put it next to.")
			return
		anchor = max(o.entry.last for o in others)
		tf = TextFile(d.path(st.rel))
		lines = list(tf.lines)
		block = lines[st.entry.first:st.entry.last + 1]
		if anchor > st.entry.last:
			lines = lines[:anchor + 1] + block + lines[anchor + 1:]
			del lines[st.entry.first:st.entry.last + 1]
		else:
			del lines[st.entry.first:st.entry.last + 1]
			lines = lines[:anchor + 1] + block + lines[anchor + 1:]
		self.write_lines(st.rel, None, None, lines)
		d._load_ideologies()

	def save_sub_icon(self, token, main, src):
		d = self.data
		tex = f"gfx/interface/ideologies/{main}_{token}.dds"
		existing = d.sprite_texture(f"GFX_ideology_{token}")
		path = existing if existing and os.path.abspath(existing).startswith(os.path.abspath(d.root)) else d.mod_path(tex)
		self.check_in_mod(path)
		if existing and os.path.exists(existing):
			self.backup(d.rel(existing))
		os.makedirs(os.path.dirname(path), exist_ok=True)
		self.touched(d.rel(path))
		fit_icon(src, IDEO_ICON).save(path, "DDS")
		if not existing:
			rel = self.new_lines_file(F_IDEO_GFX, "gfx")
			self.backup(rel)
			tf = TextFile(d.mod_path(rel))
			lines = list(tf.lines)
			close = max(i for i, l in enumerate(lines) if l.strip() == "}")
			lines[close:close] = ["\tspriteType = {", f"\t\tname = \"GFX_ideology_{token}\"", f"\t\ttexturefile = \"{tex}\"", "\t}"]
			self.write_lines(rel, None, None, lines)
			if hasattr(d, "_sprites"):
				del d._sprites

	def suggest_sub_token(self, main, name):
		"""The next numbered token when the ideology's others are numbered (NI_VARIANT_15), else main_name."""
		d = self.data
		toks = d.ideologies.get(main, [])
		nums = [m for m in (re.fullmatch(r"(.*?)(\d+)", t) for t in toks) if m]
		if toks and len(nums) * 2 >= len(toks):
			pres = [m.group(1) for m in nums]
			pre = max(set(pres), key=pres.count)
			mine = [m for m in nums if m.group(1) == pre]
			width = max(len(m.group(2)) for m in mine)
			n = max(int(m.group(2)) for m in mine) + 1
			while f"{pre}{n:0{width}d}" in d.subs:
				n += 1
			return f"{pre}{n:0{width}d}"
		slug = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
		return "" if not slug else slug if slug.startswith(main) else f"{main}_{slug}"

	def new_sub(self, main=None, after=None):
		"""Window to add a sub-ideology: its ideology, name, token, section, note and colour."""
		d = self.data
		cur = d.subs.get(after or self.sub_editing or "")
		mains = [m for m in d.mains if m in d.ideologies]
		if not mains:
			return
		main = main if main in mains else cur.main if cur else mains[0]
		win = tk.Toplevel(self.root)
		win.title("New sub-ideology")
		win.transient(self.root)
		win.resizable(False, False)
		f = ttk.Frame(win, padding=10)
		f.pack(fill="both", expand=True)
		labels = {f"{d.label(m, m)} ({m})": m for m in mains}
		v = {k: tk.StringVar() for k in ("main", "name", "token", "section", "note")}
		v["main"].set(next(k for k, m in labels.items() if m == main))
		v["section"].set(cur.section or "" if cur and cur.main == main else "")
		state = {"token_typed": False, "note_typed": False, "rgb": None}

		def chosen():
			return labels.get(v["main"].get(), main)

		def upper_notes(m):
			infos = [d.subs[t].info for t in d.ideologies.get(m, []) if d.subs[t].info]
			return infos and sum(i.isupper() for i in infos) * 2 > len(infos)

		def refresh(*_):
			m = chosen()
			if not state["token_typed"]:
				v["token"].set(self.suggest_sub_token(m, v["name"].get()))
			if not state["note_typed"]:
				n = v["name"].get().strip()
				v["note"].set(n.upper() if upper_notes(m) else n)
			sec_box.config(values=[""] + d.ideo_sections.get(m, []))
			if v["section"].get() not in [""] + d.ideo_sections.get(m, []):
				v["section"].set("")
			if state["rgb"] is None:
				own = [d.subs[t].rgb for t in d.ideologies.get(m, []) if d.subs[t].rgb]
				swatch.config(bg="#%02x%02x%02x" % (d.main_rgb.get(m) or self.main_color(m)))
				colour_note.config(text=f"(none: uses {d.label(m, m)}'s, like {len(d.ideologies.get(m, [])) - len(own)} of its others)")

		rows = (("main", "Ideology:"), ("name", "Name:"), ("token", "Token:"), ("section", "Section:"), ("note", "Note (#):"))
		for r, (k, text) in enumerate(rows):
			ttk.Label(f, text=text).grid(row=r, column=0, sticky="w", pady=2)
		ttk.Combobox(f, textvariable=v["main"], values=list(labels), state="readonly", width=34).grid(row=0, column=1, sticky="we")
		name_e = ttk.Entry(f, textvariable=v["name"], width=36)
		name_e.grid(row=1, column=1, sticky="we")
		tok_e = ttk.Entry(f, textvariable=v["token"], width=36)
		tok_e.grid(row=2, column=1, sticky="we")
		sec_box = ttk.Combobox(f, textvariable=v["section"], width=34)
		sec_box.grid(row=3, column=1, sticky="we")
		note_e = ttk.Entry(f, textvariable=v["note"], width=36)
		note_e.grid(row=4, column=1, sticky="we")
		tok_e.bind("<Key>", lambda ev: state.update(token_typed=True))
		note_e.bind("<Key>", lambda ev: state.update(note_typed=True))
		ttk.Label(f, text="Map colour:").grid(row=5, column=0, sticky="w", pady=2)
		cf = ttk.Frame(f)
		cf.grid(row=5, column=1, sticky="w")
		swatch = tk.Label(cf, width=8, relief="solid", bg="#808080")
		swatch.pack(side="left")

		def pick():
			c = colorchooser.askcolor(color=swatch.cget("bg"), parent=win)
			if c and c[0]:
				state["rgb"] = tuple(int(x) for x in c[0])
				swatch.config(bg=c[1])
				colour_note.config(text="(its own)")

		def no_colour():
			state["rgb"] = None
			refresh()
		ttk.Button(cf, text="Pick...", command=pick).pack(side="left", padx=4)
		ttk.Button(cf, text="None", command=no_colour).pack(side="left")
		colour_note = ttk.Label(f, text="", foreground="#777")
		colour_note.grid(row=6, column=1, sticky="w")
		for k in ("main", "name"):
			v[k].trace_add("write", refresh)
		refresh()

		def create():
			m, name, token = chosen(), v["name"].get().strip(), v["token"].get().strip()
			if not name:
				messagebox.showerror(APP_NAME, "Give it a name.", parent=win)
				return
			if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", token) or token in d.subs or token in d.ideologies:
				messagebox.showerror(APP_NAME, f"'{token}' can't be used (empty, odd characters, or already taken).", parent=win)
				return
			win.destroy()
			self.create_sub(m, name, token, v["section"].get().strip() or None, v["note"].get().strip(), state["rgb"])
			self.edit_sub_window(token)

		bf = ttk.Frame(f)
		bf.grid(row=7, column=0, columnspan=2, sticky="e", pady=(10, 0))
		ttk.Button(bf, text="Create", command=create).pack(side="left")
		ttk.Button(bf, text="Cancel", command=win.destroy).pack(side="left", padx=4)
		win.bind("<Return>", lambda ev: create())
		win.bind("<Escape>", lambda ev: win.destroy())
		name_e.focus_set()

	def create_sub(self, main, name, token, section, note, rgb):
		"""Writes the type after the last one of its section (in the same style: one line or a block) + its name."""
		d = self.data
		mates = [d.subs[t] for t in d.ideologies[main] if d.subs[t].section == section] or [d.subs[t] for t in d.ideologies[main]]
		last = max(mates, key=lambda m_: m_.entry.last) if mates else None
		ideo_rel = last.rel if last else d.main_rel.get(main, cd.F_IDEOLOGIES)
		lines = list(TextFile(d.path(ideo_rel)).lines)
		col = "color = { %d %d %d }" % rgb if rgb else ""
		if last is not None:
			anchor = last.entry.last
			indent = re.match(r"\s*", lines[last.entry.first]).group(0)
		else:
			types = next(t for t in d.main_entries[main].value if t.key == "types")
			anchor, indent = types.last - 1, re.match(r"\s*", lines[types.first]).group(0) + "\t"
		if last is not None and last.entry.first == last.entry.last:
			# Like the others: 'NI_VARIANT_15 = { can_be_randomly_selected = no } #NOTE'
			body = re.sub(r"\s*#.*$", "", lines[last.entry.first]).strip()
			body = re.sub(r"^[\w.\-]+", token, body, count=1)
			body = re.sub(r"color\s*=\s*\{[^}]*\}\s*", "", body)
			if col:
				body = re.sub(r"=\s*\{\s*", lambda m_: "= { " + col + " ", body, count=1)
			body = re.sub(r"\{\s+\}", "{ }", body)
			new = [indent + body + (f" #{note}" if note else "")]
		else:
			new = [f"{indent}{token} = {{" + (f" #{note}" if note else "")] + ([f"{indent}\t{col}"] if col else []) + [f"{indent}}}"]
		lines[anchor + 1:anchor + 1] = new
		self.write_lines(ideo_rel, None, None, lines)
		self.set_loc_in(token, name, self.sub_loc_file(main))
		d._load_ideologies()
		self.rebuild_tree()
		if self.tree.exists(f"ityp:{token}"):
			self.tree.selection_set(f"ityp:{token}")
			self.tree.see(f"ityp:{token}")
		self.set_status(f"Added {token} to {main} in {ideo_rel} (+ its name). Give it an icon, banner, quote and description and Save.")

	# ---------- Overview ----------
	def _build_overview(self):
		outer = ttk.Frame(self.tabs)
		self.tabs.add(outer, text="Overview")
		sc = ScrollFrame(outer)
		sc.pack(fill="both", expand=True)
		f = sc.inner
		self.ov_sections = {}

		sec = Section(f, "Cosmetic tag")
		sec.pack(fill="x")
		self.ov_sections["cosmetic"] = sec
		row = ttk.Frame(sec.body)
		row.pack(fill="x")
		ttk.Label(row, text="set_cosmetic_tag =").pack(side="left")
		self.cosmetic_var = tk.StringVar()
		ttk.Entry(row, textvariable=self.cosmetic_var, width=24).pack(side="left", padx=4)
		self.cosmetic_var.trace_add("write", lambda *a: self._sync_cosmetic_ticks())
		self.cosmetic_note = ttk.Label(sec.body, text="", foreground="#666", wraplength=420, justify="left")
		self.cosmetic_note.pack(anchor="w")
		ttk.Label(sec.body, text="Its known cosmetic tags (tick one to start with it, untick to have none; Save overview "
								 "writes it):", foreground="#555", wraplength=420).pack(anchor="w", pady=(4, 0))
		vf = ttk.Frame(sec.body)
		vf.pack(fill="x", pady=(2, 2))
		self.show_vanilla_cos = tk.BooleanVar(value=load_config().get("show_vanilla_cosmetics", True))
		self.vanilla_btn = ttk.Button(vf, command=self.toggle_vanilla_cosmetics)
		self.vanilla_btn.pack(side="left")
		tk.Label(vf, text=" vanilla ", bg=VANILLA_BG, relief="solid", bd=1, font=("Segoe UI", 8)).pack(side="left", padx=(8, 2))
		self.vanilla_note = ttk.Label(vf, text="", foreground="#777")
		self.vanilla_note.pack(side="left", padx=4)
		lf = ttk.Frame(sec.body)
		lf.pack(fill="x")
		self.cos_tree = ttk.Treeview(lf, columns=("found",), height=6, selectmode="none", show="tree")
		self.cos_tree.column("#0", width=270)
		self.cos_tree.column("found", width=150)
		ys = ttk.Scrollbar(lf, command=self.cos_tree.yview)
		self.cos_tree.config(yscrollcommand=ys.set)
		self.cos_tree.pack(side="left", fill="x", expand=True)
		ys.pack(side="left", fill="y")
		self.cos_tree.tag_configure("vanilla", background=VANILLA_BG)
		self.cos_tree.tag_configure("on", background="#c9f0c0", font=("Segoe UI", 9, "bold"))
		self.cos_tree.bind("<ButtonRelease-1>", lambda ev: self._cos_click(ev))
		self.cosmetic_ticks = {}

		sec = Section(f, "Names")
		sec.pack(fill="x")
		self.ov_sections["names"] = sec
		g = sec.body
		for j, h in enumerate(("Name", "Long name (_DEF)", "Adjective (_ADJ)")):
			ttk.Label(g, text=h, foreground="#555").grid(row=0, column=1 + j, sticky="w")
		self.name_vars = {}
		for r, ideo in enumerate((None,) + self.data.mains, start=1):
			ttk.Label(g, text=(self.data.label(ideo, ideo) if ideo else "default")).grid(row=r, column=0, sticky="w")
			for j, suffix in enumerate(("", "_DEF", "_ADJ")):
				v = tk.StringVar()
				self.name_vars[(ideo, suffix)] = v
				ttk.Entry(g, textvariable=v, width=17).grid(row=r, column=1 + j, sticky="we", padx=1, pady=1)
		for col in (1, 2, 3):
			g.columnconfigure(col, weight=1)
		ttk.Label(g, text="Empty ideology names fall back to the default one.", foreground="#777").grid(row=r + 1, column=0, columnspan=4, sticky="w")

		sec = Section(f, "Colour and flags")
		sec.pack(fill="x")
		self.ov_sections["look"] = sec
		g = sec.body
		row = ttk.Frame(g)
		row.pack(fill="x")
		ttk.Label(row, text="Map colour:").pack(side="left")
		self.color_swatch = tk.Label(row, width=8, relief="solid", bg="#808080")
		self.color_swatch.pack(side="left", padx=4)
		ttk.Button(row, text="Pick...", command=self.pick_color).pack(side="left")
		ttk.Button(row, text="Flags folder", command=lambda: self.open_path(self.data.path("gfx/flags"))).pack(side="right")
		self.flag_scroll = HScroll(g, 64)
		self.flag_scroll.pack(fill="x", pady=(4, 0))
		self.flag_row = self.flag_scroll.inner

		sec = Section(f, "Start values")
		sec.pack(fill="x")
		self.ov_sections["values"] = sec
		g = sec.body
		self.hist_vars = {}
		for r, (key, label) in enumerate((("capital", "Capital (state id)"), ("set_stability", "Stability (0-1)"),
										  ("set_war_support", "War support (0-1)"), ("set_research_slots", "Research slots"))):
			ttk.Label(g, text=label + ":").grid(row=r, column=0, sticky="w")
			v = tk.StringVar()
			self.hist_vars[key] = v
			ttk.Entry(g, textvariable=v, width=10).grid(row=r, column=1, sticky="w", pady=1)
			if key == "capital":
				self.capital_name = ttk.Label(g, text="", foreground="#555")
				self.capital_name.grid(row=r, column=2, sticky="w", padx=4)

		sec = Section(f, "Politics")
		sec.pack(fill="x")
		self.ov_sections["politics"] = sec
		g = sec.body
		ttk.Label(g, text="Ruling party:").grid(row=0, column=0, sticky="w")
		self.ruling_var = tk.StringVar()
		ttk.Combobox(g, textvariable=self.ruling_var, values=self.data.mains, state="readonly", width=12).grid(row=0, column=1, sticky="w")
		self.elect_vars = {"last_election": tk.StringVar(), "election_frequency": tk.StringVar()}
		ttk.Label(g, text="Last election:").grid(row=1, column=0, sticky="w")
		ttk.Entry(g, textvariable=self.elect_vars["last_election"], width=12).grid(row=1, column=1, sticky="w")
		ttk.Label(g, text="Every (months):").grid(row=2, column=0, sticky="w")
		ttk.Entry(g, textvariable=self.elect_vars["election_frequency"], width=6).grid(row=2, column=1, sticky="w")
		self.elections_allowed = tk.BooleanVar()
		ttk.Checkbutton(g, text="Elections allowed", variable=self.elections_allowed).grid(row=3, column=0, columnspan=2, sticky="w")
		ttk.Label(g, text="Popularities (%):").grid(row=4, column=0, sticky="nw")
		pf = ttk.Frame(g)
		pf.grid(row=4, column=1, columnspan=2, sticky="w")
		self.pop_vars = {}
		for i, ideo in enumerate(self.data.mains):
			tk.Label(pf, text=self.data.label(ideo, ideo), fg="#%02x%02x%02x" % self.main_color(ideo)).grid(row=i // 2, column=(i % 2) * 2, sticky="w")
			v = tk.StringVar()
			self.pop_vars[ideo] = v
			ttk.Spinbox(pf, from_=0, to=100, textvariable=v, width=4, command=self._pop_total).grid(row=i // 2, column=(i % 2) * 2 + 1, padx=(2, 10))
			v.trace_add("write", lambda *a: self._pop_total())
		self.pop_total = ttk.Label(pf, text="")
		self.pop_total.grid(row=2, column=0, columnspan=4, sticky="w")
		ttk.Label(g, text="Leader at start:").grid(row=5, column=0, sticky="w")
		self.ruler_label = ttk.Label(g, text="", foreground="#333", wraplength=300)
		self.ruler_label.grid(row=5, column=1, columnspan=2, sticky="w")

		sec = Section(f, "Collapses")
		sec.pack(fill="x")
		self.ov_sections["collapses"] = sec
		self.collapse_box = sec.body

		bf = ttk.Frame(f)
		bf.pack(fill="x", pady=(8, 4))
		ttk.Button(bf, text="Save overview", command=self.save_overview).pack(side="left")
		ttk.Button(bf, text="Open history file", command=lambda: self.selected and self.data.countries[self.selected].history
				   and self.open_path(self.data.path(self.data.countries[self.selected].history))).pack(side="left", padx=4)
		ttk.Button(bf, text="Fold all", command=lambda: [x.toggle(False) for x in self.ov_sections.values()]).pack(side="right")
		ttk.Button(bf, text="Unfold all", command=lambda: [x.toggle(True) for x in self.ov_sections.values()]).pack(side="right", padx=4)

	def _pop_total(self):
		try:
			t = sum(int(float(v.get() or 0)) for v in self.pop_vars.values())
		except ValueError:
			t = None
		self.pop_total.config(text=f"total {t}" if t is not None else "", foreground="#1b7f2a" if t == 100 else "#b00020")

	def fill_collapses(self):
		"""Overview > Collapses: the collapses / bombs where this country breaks up or appears, with switches."""
		d, tag = self.data, self.selected
		for w in self.collapse_box.winfo_children():
			w.destroy()
		mine = [x for x in d.decisions if tag in x.collapsing or tag in x.releases]
		makes = [x for x in d.decisions if tag in x.tags and x not in mine]
		if not mine and not makes:
			ttk.Label(self.collapse_box, text="No collapse or bomb involves it.", foreground="#777").pack(anchor="w")
			return
		for x, how in [(x, "breaks it up into " + (", ".join(sorted(x.tags)) or "nothing")) for x in mine] + \
				[(x, "makes it") for x in makes]:
			row = ttk.Frame(self.collapse_box)
			row.pack(fill="x", pady=1)
			on = x in self.active
			ttk.Button(row, text="Switch off" if on else "Switch on", width=10, command=lambda x=x: self.toggle_decision(x)).pack(side="left")
			tk.Label(row, text=f"{self.dec_label(x)} ({x.kind}): {how}", anchor="w", justify="left", wraplength=330,
					 fg="#1b6a1b" if on else "#333").pack(side="left", padx=4)

	def fill_overview(self):
		d, tag = self.data, self.selected
		c = d.countries[tag]
		self._filling_cosmetic = True
		self.cosmetic_var.set(c.cosmetic or "")
		self._filling_cosmetic = False
		self.fill_cosmetic_list(tag)
		self.fill_look(c.cosmetic or tag)
		for key, v in self.hist_vars.items():
			v.set(str(c.get(key, "")))
		cap = c.get("capital")
		self.capital_name.config(text=d.state_names.get(int(cap), "") if cap and str(cap).isdigit() else "")
		pol = c.get("set_politics")
		pol = pol if isinstance(pol, list) else []
		get = lambda k: next((e.value for e in reversed(pol) if e.key == k and not e.block), "")
		self.ruling_var.set(get("ruling_party"))
		for k, v in self.elect_vars.items():
			v.set(get(k))
		self.elections_allowed.set(get("elections_allowed") == "yes")
		pops = c.get("set_popularities")
		pops = pops if isinstance(pops, list) else []
		for ideo, v in self.pop_vars.items():
			v.set(next((e.value for e in reversed(pops) if e.key == ideo), ""))
		self.loaded_overview = self._overview_values()
		ruler = self.start_leader(tag)
		self.ruler_label.config(text=f"{d.label(ruler.name_key, ruler.id)} ({d.lead_sub(ruler, self.ruling(tag))})" if ruler else "(none recruited for the ruling party)")
		self.fill_collapses()

	def fill_cosmetic_list(self, tag):
		"""Overview > Cosmetic tag: every known cosmetic tag of this country (one list: fast even with hundreds),
		ticked when it is the one in the box, with its flag, its name and where it was found."""
		d = self.data
		t = self.cos_tree
		t.delete(*t.get_children())
		found = d.cosmetics.get(tag, {})
		cur = self.cosmetic_var.get().strip()
		keys = sorted(found, key=lambda k: (k != cur, k.lower()))
		if cur and cur not in found:
			keys.insert(0, cur)
		vanilla = [k for k in keys if k in d.vanilla_cosmetics]
		show = self.show_vanilla_cos.get()
		self.vanilla_btn.config(text="Switch off vanilla cosmetic tags" if show else "Switch on vanilla cosmetic tags")
		self.vanilla_note.config(text=(f"{len(vanilla)} from vanilla" + ("" if show else " hidden")) if vanilla else "none from vanilla")
		if not show:
			keys = [k for k in keys if k not in d.vanilla_cosmetics or k == cur]  # the one in use always shows
		self.cosmetic_ticks = {k: None for k in keys}
		if not keys:
			t.insert("", "end", iid="__none", text="(none found)" if not vanilla else "(only vanilla ones - switched off)")
			return
		ruling = self.ruling(tag)
		for k in keys:
			name = d.label(f"{k}_{ruling}") or d.label(k) or ""
			src = sorted(found.get(k, {"typed in"}))
			files = d.cosmetic_files.get(k, set())
			tip = ", ".join(src) + (f" ({len(files)} file{'s' if len(files) != 1 else ''})" if files else "")
			if k in d.vanilla_cosmetics:
				tip = "vanilla; " + tip
			t.insert("", "end", iid=k, text=("☑ " if k == cur else "☐ ") + k + (f"  -  {name}" if name else ""),
					 values=(tip,), image=self.key_flag(k, (24, 16), ruling), tags=self._cos_tags(k, k == cur))

	def _cos_tags(self, key, on):
		return (("on",) if on else ()) + (("vanilla",) if key in self.data.vanilla_cosmetics else ())

	def toggle_vanilla_cosmetics(self):
		self.show_vanilla_cos.set(not self.show_vanilla_cos.get())
		save_config(show_vanilla_cosmetics=self.show_vanilla_cos.get())  # remembered next time
		if self.selected:
			self.fill_cosmetic_list(self.selected)

	def _cos_click(self, ev):
		k = self.cos_tree.identify_row(ev.y)
		if k and k != "__none":
			self._tick_cosmetic(k)

	def key_flag(self, key, size, ideology=None):
		"""Flag of a tag or cosmetic tag (falls back to the selected country's own)."""
		fk = ("kf", key, size, ideology)
		if fk not in self._flags:
			d = self.data
			p = d.cosmetic_flag(key, ideology) or (d.flag_path(self.selected, ideology, raw=True) if self.selected else None)
			im = load_image(p, size) if p else None
			canvas = Image.new("RGBA", size, (0, 0, 0, 0))
			if im is None:
				canvas = Image.new("RGBA", size, (90, 90, 90, 255))
			else:
				canvas.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
			self._flags[fk] = ImageTk.PhotoImage(canvas)
		return self._flags[fk]

	def fill_look(self, key):
		"""Names, map colour and flags of the Overview for `key`: the country's tag, or the cosmetic tag ticked /
		typed (shown straight away; the name edits then go to that cosmetic tag's lines)."""
		d, tag = self.data, self.selected
		c = d.countries[tag]
		self.look_key = key
		saved = (c.cosmetic or tag) == key
		if key != tag:
			self.cosmetic_note.config(text=f"Names, map colour and flags below are {key}'s (its localisation, cosmetic.txt, "
										   f"gfx/flags/{key}*.tga)" + ("." if saved else " - not saved yet: Save overview makes it "
																			   "the start cosmetic tag.") + f" Untick it to see {tag}'s own.")
		else:
			self.cosmetic_note.config(text="No cosmetic tag: names, colour and flags are the tag's own." +
										  ("" if saved else " (Save overview removes the cosmetic tag.)"))
		for (ideo, suffix), v in self.name_vars.items():
			k = f"{key}_{ideo}{suffix}" if ideo else f"{key}{suffix}"
			v.set(d.loc.get(k, ""))
		self.loaded_names = {k: v.get() for k, v in self.name_vars.items()}
		rgb = (d.cosmetic_rgb.get(key) if key != tag else None) or d.countries[tag].rgb
		self.color_swatch.config(bg="#%02x%02x%02x" % tag_color(tag, rgb))
		self.new_rgb = None
		for w in self.flag_row.winfo_children():
			w.destroy()
		for ideo in (None,) + self.data.mains:
			col = ttk.Frame(self.flag_row)
			col.pack(side="left", padx=3)
			has = d.has_flag(key, ideo) if ideo else d.has_flag(key)
			tk.Label(col, image=self.key_flag(key, (62, 40), ideo)).pack()
			tk.Label(col, text=(ideo or "base") + ("" if has else " (missing)"), fg="#666" if has else "#b00020").pack()
		# The header shows it too.
		ruling = self.ruling(tag)
		name = d.label(f"{key}_{ruling}") or d.label(key) or d.name(tag, ruling, raw=True)
		self.head_flag.config(image=self.key_flag(key, (82, 52), ruling))
		self.head_title.config(text=f"{name}  ({tag}" + (f" as {key}" if key != tag else "") + (")" if saved else ", not saved)"))

	def _tick_cosmetic(self, key):
		"""Ticks a cosmetic tag (unticks the others), or unticks the one ticked."""
		cur = self.cosmetic_var.get().strip()
		self.cosmetic_var.set("" if cur == key else key)
		self.fill_look(self.cosmetic_var.get().strip() or self.selected)
		self.set_status("Cosmetic tag at start: " + (self.cosmetic_var.get() or "none") + " - Save overview to write it.")

	def _sync_cosmetic_ticks(self):
		cur = self.cosmetic_var.get().strip()
		t = getattr(self, "cos_tree", None)
		if t is not None:
			for k in t.get_children():
				if k == "__none":
					continue
				on = k == cur
				text = t.item(k, "text")
				t.item(k, text=("☑ " if on else "☐ ") + text[2:], tags=self._cos_tags(k, on))
		# Typed in the box: show that tag's look once typing stops.
		if self.selected and not getattr(self, "_filling_cosmetic", False):
			if getattr(self, "_look_job", None):
				self.root.after_cancel(self._look_job)
			self._look_job = self.root.after(500, lambda: self.selected and getattr(self, "look_key", None) != (
				self.cosmetic_var.get().strip() or self.selected) and self.fill_look(self.cosmetic_var.get().strip() or self.selected))

	def _overview_values(self):
		return dict({k: v.get().strip() for k, v in self.hist_vars.items()}, ruling=self.ruling_var.get(),
					set_cosmetic_tag=self.cosmetic_var.get().strip(),
					**{k: v.get().strip() for k, v in self.elect_vars.items()}, allowed=self.elections_allowed.get(),
					**{"pop_" + k: v.get().strip() for k, v in self.pop_vars.items()})

	def start_leader(self, tag):
		"""The recruited country leader whose ideology belongs to the ruling party (who the game shows)."""
		d = self.data
		ruling = self.ruling(tag)
		for cid in d.countries[tag].characters:
			ch = d.characters.get(cid)
			if ch and d.lead_sub(ch, ruling):
				return ch
		return None

	def pick_color(self):
		if not self.selected:
			return
		cur = self.color_swatch.cget("bg")
		c = colorchooser.askcolor(color=cur, parent=self.root)
		if c and c[0]:
			self.new_rgb = tuple(int(x) for x in c[0])
			self.color_swatch.config(bg=c[1])

	def save_overview(self):
		tag = self.selected
		if not tag:
			return
		d = self.data
		c = d.countries[tag]
		done = []
		# Names.
		for (ideo, suffix), v in self.name_vars.items():
			new = v.get().strip()
			if new != self.loaded_names[(ideo, suffix)]:
				nk = getattr(self, "look_key", None) or d.name_key(tag)
				key = f"{nk}_{ideo}{suffix}" if ideo else f"{nk}{suffix}"
				self.set_loc(key, new)
				done.append(key)
		# Colour.
		if self.new_rgb:
			self.set_color(tag, self.new_rgb, getattr(self, "look_key", None))
			done.append("colour")
		# History values.
		now = self._overview_values()
		if now != self.loaded_overview:
			if not c.history:
				self.make_history(tag)
			self.save_history_values(tag, now, self.loaded_overview)
			done.append("history")
		if done:
			self._flags = {k: v for k, v in self._flags.items() if k[0] != tag}  # its flag may be another tag's now
			self.recompute()
			self.rebuild_tree()
			self.select(tag)
			self.set_status(f"Saved {tag}: {', '.join(done)}.")
		else:
			self.set_status("Nothing changed.")

	def set_loc(self, key, text):
		d = self.data
		text = text.replace('"', '\\"') if '\\"' not in text else text
		if key in d.loc_where:
			rel, i = d.loc_where[key]
			self.backup(rel)
			tf = TextFile(d.mod_path(rel))
			self.check_in_mod(tf.path)
			m = RX_LOC_VALUE.match(tf.lines[i])
			if m:
				tf.lines[i] = m.group(1) + text + m.group(3)
				tf.save()
		elif text:
			rel = self.new_lines_file(cd.F_COUNTRY_LOC, "loc")
			self.backup(rel)
			tf = TextFile(d.mod_path(rel))
			self.check_in_mod(tf.path)
			append_line(tf, f" {key}:0 \"{text}\"")
			tf.save()
		d._load_loc()

	def set_color(self, tag, rgb, key=None):
		d = self.data
		cos = (key if key != tag else None) if key else d.countries[tag].cosmetic
		rel = cd.F_COSMETIC if cos else cd.F_COLORS
		self.backup(rel)
		if not d.in_mod(rel):  # neither the mod nor the base game has it
			os.makedirs(os.path.dirname(d.mod_path(rel)), exist_ok=True)
			open(d.mod_path(rel), "w", encoding="utf-8").write("")
		tf = TextFile(d.mod_path(rel))
		self.check_in_mod(tf.path)
		e = d.cosmetic_entries.get(cos) if cos else d.colors_entries.get(tag)
		tag = cos or tag
		col = next((x for x in e.value if x.key == "color"), None) if e else None
		if col is not None:
			line = tf.lines[col.first]
			tf.lines[col.first] = re.sub(r"(color\s*=\s*rgb\s*\{)[^}]*\}", r"\g<1> %d %d %d }" % rgb, line, count=1)
		else:
			tf.lines += [f"{tag} = {{", f"\tcolor = rgb {{ {rgb[0]} {rgb[1]} {rgb[2]} }}",
						 f"\tcolor_ui = rgb {{ {rgb[0]} {rgb[1]} {rgb[2]} }}", "}"]
			tf.ends = tf.ends[:-1] + [tf.nl] * 4 + [""]
		tf.save()
		d._load_colors()

	def make_history(self, tag):
		d = self.data
		# Never overwrite: a file for this tag may exist under another case ("FLo - Florida.txt").
		same = [os.path.basename(f) for f in d._files(cd.D_HISTORY) if os.path.basename(f)[:3].upper() == tag.upper()
				and os.path.basename(f)[3:6] == " - "]
		if same:
			d.countries[tag].history = f"{cd.D_HISTORY}/{same[0]}"
			self.reload_file(d.countries[tag].history)
			return
		name = re.sub(r'[\\/:*?"<>|]', "", d.name(tag)) or tag
		rel = f"{cd.D_HISTORY}/{tag} - {name}.txt"
		self.touched(rel)
		os.makedirs(os.path.dirname(d.mod_path(rel)), exist_ok=True)
		with open(d.mod_path(rel), "x", encoding="utf-8-sig", newline="\r\n") as f:
			f.write("capital = 1\n\noob = \"generic\"\n\nset_research_slots = 3\nset_stability = 0.5\nset_war_support = 0.5\n\n"
					"set_politics = {\n\truling_party = neutrality\n\tlast_election = \"1930.1.1\"\n\telection_frequency = 48\n"
					"\telections_allowed = no\n}\n\nset_popularities = {\n\tdemocratic = 25\n\tfascism = 25\n\tcommunism = 25\n"
					"\tneutrality = 25\n}\n")
		d.countries[tag].history = rel
		self.reload_file(rel)

	def save_history_values(self, tag, now, was):
		"""Writes the Overview values into the history file: each one replaces the line that sets it now (the last
		one, as the game applies them in order), or goes in a new line."""
		d = self.data
		c = d.countries[tag]
		rel = c.history
		self.backup(rel)
		tf = TextFile(d.path(rel))
		top = parse("\n".join(tf.lines))
		edits = {}   # line -> new text
		inserts = []  # lines added at the end

		def set_top(key, value):
			hit = [e for e in top if e.key == key and not e.block]
			if hit and value == "" and key == "set_cosmetic_tag":
				for e in hit:
					edits[e.first] = None  # no cosmetic tag any more: its lines go
				return
			if hit:
				e = hit[-1]
				edits[e.first] = re.sub(r"(\b%s\s*=\s*)(\"[^\"]*\"|\S+)" % re.escape(key), lambda m: m.group(1) + value,
										edits.get(e.first, tf.lines[e.first]), count=1)
			elif value != "":
				# A new top line goes under the capital / oob lines (else at the end).
				anchor = [e for e in top if e.key in ("oob", "capital") and not e.block]
				if anchor:
					a = anchor[-1].first
					edits[a] = edits.get(a, tf.lines[a]) + chr(10) + f"{key} = {value}"
				else:
					inserts.append(f"{key} = {value}")

		def set_in_block(block_key, values):
			blocks = [e for e in top if e.key == block_key and e.block]
			if not blocks:
				inserts.extend([f"{block_key} = {{"] + [f"\t{k} = {v}" for k, v in values.items() if v != ""] + ["}"])
				return
			b = blocks[-1]
			for k, v in values.items():
				hit = [e for e in b.value if e.key == k and not e.block]
				if hit:
					e = hit[-1]
					edits[e.first] = re.sub(r"(\b%s\s*=\s*)(\"[^\"]*\"|\S+)" % re.escape(k), lambda m: m.group(1) + v,
											edits.get(e.first, tf.lines[e.first]), count=1)
				elif v != "":
					close = b.last
					edits[close] = f"\t{k} = {v}" + "\n" + edits.get(close, tf.lines[close])

		changed = lambda k: k in now and now[k] != was.get(k)
		for key in list(self.hist_vars) + ["oob", "set_cosmetic_tag"]:
			if changed(key):
				set_top(key, now[key])
		pol = {}
		if changed("ruling"):
			pol["ruling_party"] = now["ruling"]
		if changed("last_election"):
			pol["last_election"] = f'"{now["last_election"].strip(chr(34))}"'
		if changed("election_frequency"):
			pol["election_frequency"] = now["election_frequency"]
		if changed("allowed"):
			pol["elections_allowed"] = "yes" if now["allowed"] else "no"
		if pol:
			set_in_block("set_politics", pol)
		pops = {i: now["pop_" + i] for i in self.data.mains if changed("pop_" + i)}
		if pops:
			set_in_block("set_popularities", pops)
		new_lines = []
		for i, line in enumerate(tf.lines):
			new = edits.get(i, line)
			if new is not None:
				new_lines += new.split("\n")
		new_lines += inserts
		self.write_lines(rel, None, None, new_lines)

	# ---------- Leaders ----------
	# ---------- Generics ----------
	def _build_generics(self):
		f = self.generics_tab = ttk.Frame(self.tabs, padding=4)
		self.tabs.add(f, text="Generics")
		self.gen_source = ttk.Label(f, text="", font=("Segoe UI", 9, "bold"), wraplength=440, justify="left")
		self.gen_source.pack(anchor="w")
		self.gen_note = ttk.Label(f, text="", foreground="#666", wraplength=440, justify="left")
		self.gen_note.pack(anchor="w", pady=(0, 2))
		rf = ttk.Frame(f)
		rf.pack(fill="x", pady=(0, 4))
		ttk.Button(rf, text="Open the rework list", style="Small.TButton", command=self.open_rework_file).pack(side="left")
		self.rework_label = tk.Label(rf, text="", fg=REWORK_COLOUR, font=("Segoe UI", 8), wraplength=320, justify="left")
		self.rework_label.pack(side="left", padx=6)
		self._gen_cells = {}
		self.gen_scroll = ScrollFrame(f)
		self.gen_scroll.pack(fill="both", expand=True)
		self._gen_photos = []
		self._gen_cache = {}
		self._generics_for = None
		self.tabs.bind("<<NotebookTabChanged>>", lambda ev: self.tabs.select() == str(self.generics_tab)
					   and self._generics_for != self.selected and self.fill_generics(), add="+")

	def fill_generics(self):
		"""Its generic portraits (own block, or its continent's), large with the small one (sprite_small) next to it."""
		d, tag = self.data, self.selected
		if not tag:
			return
		self._generics_for = tag
		body = self.gen_scroll.inner
		for w in body.winfo_children():
			w.destroy()
		self._gen_cells = {}
		self._gen_photos = []
		kind, key = d.generic_source(tag)
		items = d.generics_of(tag)
		if kind == "own":
			files = sorted(d.generic_files.get(key, ()))
			self.gen_source.config(text=f"Its own generics: {key}" + (" (its cosmetic tag)" if key != tag else ""), foreground="#1b6a1b")
			self.gen_note.config(text="From " + ", ".join(files))
		elif kind == "continent":
			same = sum(1 for t in d.countries if d.generic_source(t) == (kind, key))
			self.gen_source.config(text=f"Shared: {d.label(key, key.replace('_', ' ').title())} (its capital's continent)", foreground="#8a5a00")
			self.gen_note.config(text=f"No block of its own in portraits/: it uses continent = {{ name = {key} }} like {same - 1} other "
									  f"countries. Add a '{tag} = {{ army = {{ male = {{ ... }} }} }}' block to give it its own.")
		else:
			self.gen_source.config(text="No generic portraits", foreground="#b00")
			self.gen_note.config(text=("Its continent (" + key + ") has no generics block either" if key else
									   "It has no capital / continent") + ": the game shows the unknown portrait.")
		if not items:
			return
		groups = {}
		for cat, detail, sprite in items:
			groups.setdefault((cat, detail), []).append(sprite)
		# Cells now, pictures a few at a time after (a continent can have hundreds): the tab shows at once.
		jobs = []
		for (cat, detail), sprites in groups.items():
			sec = Section(body, f"{cat.title()}" + (f" - {detail}" if detail else "") + f" ({len(sprites)})")
			sec.pack(fill="x")
			g = sec.body
			for i, sprite in enumerate(sprites):
				cell = tk.Frame(g, padx=2, pady=2, highlightthickness=2)
				cell.grid(row=i // 3, column=i % 3, sticky="n", padx=1, pady=1)
				pics = tk.Frame(cell)
				pics.pack()
				for size, name, box in (("large", sprite, (66, 90)), ("small", sprite + "_small", (40, 54))):
					if size == "small" and not d.needs_small(cat, sprite):
						continue  # political / operative / scientist portraits have no small one
					lab = tk.Label(pics, text="...", fg="#999", relief="groove", width=5 if size == "small" else 8,
								   height=3 if size == "small" else 5, font=("Segoe UI", 7))
					lab.pack(side="left", anchor="s", padx=1)
					jobs.append((lab, size, name, box))
				name_lab = tk.Label(cell, text="", font=("Segoe UI", 7), wraplength=125)
				name_lab.pack()
				used = (f"{key} " if kind == "own" else f"continent {key} ") + f"({cat}" + (f" / {detail})" if detail else ")")
				self._gen_cells.setdefault(sprite, []).append((cell, name_lab))
				self._show_rework(sprite)
				for w in [cell, pics, name_lab] + list(pics.winfo_children()):
					w.bind("<Button-3>", lambda ev, sp=sprite, u=used: self._generic_menu(ev, sp, u))
		self._update_rework_label()
		self._gen_missing = 0
		self._gen_base_note = self.gen_note.cget("text")
		if getattr(self, "_gen_job", None):
			self.root.after_cancel(self._gen_job)
		self._gen_job = self.root.after(1, lambda: self._load_generic_pictures(tag, jobs))

	# ---------- generics marked for rework (generics_to_rework.txt next to the exe) ----------
	def rework_marks(self):
		return self.rework.get(os.path.basename(os.path.normpath(self.mod_root)), {})

	def _generic_menu(self, ev, sprite, used):
		menu = tk.Menu(self.root, tearoff=0)
		menu.add_command(label=sprite, state="disabled")
		self.rework_menu_items(menu, sprite, used)
		menu.add_separator()
		menu.add_command(label="Copy the sprite name", command=lambda: (self.root.clipboard_clear(), self.root.clipboard_append(sprite)))
		path = self.data.portrait_path(sprite)
		if path:
			menu.add_command(label="Open the picture", command=lambda: self.open_path(path))
		menu.tk_popup(ev.x_root, ev.y_root)

	def rework_menu_items(self, menu, sprite, used):
		"""Mark for rework: one of the categories (ticked = its category now), or not marked."""
		cur = self.rework_marks().get(sprite, (None,))[0]
		var = tk.StringVar(value=cur or "")
		self._rework_var = var  # kept alive while the menu is open
		sub = tk.Menu(menu, tearoff=0)
		for cat, colour in REWORK_CATS.items():
			sub.add_radiobutton(label=cat, variable=var, value=cat, foreground=colour,
								command=lambda c=cat: self.mark_rework(sprite, used, c))
		sub.add_separator()
		sub.add_radiobutton(label="Not marked", variable=var, value="", command=lambda: self.mark_rework(sprite, used, None))
		menu.add_cascade(label="Mark for rework" + (f"  (now: {cur})" if cur else ""), menu=sub)

	def mark_rework(self, sprite, used, cat):
		"""cat: a REWORK_CATS category, or None to unmark."""
		mod = os.path.basename(os.path.normpath(self.mod_root))
		self.rework = load_rework()  # someone (or another window) may have changed it
		marks = self.rework.setdefault(mod, {})
		if cat:
			marks[sprite] = (cat, used, time.strftime("%Y-%m-%d"))
		else:
			marks.pop(sprite, None)
		try:
			save_rework(self.rework)
		except OSError as ex:
			messagebox.showerror(APP_NAME, f"Can't write {REWORK_FILE}:\n{ex}")
			return
		self._show_rework(sprite)
		self._update_rework_label()
		self._show_portrait_rework()
		self._mark_leader_rows()
		self.set_status(f"{sprite}: {cat or 'no longer marked for rework'} ({os.path.basename(REWORK_FILE)}: "
						f"{len(marks)} marked in this mod).")
		if GAP_OPTIONS.get(self.gap_var.get(), "").startswith("rework:"):
			self.rebuild_tree()

	def _show_rework(self, sprite):
		m = self.rework_marks().get(sprite)
		for cell, name_lab in self._gen_cells.get(sprite, []):
			if not cell.winfo_exists():
				continue
			bg = cell.cget("bg")
			col = REWORK_CATS[m[0]] if m else bg
			cell.config(highlightbackground=col, highlightcolor=col)
			name_lab.config(text=(f"⚑ {m[0]}\n" if m else "") + sprite.removeprefix("GFX_"), fg=REWORK_CATS[m[0]] if m else "#555",
							font=("Segoe UI", 7, "bold" if m else "normal"))

	def _update_rework_label(self):
		marks = self.rework_marks()
		mine = sum(1 for sp in self._gen_cells if sp in marks)
		self.rework_label.config(text=(f"⚑ {mine} of these marked for rework; " if mine else "") +
								 f"{len(marks)} portraits marked in this mod (right-click a portrait to mark it)")

	def open_rework_file(self):
		if not os.path.exists(REWORK_FILE):
			save_rework(self.rework)
		self.open_path(REWORK_FILE)

	def _load_generic_pictures(self, tag, jobs):
		self._gen_job = None
		if self._generics_for != tag:
			return  # another country was picked meanwhile
		d = self.data
		t0 = time.time()
		while jobs and time.time() - t0 < 0.05:
			lab, size, name, box = jobs.pop(0)
			key = (name, box)
			if key not in self._gen_cache:  # pictures stay loaded: going back to a country is instant
				path = d.portrait_path(name)
				im = load_image(path, box) if path else None
				self._gen_cache[key] = ImageTk.PhotoImage(im) if im else None
			ph = self._gen_cache[key]
			if not lab.winfo_exists():
				continue
			if ph:
				lab.config(image=ph, text="", width=ph.width(), height=ph.height())
			else:
				self._gen_missing += 1
				lab.config(text=f"no\n{size}", fg="#b00")
		if jobs:
			self._gen_job = self.root.after(1, lambda: self._load_generic_pictures(tag, jobs))
		elif self._gen_missing:
			n = self._gen_missing
			self.gen_note.config(text=self._gen_base_note + f"  -  {n} picture{'s' if n != 1 else ''} missing (red).")

	def _build_leaders(self):
		f = ttk.Frame(self.tabs, padding=6)
		self.tabs.add(f, text="Leaders")
		top = ttk.Frame(f)
		top.pack(fill="x")
		self.lead_tree = ttk.Treeview(top, columns=("roles", "ideology", "start"), height=8, selectmode="browse")
		for col, text, w in (("#0", "Character", 150), ("roles", "Roles", 105), ("ideology", "Ideology", 125), ("start", "At start", 52)):
			self.lead_tree.heading(col, text=text)
			self.lead_tree.column(col, width=w, anchor="w" if col != "start" else "center")
		ys = ttk.Scrollbar(top, command=self.lead_tree.yview)
		self.lead_tree.config(yscrollcommand=ys.set)
		self.lead_tree.pack(side="left", fill="x", expand=True)
		ys.pack(side="left", fill="y")
		self.lead_tree.bind("<<TreeviewSelect>>", lambda ev: self.show_character())
		self.lead_tree.tag_configure("noport", foreground="#b00")  # no large portrait
		for i, colour in enumerate(REWORK_CATS.values()):
			self.lead_tree.tag_configure(f"rw_{i}", foreground=colour)  # a portrait marked for rework
		mid = ttk.Frame(f)
		mid.pack(fill="x", pady=6)
		pf = ttk.Frame(mid)
		pf.pack(side="left", anchor="n")
		self.portrait = tk.Label(pf, text="", width=16, height=8, relief="groove")
		self.portrait.pack()
		# Large / small (units, doctrines): the arrow on the picture switches between them.
		self.portrait_flip = tk.Button(self.portrait, text="▶", font=("Segoe UI", 8, "bold"), padx=3, pady=0, bd=1,
									   cursor="hand2", command=lambda: self.flip_portrait(1))
		self.portrait_kind = ttk.Label(pf, text="", foreground="#555", font=("Segoe UI", 8))
		self.portrait_kind.pack()
		self.portrait_rework = tk.Label(pf, text="", font=("Segoe UI", 8, "bold"))
		self.portrait_rework.pack()
		self.portrait.config(highlightthickness=3)
		self.portrait.bind("<Button-3>", self._leader_portrait_menu)
		self.portrait_slots, self.portrait_i = [], 0
		form = ttk.Frame(mid)
		form.pack(side="left", fill="x", expand=True, padx=8)
		self.ch_vars = {k: tk.StringVar() for k in ("name", "ideology", "expire", "traits")}
		ttk.Label(form, text="Name:").grid(row=0, column=0, sticky="w")
		ttk.Entry(form, textvariable=self.ch_vars["name"], width=30).grid(row=0, column=1, sticky="we")
		ttk.Label(form, text="Leader ideology:").grid(row=1, column=0, sticky="w")
		self.ideo_box = ttk.Combobox(form, textvariable=self.ch_vars["ideology"], width=28)
		self.ideo_box.grid(row=1, column=1, sticky="we")
		ttk.Label(form, text="Expire:").grid(row=2, column=0, sticky="w")
		ttk.Entry(form, textvariable=self.ch_vars["expire"], width=30).grid(row=2, column=1, sticky="we")
		ttk.Label(form, text="Leader traits:").grid(row=3, column=0, sticky="w")
		ttk.Entry(form, textvariable=self.ch_vars["traits"], width=30).grid(row=3, column=1, sticky="we")
		self.recruit_var = tk.BooleanVar()
		ttk.Checkbutton(form, text="Recruited at game start (recruit_character in its history)", variable=self.recruit_var).grid(
			row=4, column=0, columnspan=2, sticky="w")
		bf = ttk.Frame(form)
		bf.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))
		ttk.Button(bf, text="Save character", command=self.save_character).pack(side="left")
		ttk.Button(bf, text="New character...", command=self.new_character).pack(side="left", padx=4)
		form.columnconfigure(1, weight=1)
		ttk.Label(f, text="The whole character (everything else: generals' skills, advisor roles, portraits...):",
				  foreground="#555").pack(anchor="w")
		self.char_raw = RawEditor(f, self, height=12, on_saved=lambda: self.fill_leaders(keep=True))
		self.char_raw.pack(fill="both", expand=True)

	def fill_leaders(self, keep=False):
		d, tag = self.data, self.selected
		if not tag:
			return
		sel = self.lead_tree.selection()
		self.lead_tree.delete(*self.lead_tree.get_children())
		c = d.countries[tag]
		ids = list(c.characters) + sorted(cid for cid in d.characters if cid.startswith(tag + "_") and cid not in c.characters)
		subs = sorted(d.sub_ideology)
		self.ideo_box.config(values=subs)
		for cid in ids:
			ch = d.characters.get(cid)
			if ch is None:
				self.lead_tree.insert("", "end", iid=cid, text=f"{cid} (not defined!)", values=("", "", "yes"))
				continue
			self.lead_tree.insert("", "end", iid=cid, text=d.label(ch.name_key, cid),
								  values=(", ".join(ch.roles), " / ".join(r[0] or "?" for r in ch.leaders()), "yes" if cid in c.characters else ""),
								  tags=() if d.has_large_portrait(ch) else ("noport",))
		self._mark_leader_rows()
		if keep and sel and self.lead_tree.exists(sel[0]):
			self.lead_tree.selection_set(sel[0])
		elif ids:
			self.lead_tree.selection_set(ids[0])
		else:
			self.char_raw.show(None)

	def show_character(self):
		sel = self.lead_tree.selection()
		if not sel:
			return
		d = self.data
		ch = d.characters.get(sel[0])
		if ch is None:
			self.char_raw.show(None)
			return
		lead = ch.leader()
		self.ch_vars["name"].set(d.loc.get(ch.name_key, ""))
		self.ch_vars["ideology"].set(lead[0] if lead else "")
		self.ch_vars["expire"].set(lead[1] if lead and lead[1] else "")
		self.ch_vars["traits"].set(" ".join(lead[2]) if lead else "")
		self.recruit_var.set(ch.id in d.countries[self.selected].characters)
		self.loaded_char = {k: v.get() for k, v in self.ch_vars.items()}
		self.loaded_recruit = self.recruit_var.get()
		self.char_raw.show(ch.rel, ch.entry.first, ch.entry.last)
		self.portrait_slots = list(ch.portrait_slots)
		self.portrait_i = 0
		self.show_portrait()

	def _shown_portrait(self):
		"""(character id, (civilian/army/navy, large/small, sprite)) of the portrait on the Leaders tab, or None."""
		sel = self.lead_tree.selection()
		if not sel or not self.portrait_slots:
			return None
		return sel[0], self.portrait_slots[self.portrait_i]

	def _leader_portrait_menu(self, ev):
		shown = self._shown_portrait()
		if not shown:
			return
		cid, (typ, size, value) = shown
		menu = tk.Menu(self.root, tearoff=0)
		menu.add_command(label=f"{value} ({typ} {size})", state="disabled")
		self.rework_menu_items(menu, value, f"{cid} ({typ} {size})")
		menu.add_separator()
		menu.add_command(label="Copy the sprite name", command=lambda: (self.root.clipboard_clear(), self.root.clipboard_append(value)))
		path = self.data.portrait_path(value)
		if path:
			menu.add_command(label="Open the picture", command=lambda: self.open_path(path))
		menu.tk_popup(ev.x_root, ev.y_root)

	def _show_portrait_rework(self):
		"""The shown leader portrait: a coloured frame and its category when it is marked for rework."""
		if not hasattr(self, "portrait_rework"):
			return
		shown = self._shown_portrait()
		m = self.rework_marks().get(shown[1][2]) if shown else None
		bg = self.portrait.master.cget("background") if isinstance(self.portrait.master, tk.Frame) else ttk.Style().lookup("TFrame", "background")
		col = REWORK_CATS[m[0]] if m else bg
		self.portrait.config(highlightbackground=col, highlightcolor=col)
		self.portrait_rework.config(text=f"⚑ {m[0]}" if m else "", fg=REWORK_CATS[m[0]] if m else "#555")

	def _mark_leader_rows(self):
		"""Leaders list: a character with a portrait marked for rework gets a ⚑ (in the colour of its worst one)."""
		if not hasattr(self, "lead_tree"):
			return
		marks = self.rework_marks()
		order = list(REWORK_CATS)
		for cid in self.lead_tree.get_children():
			ch = self.data.characters.get(cid)
			cats = [marks[v][0] for _, _, v in (ch.portrait_slots if ch else []) if v in marks]
			tags = [t for t in self.lead_tree.item(cid, "tags") if not t.startswith("rw_")]
			text = self.lead_tree.item(cid, "text").removeprefix("⚑ ")
			if cats:
				worst = max(cats, key=lambda c: order.index(c) if c != "Something about it" else -1)
				tags.append("rw_" + str(order.index(worst)))
				text = "⚑ " + text
			self.lead_tree.item(cid, tags=tags, text=text)

	def flip_portrait(self, step):
		if self.portrait_slots:
			self.portrait_i = (self.portrait_i + step) % len(self.portrait_slots)
			self.show_portrait()

	def show_portrait(self):
		"""The picked portrait (large first); the arrow shows when it has more than one."""
		d = self.data
		slots = self.portrait_slots
		self._portrait = None
		kind = ""
		if slots:
			typ, size, value = slots[self.portrait_i]
			path = d.portrait_path(value)
			im = load_image(path, (156, 210)) if path else None
			if im:
				self._portrait = ImageTk.PhotoImage(im)
			kind = f"{typ} {size}" + (f"  ({self.portrait_i + 1}/{len(slots)})" if len(slots) > 1 else "")
			if not im:
				kind += f"\nmissing: {value}"
		has_large = any(s == "large" and d.portrait_path(v) for _, s, v in slots)
		text = "(no portrait)" if not slots else "(picture missing)"
		self.portrait.config(image=self._portrait or "", text="" if self._portrait else text,
							 width=156 if self._portrait else 16, height=210 if self._portrait else 8)
		self.portrait_kind.config(text=kind + ("" if has_large or not slots else "\nno large portrait (Gap Finder)"),
								  foreground="#555" if self._portrait and has_large else "#b00", wraplength=170)
		self._show_portrait_rework()
		if len(slots) > 1:
			nxt = slots[(self.portrait_i + 1) % len(slots)]
			cur = slots[self.portrait_i]
			self.portrait_flip.config(text=f"▶ {nxt[1] if nxt[1] != cur[1] else nxt[0]}")
			self.portrait_flip.place(relx=1.0, rely=1.0, x=-2, y=-2, anchor="se")
			self.portrait_flip.lift()
		else:
			self.portrait_flip.place_forget()

	def save_character(self):
		sel = self.lead_tree.selection()
		if not sel or not self.selected:
			return
		d = self.data
		ch = d.characters.get(sel[0])
		if ch is None:
			return
		now = {k: v.get().strip() for k, v in self.ch_vars.items()}
		text = self.char_raw.get()
		if now["name"] != self.loaded_char["name"]:
			self.set_loc(ch.name_key, now["name"])
		lead_changed = any(now[k] != self.loaded_char[k] for k in ("ideology", "expire", "traits"))
		if lead_changed:
			text = self._edit_leader_block(text, now)
		if text != "\n".join(TextFile(d.path(ch.rel)).lines[ch.entry.first:ch.entry.last + 1]):
			self.write_lines(ch.rel, ch.entry.first, ch.entry.last, text.split("\n"))
		if self.recruit_var.get() != self.loaded_recruit:
			self.set_recruited(self.selected, ch.id, self.recruit_var.get())
		self.fill_leaders(keep=True)
		self.set_status(f"Saved {ch.id}.")

	@staticmethod
	def _edit_leader_block(text, now):
		"""Puts ideology / expire / traits into the country_leader block of a character's text (adds one if missing)."""
		m = re.search(r"country_leader\s*=\s*\{", text)
		if not m:
			return re.sub(r"\}\s*$", "\tcountry_leader = {\n\t\t\tideology = %s\n\t\t\texpire = \"%s\"\n\t\t\tid = -1\n\t\t}\n\t}"
						  % (now["ideology"], now["expire"] or "1999.1.1.1"), text.rstrip(), count=1)
		depth, i = 0, m.end() - 1
		while i < len(text):
			if text[i] == "{":
				depth += 1
			elif text[i] == "}":
				depth -= 1
				if depth == 0:
					break
			i += 1
		inner = text[m.end():i]
		for key, val in (("ideology", now["ideology"]), ("expire", f'"{now["expire"]}"' if now["expire"] else "")):
			if re.search(r"\b%s\s*=" % key, inner):
				inner = re.sub(r"(\b%s\s*=\s*)(\"[^\"]*\"|\S+)" % key, lambda mm: mm.group(1) + val, inner, count=1) if val else inner
			elif val:
				inner = f"\n\t\t\t{key} = {val}" + inner
		traits = now["traits"].split()
		if re.search(r"\btraits\s*=\s*\{[^}]*\}", inner):
			inner = re.sub(r"(\btraits\s*=\s*\{)[^}]*\}", lambda mm: mm.group(1) + (" " + " ".join(traits) + " " if traits else " ") + "}", inner, count=1)
		elif traits:
			inner = f"\n\t\t\ttraits = {{ {' '.join(traits)} }}" + inner
		return text[:m.end()] + inner + text[i:]

	def set_recruited(self, tag, cid, on):
		d = self.data
		c = d.countries[tag]
		if not c.history:
			self.make_history(tag)
		tf = TextFile(d.path(c.history))
		lines = list(tf.lines)
		if on:
			last = max((e.last for e in c.hist if e.key == "recruit_character"), default=None)
			if last is None:
				lines += ["", "#leaders", f"recruit_character = {cid}"]
			else:
				lines.insert(last + 1, f"recruit_character = {cid}")
		else:
			lines = [l for l in lines if not re.match(r"^\s*recruit_character\s*=\s*%s\s*(#.*)?$" % re.escape(cid), l)]
		self.write_lines(c.history, None, None, lines)

	def new_character(self):
		tag = self.selected
		if not tag:
			return
		name = simpledialog.askstring(APP_NAME, f"Name of the new {tag} character (e.g. Kurt Schuschnigg):", parent=self.root)
		if not name:
			return
		cid = f"{tag}_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
		d = self.data
		if cid in d.characters:
			messagebox.showinfo(APP_NAME, f"{cid} already exists.")
			return
		ideo = f"{self.ruling(tag) or 'neutrality'}"
		subs = d.ideologies.get(ideo) or [ideo]
		block = [f"\t{cid}={{", f"\t\tname={cid}", "\t\tportraits={", "\t\t\tcivilian={", f"\t\t\t\tlarge=GFX_{cid}", "\t\t\t}", "\t\t}",
				 "\t\tcountry_leader={", f"\t\t\tideology={subs[0]}", "\t\t\texpire=\"1999.1.1.1\"", "\t\t\tid=-1", "\t\t}", "\t}"]
		rel = f"{cd.D_CHARACTERS}/{tag}.txt"
		path = d.path(rel)
		if os.path.exists(path):
			tf = TextFile(path)
			top = parse("\n".join(tf.lines))
			chars = next((e for e in top if e.key == "characters" and e.block), None)
			if chars is None:
				messagebox.showerror(APP_NAME, f"{rel} has no characters = {{ }} block.")
				return
			lines = tf.lines[:chars.last] + block + tf.lines[chars.last:]
			self.write_lines(rel, None, None, lines)
		else:
			self.touched(rel)
			path = d.mod_path(rel)
			os.makedirs(os.path.dirname(path), exist_ok=True)
			with open(path, "x", encoding="utf-8", newline="\r\n") as f:
				f.write("characters={\n" + "\n".join(block) + "\n}\n")
			self.reload_file(rel)
		self.set_loc(cid, name)
		self.set_recruited(tag, cid, True)
		self.fill_leaders()
		if self.lead_tree.exists(cid):
			self.lead_tree.selection_set(cid)
		self.set_status(f"Made {cid} in {rel} and recruited it. Its portrait sprite GFX_{cid} still needs a picture.")

	# ---------- National ideas ----------
	def _build_ideas(self):
		f = ttk.Frame(self.tabs, padding=6)
		self.tabs.add(f, text="National ideas")
		top = ttk.Frame(f)
		top.pack(fill="x")
		self.idea_tree = ttk.Treeview(top, columns=("start", "file"), height=7, selectmode="browse")
		for col, text, w in (("#0", "Idea", 200), ("start", "At start", 52), ("file", "File", 160)):
			self.idea_tree.heading(col, text=text)
			self.idea_tree.column(col, width=w)
		ys = ttk.Scrollbar(top, command=self.idea_tree.yview)
		self.idea_tree.config(yscrollcommand=ys.set)
		self.idea_tree.pack(side="left", fill="x", expand=True)
		ys.pack(side="left", fill="y")
		self.idea_tree.bind("<<TreeviewSelect>>", lambda ev: self.show_idea())
		mid = ttk.Frame(f)
		mid.pack(fill="x", pady=6)
		self.idea_pic = tk.Label(mid, text="", width=10, height=5, relief="groove")
		self.idea_pic.pack(side="left")
		form = ttk.Frame(mid)
		form.pack(side="left", fill="x", expand=True, padx=8)
		self.idea_vars = {"name": tk.StringVar(), "desc": tk.StringVar()}
		ttk.Label(form, text="Name:").grid(row=0, column=0, sticky="w")
		ttk.Entry(form, textvariable=self.idea_vars["name"]).grid(row=0, column=1, sticky="we")
		ttk.Label(form, text="Description:").grid(row=1, column=0, sticky="w")
		ttk.Entry(form, textvariable=self.idea_vars["desc"]).grid(row=1, column=1, sticky="we")
		self.idea_start = tk.BooleanVar()
		ttk.Checkbutton(form, text="Starts with it (add_ideas in its history)", variable=self.idea_start).grid(row=2, column=0, columnspan=2, sticky="w")
		bf = ttk.Frame(form)
		bf.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))
		ttk.Button(bf, text="Save idea", command=self.save_idea).pack(side="left")
		ttk.Button(bf, text="Add an idea it starts with...", command=self.add_start_idea).pack(side="left", padx=4)
		form.columnconfigure(1, weight=1)
		ttk.Label(f, text="The whole idea (modifiers, allowed, picture...):", foreground="#555").pack(anchor="w")
		self.idea_raw = RawEditor(f, self, height=12, on_saved=lambda: self.fill_ideas(keep=True))
		self.idea_raw.pack(fill="both", expand=True)

	def fill_ideas(self, keep=False):
		d, tag = self.data, self.selected
		if not tag:
			return
		sel = self.idea_tree.selection()
		self.idea_tree.delete(*self.idea_tree.get_children())
		c = d.countries[tag]
		names = list(dict.fromkeys(d.country_ideas(tag) + [i for i in c.ideas if i not in d.ideas]))  # once each
		for n in names:
			idea = d.ideas.get(n)
			self.idea_tree.insert("", "end", iid=n, text=d.label(n, n), values=("yes" if n in c.ideas else "",
																				   idea.rel if idea else "(not defined!)"))
		if keep and sel and self.idea_tree.exists(sel[0]):
			self.idea_tree.selection_set(sel[0])
		elif names:
			self.idea_tree.selection_set(names[0])
		else:
			self.idea_raw.show(None)
			self.idea_pic.config(image="", text="(none)", width=10, height=5)

	def show_idea(self):
		sel = self.idea_tree.selection()
		if not sel:
			return
		d = self.data
		n = sel[0]
		idea = d.ideas.get(n)
		self.idea_vars["name"].set(d.loc.get(n, ""))
		self.idea_vars["desc"].set(d.loc.get(n + "_desc", ""))
		self.idea_start.set(n in d.countries[self.selected].ideas)
		self.loaded_idea = ({k: v.get() for k, v in self.idea_vars.items()}, self.idea_start.get())
		if idea:
			self.idea_raw.show(idea.rel, idea.entry.first, idea.entry.last)
		else:
			self.idea_raw.show(None)
		self._idea_photo = None
		pic = idea.picture if idea else None
		for sprite in ([f"GFX_idea_{pic}", pic] if pic else []) + [f"GFX_idea_{n}"]:
			path = d.sprite_texture(sprite) if sprite else None
			im = load_image(path, (128, 128)) if path else None
			if im:
				self._idea_photo = ImageTk.PhotoImage(im)
				break
		if self._idea_photo:
			self.idea_pic.config(image=self._idea_photo, text="", width=self._idea_photo.width(), height=self._idea_photo.height())
		else:
			self.idea_pic.config(image="", text="(no picture)", width=10, height=5)

	def save_idea(self):
		sel = self.idea_tree.selection()
		if not sel or not self.selected:
			return
		n = sel[0]
		names, start = self.loaded_idea
		if self.idea_vars["name"].get().strip() != names["name"]:
			self.set_loc(n, self.idea_vars["name"].get().strip())
		if self.idea_vars["desc"].get().strip() != names["desc"]:
			self.set_loc(n + "_desc", self.idea_vars["desc"].get().strip())
		idea = self.data.ideas.get(n)
		if idea:
			lines = TextFile(self.data.path(idea.rel)).lines
			if self.idea_raw.get() != "\n".join(lines[idea.entry.first:idea.entry.last + 1]):
				self.idea_raw.save()
		if self.idea_start.get() != start:
			self.set_start_idea(self.selected, n, self.idea_start.get())
		self.fill_ideas(keep=True)
		self.set_status(f"Saved {n}.")

	def set_start_idea(self, tag, idea, on):
		d = self.data
		c = d.countries[tag]
		if not c.history:
			self.make_history(tag)
		lines = list(TextFile(d.path(c.history)).lines)
		blocks = [e for e in c.hist if e.key == "add_ideas"]
		if on:
			b = next((e for e in blocks if e.block), None)
			if b is None:
				lines += ["", "add_ideas = {", f"\t{idea}", "}"]
			else:
				lines.insert(b.last, f"\t{idea}")
		else:
			for b in blocks:
				for i in range(b.first, b.last + 1):
					stripped = strip_comment(lines[i])
					if re.search(r"(?<![\w])%s(?![\w])" % re.escape(idea), stripped):
						if stripped.strip() == idea:
							lines[i] = None
						else:
							lines[i] = re.sub(r"(?<![\w])%s(?![\w])" % re.escape(idea), "", lines[i], count=1)
						break
			lines = [l for l in lines if l is not None]
		self.write_lines(c.history, None, None, lines)

	def add_start_idea(self):
		tag = self.selected
		if not tag:
			return
		name = simpledialog.askstring(APP_NAME, "Idea token to start with (any idea in common/ideas):", parent=self.root)
		if not name:
			return
		name = name.strip()
		if name not in self.data.ideas and not messagebox.askyesno(APP_NAME, f"{name} isn't an idea in common/ideas. Add it anyway?"):
			return
		self.set_start_idea(tag, name, True)
		self.fill_ideas()
		self.set_status(f"Saved {tag}: starts with {name}.")

	# ---------- OOB ----------
	def _build_oob(self):
		f = ttk.Frame(self.tabs, padding=6)
		self.tabs.add(f, text="OOB")
		row = ttk.Frame(f)
		row.pack(fill="x")
		ttk.Label(row, text="oob = ").pack(side="left")
		self.oob_var = tk.StringVar()
		self.oob_box = ttk.Combobox(row, textvariable=self.oob_var, width=24)
		self.oob_box.pack(side="left")
		ttk.Button(row, text="Use this OOB", command=self.save_oob_name).pack(side="left", padx=4)
		ttk.Button(row, text="Make its own OOB file", command=self.make_own_oob).pack(side="left")
		self.oob_info = ttk.Label(f, text="", foreground="#555", wraplength=520, justify="left")
		self.oob_info.pack(fill="x", pady=4)
		self.oob_raw = RawEditor(f, self, height=24)
		self.oob_raw.pack(fill="both", expand=True)

	def fill_oob(self):
		d, tag = self.data, self.selected
		c = d.countries[tag]
		files = sorted(os.path.splitext(os.path.basename(p))[0] for p in os.listdir(d.path(cd.D_UNITS)) if p.endswith(".txt"))
		self.oob_box.config(values=files)
		self.oob_var.set(c.oob or "")
		users = sum(1 for x in d.countries.values() if x.oob == c.oob) if c.oob else 0
		rel = f"{cd.D_UNITS}/{c.oob}.txt" if c.oob else None
		if c.oob and os.path.exists(d.path(rel)):
			text = read_text(d.path(rel))
			info = (f"{rel}: {text.count('division_template')} division templates, {len(re.findall(r'\bdivision\s*=', text))} divisions, "
					f"{len(re.findall(r'\bship\s*=', text))} ships.")
			if users > 1:
				info += f" Shared by {users} countries - changes here change all of them (use 'Make its own OOB file')."
			self.oob_info.config(text=info)
			self.oob_raw.show(rel)
		else:
			self.oob_info.config(text="No OOB file." if not c.oob else f"{rel} doesn't exist.")
			self.oob_raw.show(None)

	def save_oob_name(self):
		tag = self.selected
		if not tag:
			return
		name = self.oob_var.get().strip()
		was = self.data.countries[tag].oob or ""
		if name and name != was:
			self.save_history_values(tag, {"oob": f'"{name}"'}, {"oob": was})
			self.fill_oob()
			self.set_status(f"Saved {tag}: oob = \"{name}\".")

	def make_own_oob(self):
		tag = self.selected
		if not tag:
			return
		d = self.data
		c = d.countries[tag]
		dst = f"{cd.D_UNITS}/{tag}.txt"
		if os.path.exists(d.path(dst)):
			messagebox.showinfo(APP_NAME, f"{dst} already exists; pick {tag} in the box and press 'Use this OOB'.")
			return
		src = d.path(f"{cd.D_UNITS}/{c.oob}.txt") if c.oob else None
		self.touched(dst)
		os.makedirs(os.path.dirname(d.mod_path(dst)), exist_ok=True)
		if src and os.path.exists(src):
			shutil.copy2(src, d.mod_path(dst))
		else:
			open(d.mod_path(dst), "w", encoding="utf-8").write("units = {\n}\n")
		self.oob_var.set(tag)
		self.save_oob_name()

	# ---------- History (raw) ----------
	def _build_history(self):
		f = ttk.Frame(self.tabs, padding=6)
		self.tabs.add(f, text="History file")
		ttk.Label(f, text="Everything the country starts with (the Overview, Leaders and Ideas tabs edit parts of this):",
				  foreground="#555").pack(anchor="w")
		self.hist_raw = RawEditor(f, self, height=30, on_saved=lambda: self.select(self.selected))
		self.hist_raw.pack(fill="both", expand=True)

	def fill_history(self):
		self.hist_raw.show(self.data.countries[self.selected].history)

	# ---------- Spawn ----------
	def _build_spawn(self):
		f = ttk.Frame(self.tabs, padding=6)
		self.tabs.add(f, text="How it appears")
		self.spawn_events_title = ttk.Label(f, text="", font=("Segoe UI", 9, "bold"))
		self.spawn_events_title.pack(anchor="w")
		ef = ttk.Frame(f)
		ef.pack(fill="x", pady=(2, 6))
		self.spawn_events = ttk.Treeview(ef, columns=("gives", "file"), height=6, selectmode="browse")
		self.spawn_events.heading("#0", text="Event (option)")
		self.spawn_events.heading("gives", text="Gives it")
		self.spawn_events.heading("file", text="File")
		self.spawn_events.column("#0", width=250)
		self.spawn_events.column("gives", width=110)
		self.spawn_events.column("file", width=120)
		ys = ttk.Scrollbar(ef, command=self.spawn_events.yview)
		self.spawn_events.config(yscrollcommand=ys.set)
		self.spawn_events.pack(side="left", fill="x", expand=True)
		ys.pack(side="left", fill="y")
		self.spawn_events.tag_configure("on", foreground="#1b6a1b", font=("Segoe UI", 9, "bold"))
		self.spawn_events.bind("<Double-1>", lambda ev: self._spawn_event_row(ev, "toggle"))
		self.spawn_events.bind("<Button-3>", lambda ev: self._spawn_event_row(ev, "menu"))
		self.spawn_events_hint = ttk.Label(f, text="Double-click an event (or right-click > Launch) to see it on the map; "
											"again to switch it off.", foreground="#777", wraplength=420)
		self.spawn_events_hint.pack(anchor="w")
		self.spawn_text = tk.Text(f, wrap="word", font=("Segoe UI", 9), height=24)
		self.spawn_text.pack(fill="both", expand=True)

	def events_making(self, tag):
		return [x for x in self.data.event_spawns if tag in x.tags]

	def event_states(self, x, tag=None):
		"""States an event gives (to tag, or to anyone) when it is the only thing switched on."""
		own = self.data.simulate([x])
		return sorted(s for s, t in own.items() if self.data.state_owner.get(s) != t and (tag is None or t == tag))

	def _spawn_event_row(self, ev, what):
		row = self.spawn_events.identify_row(ev.y)
		x = next((y for y in self.data.event_spawns if y.key == row), None)
		if x is None:
			return
		self.spawn_events.selection_set(row)
		if what == "toggle":
			self.toggle_decision(x)
			return
		menu = tk.Menu(self.root, tearoff=0)
		self.event_menu_items(menu, x)
		menu.tk_popup(ev.x_root, ev.y_root)

	def event_menu_items(self, menu, x, label=None):
		on = x in self.active
		menu.add_command(label=label or (("Switch off " if on else "Launch ") + self.dec_label(x)), command=lambda: self.toggle_decision(x))
		states = self.event_states(x)
		if states:
			self._show_on_map_items(menu, ("event", x.key), lambda: set(states), self.dec_label(x))
		menu.add_command(label=f"Open the event file ({x.rel.split('/')[-1]})", command=lambda: self.open_path(self.data.path(x.rel)))

	def fill_spawn(self):
		d, tag = self.data, self.selected
		c = d.countries[tag]
		out = []
		if c.states:
			out.append(f"On the map at game start with {len(c.states)} states: "
					   + ", ".join(f"{d.state_names.get(s, s)} ({s})" for s in sorted(c.states)[:40]) + (" ..." if len(c.states) > 40 else ""))
		else:
			out.append("Not on the map at game start.")
		evs = self.events_making(tag)
		t = self.spawn_events
		t.delete(*t.get_children())
		self.spawn_events_title.config(text=f"Events that can make it ({len(evs)})" if evs else "No event makes it.")
		for x in evs:
			n = len(self.event_states(x, tag))
			mine = [s_ for s_, t_ in list(x.transfers.items()) + list(x.core_adds.items()) if t_ == tag]
			gives = f"{n} state{'s' if n != 1 else ''}" if n else ("states (unclear which)" if tag in x.vague else
											f"{len(set(mine))} states (its own at start)" if mine and all(d.state_owner.get(s_) == tag for s_ in mine)
											else "cores only" if mine else "releases it")
			t.insert("", "end", iid=x.key, text=("● " if x in self.active else "") + self.dec_label(x),
					 values=(gives, x.rel.split("/")[-1]), tags=("on",) if x in self.active else ())
		if evs:
			out.append(f"Can spawn by event: {len(evs)} event{'s' if len(evs) != 1 else ''} / option{'s' if len(evs) != 1 else ''} "
					   "(list above).")
		decs = [x for x in d.decisions if tag in x.tags]
		for x in decs:
			states = sorted(s for s, t in d.simulate([x]).items() if t == tag)
			out.append(f"\n{x.kind}: {self.dec_label(x)} ({x.name})  ->  {len(states)} states"
					   + (f"; collapses {', '.join(sorted(x.collapsing))}" if x.collapsing else "")
					   + (f"; events {', '.join(x.events)}" if x.events else ""))
		for x in d.decisions:
			if tag in x.collapsing and x not in decs:
				out.append(f"\nCollapses in {x.kind}: {self.dec_label(x)} (makes {', '.join(sorted(x.tags))})")
		if c.cores:
			out.append(f"\nHas cores on {len(c.cores)} states (a collapse or release of their owner can make it): "
					   + ", ".join(f"{d.state_names.get(s, s)} ({s})" for s in sorted(c.cores)[:40]))
		if d.scripted.get(tag):
			out.append("\nScript that can bring it in (release / release_puppet / add_core_of / transfer_state):\n    "
					   + "\n    ".join(sorted(d.scripted[tag])[:30]))
		if not c.history:
			out.append("\nIt has no history file: it starts with no leaders, ideas or politics of its own.")
		self.spawn_text.config(state="normal")
		self.spawn_text.delete("1.0", "end")
		self.spawn_text.insert("1.0", "\n".join(out))
		self.spawn_text.config(state="disabled")

	# ---------- map ----------
	def recompute(self):
		"""State owners with the switched-on collapses / bombs (and the one being previewed)."""
		prev = getattr(self, "preview", None)
		self.owner = self.data.simulate(self.active + ([prev] if prev else []))
		self.counts, self.pops = {}, {}
		for sid, t in self.owner.items():
			self.counts[t] = self.counts.get(t, 0) + 1
			self.pops[t] = self.pops.get(t, 0) + self.data.state_pop.get(sid, 0)
		# What changed hands because of the collapses / bombs (outlined on the map).
		self.changed = {s for s, t in self.owner.items() if self.data.state_owner.get(s) != t}
		self.rebuild_lut()

	def state_color(self, sid):
		d = self.data
		tag = self.owner.get(sid)
		mode = self.map_mode.get()
		if mode == "cores":
			if not self.selected:
				return UNOWNED
			if sid in d.countries[self.selected].cores or any(x.core_adds.get(sid) == self.selected for x in self.active):
				base = tag_color(self.selected, d.map_rgb(self.selected))
				return base if tag == self.selected else tuple(int(c * 0.6 + 60) for c in base)
			return (60, 60, 60)
		if not tag:
			return UNOWNED
		if mode == "continent":
			cont = self.data.state_continent.get(sid, "")
			h = (sum(map(ord, cont)) * 37 % 360) / 360
			r, g, b = colorsys.hsv_to_rgb(h, 0.5, 0.85)
			return int(r * 255), int(g * 255), int(b * 255)
		if mode == "subideology":
			if not tag:
				return UNOWNED
			main, sub = self.sub_ideology_of(tag)
			hl = getattr(self, "sub_highlight", None) if self.layer.get() == "subs" else None
			if hl and sub != hl:  # a sub-ideology picked in the list: the others go grey
				base = d.sub_rgb(sub) if sub in d.subs else (55, 55, 55)
				g = int(sum(base) / 3 * 0.25 + 45)
				return (g, g, g)
			if hl and sub == hl:
				return tuple(min(255, int(c * 1.25 + 30)) for c in d.sub_rgb(sub))
			if sub in d.subs:
				return d.sub_rgb(sub)
			# A leader with an ideology that isn't a type (or none at all): the ideology's colour, darker.
			lead = d.leader_for(tag, main) if main in self.data.mains else None
			return tuple(int(c * 0.5) for c in self.main_color(main)) if lead or main in self.data.mains else (55, 55, 55)
		if mode == "strength":
			return self.strength_color(tag)
		if mode == "ideology" and self.view_var.get() != VIEW_START:
			main = self.view_main(tag) if tag else None
			if not tag or not d.leader_for(tag, main):
				return (55, 55, 55)
			return self.main_color(main)
		if mode == "ideology":
			ideo = self.ruling(tag)
			return self.main_color(ideo) if ideo else (90, 90, 90)
		return tag_color(tag, d.map_rgb(tag) if tag in d.countries else None)

	def strength_color(self, tag):
		"""Brush strength: how popular the selected (sub-)ideology is in the owner (its set_popularities). A
		sub-ideology only counts where the owner's leader for that ideology has it."""
		d = self.data
		sel = getattr(self, "sub_selected", None)
		if not tag or not sel:
			return (55, 55, 55) if tag else UNOWNED
		if sel in self.data.mains:
			main, base = sel, self.main_color(sel)
		else:
			st = d.subs.get(sel)
			if not st:
				return (55, 55, 55)
			main, base = st.main, d.sub_rgb(sel)
			lead = d.leader_for(tag, main)
			if not lead or d.lead_sub(lead, main) != sel:
				return (45, 45, 45)
		p = max(0.0, min(100.0, d.popularity(tag, main))) / 100
		if p <= 0:
			return (45, 45, 45)
		t = 0.2 + 0.8 * p
		return tuple(int(35 * (1 - t) + c * t) for c in base)

	def rebuild_lut(self):
		if not hasattr(self, "owner"):
			return
		lut = np.empty((65536, 3), dtype=np.uint8)
		lut[:] = NO_STATE
		lut[0] = WATER
		olut = np.zeros(65536, dtype=np.int32)
		ids = {t: i + 1 for i, t in enumerate(sorted(set(self.owner.values())))}
		for sid in self.map.land_states:
			if 0 < sid < 65535:
				lut[sid] = self.state_color(sid)
				olut[sid] = ids.get(self.owner.get(sid), 0)
		self.lut = lut
		self.owner_lut = olut
		self.schedule_render()

	def schedule_render(self):
		if not self._render_pending:
			self._render_pending = True
			self.root.after_idle(self.render)

	def render(self):
		self._render_pending = False
		if self.zoom is None or not hasattr(self, "lut") or not self.canvas.winfo_exists():
			return  # (no canvas any more: another mod was opened in this window)
		w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
		if w < 2 or h < 2:
			return
		mw, mh = self.map.width, self.map.height
		xs = ((self.ox + (np.arange(w) + 0.5) / self.zoom).astype(np.int64)) % mw
		yf = self.oy + (np.arange(h) + 0.5) / self.zoom
		inside = (yf >= 0) & (yf < mh)
		ys = np.clip(yf.astype(np.int64), 0, mh - 1)
		ix = np.ix_(ys, xs)
		st = self.map.stmap[ix]
		img = self.lut[st]
		if self.zoom >= 0.5:
			b = self.map.border[ix]
			img[b] = (img[b] * 0.7).astype(np.uint8)
		# Country borders (where the owner changes) in dark lines, so a collapse shows even in similar colours.
		own = self.owner_lut[st]
		cb = np.zeros(st.shape, dtype=bool)
		cb[:, :-1] |= own[:, :-1] != own[:, 1:]
		cb[:-1, :] |= own[:-1, :] != own[1:, :]
		img[cb & (st > 0)] = (20, 20, 20)
		if self.changed and self.map_mode.get() == "owner":
			# States that changed hands (switched-on collapses / bombs, or the preview) get a light hatch.
			m = np.isin(st, list(self.changed))
			hatch = ((np.add.outer(np.arange(st.shape[0]), np.arange(st.shape[1])) // 3) % 4 == 0)
			img[m & hatch] = (img[m & hatch] * 0.5 + 127).astype(np.uint8)
		if self.selected and self.map_mode.get() == "owner" and not getattr(self, "preview", None):
			mine = [s for s, t in self.owner.items() if t == self.selected]
			if mine:
				m = np.isin(st, mine)
				land = st > 0
				img[land & ~m] = (img[land & ~m] * 0.55 + 25).astype(np.uint8)
		if self.selected_state:
			m = st == self.selected_state
			img[m] = (img[m] * 0.5 + 127).astype(np.uint8)
		if self.highlight:  # Show on map
			m = np.isin(st, list(self.highlight))
			img[m] = (img[m] * 0.55 + np.array([255, 230, 90]) * 0.45).astype(np.uint8)
		img[~inside] = (29, 38, 51)
		self.photo = ImageTk.PhotoImage(Image.fromarray(img))
		self.canvas.itemconfig(self.canvas_img, image=self.photo)

	def fit_map(self):
		w = self.canvas.winfo_width()
		if w < 10:
			self.root.after(100, self.fit_map)
			return
		try:  # the country side starts narrow; drag the divider to make it wider
			self.pw.sashpos(1, self.pw.winfo_width() - 470)
			self.root.update_idletasks()
			w = self.canvas.winfo_width()
		except tk.TclError:
			pass
		h = self.canvas.winfo_height()
		# The whole height of the map, centred on Europe (where most countries are).
		self.zoom = max(0.12, h / self.map.height)
		self.ox = self.map.width * 0.52 - w / 2 / self.zoom
		self.oy = 0
		self.render()

	def zoom_to_points(self, pts):
		xs, ys = [p[0] for p in pts], [p[1] for p in pts]
		w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
		span = max((max(xs) - min(xs) + 200) / w, (max(ys) - min(ys) + 200) / h)
		self.zoom = min(4.0, max(0.12, 1 / span))
		self.ox = (min(xs) + max(xs)) / 2 - w / 2 / self.zoom
		self.oy = (min(ys) + max(ys)) / 2 - h / 2 / self.zoom
		self.render()

	def zoom_to_tags(self, tags, dec=None, quiet=False):
		if dec and dec not in self.active:
			self.toggle_decision(dec)
		pts = [self.map.centroids[s] for s, t in self.owner.items() if t in tags and s in self.map.centroids]
		if not pts:
			if not quiet:
				self.set_status("Not on the map" + (" (switch its collapse / bomb on)." if not dec else "."))
			return
		xs, ys = [p[0] for p in pts], [p[1] for p in pts]
		w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
		span = max((max(xs) - min(xs) + 200) / w, (max(ys) - min(ys) + 200) / h)
		self.zoom = min(4.0, max(0.12, 1 / span))
		self.ox = (min(xs) + max(xs)) / 2 - w / 2 / self.zoom
		self.oy = (min(ys) + max(ys)) / 2 - h / 2 / self.zoom
		self.render()

	def show_country_on_map(self, tag):
		"""Moves the map to a country picked in the list (zooms out / in only when it doesn't fit)."""
		pts = [self.map.centroids[s] for s, t in self.owner.items() if t == tag and s in self.map.centroids]
		if not pts or self.zoom is None:
			return
		xs, ys = [p[0] for p in pts], [p[1] for p in pts]
		w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
		need = min(4.0, max(0.12, 1 / max((max(xs) - min(xs) + 200) / w, (max(ys) - min(ys) + 200) / h)))
		if need < self.zoom or self.zoom < need / 4:
			self.zoom = need
		self.ox = (min(xs) + max(xs)) / 2 - w / 2 / self.zoom
		self.oy = (min(ys) + max(ys)) / 2 - h / 2 / self.zoom
		self.render()

	def state_at(self, x, y):
		mx = int(self.ox + x / self.zoom) % self.map.width
		my = int(self.oy + y / self.zoom)
		if 0 <= my < self.map.height:
			s = int(self.map.stmap[my, mx])
			if 0 < s < 65535:
				return s
		return None

	def on_wheel(self, ev):
		if self.zoom is None:
			return
		f = 1.25 if ev.delta > 0 else 0.8
		nz = min(8.0, max(0.12, self.zoom * f))
		mx = self.ox + ev.x / self.zoom
		my = self.oy + ev.y / self.zoom
		self.zoom = nz
		self.ox = mx - ev.x / nz
		self.oy = my - ev.y / nz
		self.render()

	def on_pan_start(self, ev):
		self.pan_start = (ev.x, ev.y, self.ox, self.oy)

	def on_pan(self, ev):
		if self.pan_start:
			x0, y0, ox, oy = self.pan_start
			self.ox = ox - (ev.x - x0) / self.zoom
			self.oy = oy - (ev.y - y0) / self.zoom
			self.render()

	def on_click(self, ev):
		sid = self.state_at(ev.x, ev.y)
		if sid is None:
			return
		self.selected_state = sid
		tag = self.owner.get(sid)
		if tag not in self.data.countries:
			self.render()
			return
		if self.layer.get() == "subs":
			return self.pick_country_sub(tag)
		self.select(tag)
		if self.map_mode.get() in ("subideology", "ideology"):
			self.say_sub(tag)

	def say_sub(self, tag):
		d = self.data
		main, sub = self.sub_ideology_of(tag)
		lead = d.leader_for(tag, main) if main in self.data.mains else None
		who = d.label(lead.name_key, lead.id) if lead else "no leader"
		self.set_status(f"{d.name(tag, self.ruling(tag))} ({tag}): {d.label(main, main)} - {who}: "
						f"{d.label(sub, sub)} ({sub})")

	def pick_country_sub(self, tag):
		"""Sub-ideologies layer: a click on the map opens the sub-ideology of that country (in the View) on the
		right, without changing the map."""
		d = self.data
		main, sub = self.sub_ideology_of(tag)
		self.say_sub(tag)
		self.picked_country = tag
		if sub in d.subs:
			iid = f"ityp:{sub}"
			if not self.tree.exists(iid):
				self.sub_gap_var.set(GAP_ALL)
				self.search_var.set("")
				self.rebuild_sub_tree()
			# The select event comes later and must leave the map alone (only when the row changes).
			self._keep_map = self.tree.selection() != (iid,)
			self.tree.selection_set(iid)
			self.tree.see(iid)
			self.fill_sub(sub)
		self.render()

	def on_right_release(self, ev):
		if self.pan_start and abs(ev.x - self.pan_start[0]) + abs(ev.y - self.pan_start[1]) > 4:
			return
		sid = self.state_at(ev.x, ev.y)
		if sid is None:
			return
		d = self.data
		menu = tk.Menu(self.root, tearoff=0)
		menu.add_command(label=f"{d.state_names.get(sid, sid)} (state {sid})", state="disabled")
		if self.highlight:
			menu.add_command(label=f"Clear Show on map ({self.highlight_label})", command=self.clear_highlight)
		tag = self.owner.get(sid)
		if tag:
			menu.add_command(label=f"Owner: {d.name(tag, self.ruling(tag))} ({tag})", command=lambda: self.select(tag))
		cores = sorted(d.state_cores.get(sid, ()))
		for t in cores:
			if t != tag:
				menu.add_command(label=f"Core of {d.name(t)} ({t})", command=lambda t=t: self.select(t))
		for x in d.decisions:
			if sid in x.core_adds or sid in x.transfers:
				t = x.core_adds.get(sid) or x.transfers.get(sid)
				on = x in self.active
				menu.add_command(label=f"{'Switch off' if on else 'Switch on'} {self.dec_label(x)} (gives it to {t})",
								 command=lambda x=x: self.toggle_decision(x))
		# Events that make a country with this state.
		evs = []
		for x in d.event_spawns:
			t = x.transfers.get(sid) or x.core_adds.get(sid) or next(
				(r for ts in x.releases.values() for r in ts if r in d.state_cores.get(sid, ())), None)
			if t:
				evs.append((x, t))
		if evs:
			menu.add_separator()
			sub = tk.Menu(menu, tearoff=0) if len(evs) > 8 else menu
			for x, t in evs:
				on = x in self.active
				sub.add_command(label=f"{'Switch off' if on else 'Launch'} {self.dec_label(x)} (makes {d.name(t) + ' - ' if d.name(t) != t else ''}{t})",
								command=lambda x=x: self.toggle_decision(x))
			if sub is not menu:
				menu.add_cascade(label=f"Launch an event that makes a country here ({len(evs)})", menu=sub)
		if sid in d.state_files:
			menu.add_separator()
			menu.add_command(label="Open the state's file", command=lambda: self.open_path(d.path(d.state_files[sid])))
		menu.tk_popup(ev.x_root, ev.y_root)

	def on_motion(self, ev):
		if self.zoom is None:
			return
		sid = self.state_at(ev.x, ev.y)
		if sid is None:
			return
		tag = self.owner.get(sid)
		d = self.data
		self.set_status(f"{d.state_names.get(sid, sid)} ({sid})  -  {d.name(tag, self.ruling(tag)) if tag else 'no owner'}"
						+ (f" ({tag})" if tag else ""))

	# ---------- misc ----------
	def show_changes(self):
		"""Everything saved this session (newest first) with the files it wrote. Double-click to go back to it."""
		w = tk.Toplevel(self.root)
		w.title("Recent changes")
		w.transient(self.root)
		w.geometry(f"760x520+{self.root.winfo_rootx() + 200}+{self.root.winfo_rooty() + 80}")
		f = ttk.Frame(w, padding=8)
		f.pack(fill="both", expand=True)
		ttk.Label(f, text="Country Master writes to the files when you press a Save button. Old files are in "
						  "tools/country_master/backups/<time>. Double-click an entry to go back to it.", foreground="#555",
				  wraplength=720).pack(anchor="w")
		box = ttk.Frame(f)
		box.pack(fill="both", expand=True, pady=4)
		t = ttk.Treeview(box, columns=("when",), selectmode="browse")
		t.heading("#0", text="Change")
		t.heading("when", text="When")
		t.column("#0", width=620)
		t.column("when", width=80, anchor="center")
		ys = ttk.Scrollbar(box, command=t.yview)
		t.config(yscrollcommand=ys.set)
		t.pack(side="left", fill="both", expand=True)
		ys.pack(side="left", fill="y")
		targets = {}
		if not self.change_log:
			t.insert("", "end", text="Nothing saved yet this session.")
		for i, (when, text, files, target) in enumerate(reversed(self.change_log)):
			iid = f"c{i}"
			t.insert("", "end", iid=iid, text=text, values=(when,), open=False)
			targets[iid] = target
			for rel in files:
				t.insert(iid, "end", text=rel)

		def jump(ev):
			row = t.identify_row(ev.y)
			target = targets.get(row) or targets.get(t.parent(row))
			if not target:
				return
			kind, value = target
			if kind == "tag" and value in self.data.countries:
				if self.layer.get() != "countries":
					self.layer.set("countries")
					self.switch_layer()
				self.select(value)
			elif kind == "sub" and value in self.data.subs:
				if self.layer.get() != "subs":
					self.layer.set("subs")
					self.switch_layer()
				iid = f"ityp:{value}"
				if self.tree.exists(iid):
					self.tree.selection_set(iid)
					self.tree.see(iid)
		t.bind("<Double-1>", jump)
		ttk.Button(f, text="Close", command=w.destroy).pack(side="right")

	def reload_all(self):
		self.set_status("Reloading...")
		self.root.update()
		self.data = CountryData(self.mod_root, self.data.game)
		self._gen_cache = {}  # pictures may have changed on disk
		keys = {x.key for x in self.active}
		self.active = [x for x in self.data.decisions + self.data.event_spawns if x.key in keys]
		self._flags.clear()
		self.recompute()
		self.rebuild_tree()
		if self.selected in self.data.countries:
			self.select(self.selected)
		self.set_status("Reloaded from disk.")

	def show_warnings(self):
		w = self.data.warnings
		messagebox.showinfo(APP_NAME, "\n".join(w[:60]) if w else "Nothing found.")

	def open_other_mod(self):
		d = pick_mod_folder(self.root)
		if not d:
			return
		save_config(mod_root=d)
		# Switch in this window (a restarted one-file exe would share the old one's temp folder).
		if self._tree_job:
			self.root.after_cancel(self._tree_job)
		self._render_pending = True  # no more renders for the old map
		root = self.root
		for w in root.winfo_children():
			w.destroy()
		root.config(menu="")
		App(root, d)

	def open_culture_master(self):
		base = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)))
		exe = os.path.join(base, "culture_master", "CultureMaster.exe")
		script = os.path.join(base, "culture_master", "culture_master.py")
		if os.path.exists(exe):
			subprocess.Popen([exe, self.mod_root], env=clean_env())
		elif os.path.exists(script):
			subprocess.Popen([sys.executable, script, self.mod_root], env=clean_env())
		else:
			messagebox.showerror(APP_NAME, "Culture Master isn't next to this tool (tools/culture_master).")


CONFIG = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "CountryMaster", "config.json")


def clean_env():
	"""Environment for starting the other tool: a fresh one-file exe (not tied to this one's temp folder)."""
	env = dict(os.environ)
	env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
	for k in list(env):
		if k.startswith("_MEIPASS") or k.startswith("_PYI_"):
			del env[k]
	return env


def load_config():
	try:
		return json.load(open(CONFIG, encoding="utf-8"))
	except Exception:
		return {}


def save_config(**kw):
	cfg = load_config()
	cfg.update(kw)
	os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
	json.dump(cfg, open(CONFIG, "w", encoding="utf-8"), indent=1)


def is_mod(d):
	"""Any HOI4 mod folder: it has a descriptor.mod, or the usual folders."""
	return bool(d) and os.path.isdir(d) and (os.path.isfile(os.path.join(d, "descriptor.mod")) or
											 os.path.isdir(os.path.join(d, "common")) or os.path.isdir(os.path.join(d, "history")))


def pick_mod_folder(parent=None):
	d = filedialog.askdirectory(parent=parent, title="Pick the mod folder (the one with descriptor.mod, common, history...)")
	if d and not is_mod(d):
		messagebox.showerror(APP_NAME, "That folder doesn't look like a HOI4 mod (no descriptor.mod, common or history folder).")
		return None
	return d or None


def find_mod_root(argv):
	"""The mod to open: the folder given on the command line, the mod this tool sits in, the last one opened, or
	one picked by hand."""
	if len(argv) > 1 and is_mod(argv[1]):
		return os.path.abspath(argv[1])
	base = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
	d = base
	for _ in range(6):
		if os.path.isfile(os.path.join(d, "descriptor.mod")):
			return d
		d = os.path.dirname(d)
	saved = load_config().get("mod_root")
	if is_mod(saved):
		return saved
	d = pick_mod_folder()
	if d:
		save_config(mod_root=d)
	return d


def find_game_dir(mod_root):
	"""The base game (hoi4.exe): the usual Steam folders, the last one used, or picked by hand (once)."""
	g = cd.find_game(mod_root) or load_config().get("game")
	if g and os.path.isfile(os.path.join(g, "hoi4.exe")):
		return g
	if messagebox.askyesno(APP_NAME, "Where is Hearts of Iron IV installed? Country Master reads the base game for whatever "
									 "the mod doesn't change.\n\nPick the folder with hoi4.exe now? (No: only the mod's own files)"):
		g = filedialog.askdirectory(title="Pick the Hearts of Iron IV folder (with hoi4.exe)")
		if g and os.path.isfile(os.path.join(g, "hoi4.exe")):
			save_config(game=g)
			return g
	return None


def main():
	root = tk.Tk()
	try:
		root.iconbitmap(os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "country_master.ico"))
	except Exception:
		pass
	mod = find_mod_root(sys.argv)
	if not mod:
		root.destroy()
		return
	App(root, mod)
	root.mainloop()


if __name__ == "__main__":
	main()
