# ONDA Doc / onda-help — Agent Handoff Document

**Last updated:** 2026-09-02
**Repo:** https://github.com/david78737/onda-help
**Live site:** https://david78737.github.io/onda-help/

This document is the single source of truth for any agent (Mac Claude, PC Claude,
iOS Claude, or a future instance) working on this repo. Read it before touching
anything. Update it when you make a significant change.

**Note:** this repo had no README or HANDOFF file before this one. It's a small,
mostly-finished repo, so this is a first-pass documentation of what's actually here
— not a rewrite of anything stale.

---

## Repo Relationship Map

`onda-help` is one of **four related repos**:

| Repo | What it is |
|------|-----------|
| `onda-replay` | The Flutter iOS/Android app — links out to this repo for in-app help |
| `onda-archive` | ONDA Nile discovery platform + marketing/spec docs; its `docs/onda-doc-demo.html` links directly to this repo's live site as a "Live Demo" |
| `pca-archive` | ProductCamp Austin session archive — unrelated to this repo |
| `onda-help` (this repo) | **ONDA Doc** — the living help documentation product itself, and the tooling used to build it |

**How the app reaches this repo:** `onda-replay`'s `lib/audio_notebook/an_config/an_constants.dart`
defines `anHelpUrl = 'https://david78737.github.io/onda-help/help.html'`. In-app
"Help" and "Ideas" icons open this URL, in some cases with a `?ctx=<Screen>` query
parameter (e.g. `?ctx=Catalog`) that pre-filters the page to just that screen's
articles — see "How help.html Works" below.

**No dependency the other direction:** `onda-help` doesn't read from or build
against `onda-replay` or `onda-archive` — it's a standalone static site. The only
coupling is conceptual: every article's screenshots and described behavior must
match what's actually in the `onda-replay` app, which is why the workflow (below)
insists on reading real source code rather than guessing from a screenshot alone.

---

## What "ONDA Doc" Is

ONDA Doc is David's living-help-documentation concept: numbered callouts on real
app screenshots, each callout naming a control and describing — verified against
actual app source code, not guessed — what it does. This repo is both the
**published product** (`help.html`, live help site) and the **workshop** used to
build it (`tools/`).

It's also pitched as a standalone product idea beyond ONDA Replay itself — see
`onda-archive/docs/onda-doc.html` and `onda-doc-demo.html` for the marketing/demo
pitch, and the `onda-doc` skill in Claude's tooling for the automated
screenshot-to-published-record workflow.

---

## Repository Structure

```
onda-help/
├── help.html              ← The entire published help site. One self-contained file
│                             (inline CSS + inline JS, no build step, no dependencies).
├── help-images/            ← All screenshots referenced by help.html, plus a number
│                             of unreferenced/orphaned images — see "Known Gaps" below.
├── tools/
│   ├── place_callouts.py   ← Python script: draws numbered callout circles onto a
│                             screenshot given control coordinates. The "callout-
│                             placement algorithm" referenced in project memory.
│   └── callout_picker.html ← Browser-based tool: click a screenshot to place pins,
│                             then export either a place_callouts.py-ready coordinate
│                             block or a help.html-ready callout stub.
├── .gitignore              ← Ignores .venv/ and __pycache__/ (both present locally,
│                             correctly untracked)
└── HANDOFF.md              ← This file.
```

There is no build step, no package.json, no server-side code. GitHub Pages serves
`help.html` and `help-images/` directly from the `main` branch root (confirmed via
`gh api repos/david78737/onda-help/pages` — Pages is live, source is `main` / `/`,
no custom domain/CNAME).

---

## How `help.html` Works

It's a single HTML file — not a giant wall of markup, but a small shell (header,
search bar, tag sidebar, card list, a bottom-sheet detail view, an image lightbox)
driven entirely by one JavaScript data array called `ARTICLES`, hardcoded near the
top of the `<script>` block (currently **23 entries**, ids 1–23).

Each entry in `ARTICLES` looks like:

```js
{
  id: 1,
  screen: "Recording",                 // groups articles by app screen in the sidebar
  title: "Recording Studio — Overview",
  tags: ["recording", "studio", ...],  // free-text topic tags, also used for search
  image: "help-images/record-screen-active.png",
  callouts: [ { n: 1, label: "...", text: "..." }, ... ],
  summary: "..."
}
```

**Navigation:** the left sidebar lists "Screens" (Recording, Catalog, Cover Editor,
Transcript, Explore, Utilities, Storyboard) and "Topics" (tags, sorted by
frequency). Clicking either filters the card list; the search box does a plain
substring match across title/summary/callout text. Tapping a card opens a bottom
sheet with the full screenshot (tap to expand into a lightbox), the callout table,
and the article's tags.

**The `?ctx=` deep link:** if the URL has `?ctx=Catalog` (etc.), the page opens
pre-filtered to that screen, with a banner reading "Showing help for: Catalog" and
a "Show all" link to clear it. This is how the app's context-sensitive Help/Ideas
buttons work — each screen's help button links to `help.html?ctx=<ThatScreen>`.

**Display order caveat:** with no filter active, articles render in `ARTICLES`
array order, which is edit-history order, not screen order or numeric id order
(e.g. id 19 appears third in the file, between ids 2 and 3). Not a bug — the
sidebar's Screen/Topic filters are the real navigation — but worth knowing if you
go looking for an article and expect it near its numeric neighbors.

---

## What Each Tool Does

### `tools/place_callouts.py`

Given a screenshot and a dict of `{label: (x_percent, y_percent)}` center points
for each control, draws numbered circles pointing at each one — close enough to
read as "pointing at this control," far enough not to sit on top of it, and never
crowding another dot or running off the image edge.

Two-part algorithm (fully documented in the file's own docstring, dated
2026-08-18, developed "live with David" by iterating against a real screenshot):

1. **Row/column detection** — controls with near-identical Y (or X) coordinates
   and 3+ members are treated as one toolbar-like group and shifted uniformly,
   preserving their natural spacing.
2. **Ring search** — every other control tries placement points on a ring around
   itself (diagonals first, then cardinals, then toward the image's own center as
   a smart first guess), picking the first spot that clears both the canvas edge
   and every already-placed dot.

All distance constants are tuned against a 381px reference width and scaled up
for larger source images (e.g. raw Simulator screenshots, which run ~3x that
width). A known, accepted edge case: a control very close to a corner may not get
a perfectly clean ring — the dot still lands validly, but David's documented
decision is to let a human flag and manually adjust rare corner cases rather than
add more special-case logic.

Run directly (`python place_callouts.py`) and it just prints its own docstring —
it's meant to be imported and called with `place_callouts(image_path, centers_pct,
order, output_path)`, not run as a CLI tool.

### `tools/callout_picker.html`

A standalone browser tool (open it directly as a file, no server needed) for
generating the coordinate data `place_callouts.py` needs, without eyeballing
pixel positions by hand. Load a screenshot, either click each control to drop a
numbered pin (dragging to fine-tune) or paste in an AI-generated JSON list of
`{label, text, x, y}` pins, then export:

- **Copy Python snippet** — a `centers_pct`/`order` block ready to paste into a
  script that calls `place_callouts.py`'s `place_callouts()`.
- **Copy help.html callout stub** — one `{ n, label, text }` entry per pin, ready
  to paste into a new or existing `ARTICLES` entry's `callouts` array.

It's self-documented in an HTML comment at the top of the file plus a set of
in-page `<details>` accordions covering: the four-element architecture of a help
file (image, pin, label, description), first-time documentation workflow, updating
an existing article when a screen changes, troubleshooting a failed AI-JSON paste,
and where screenshot files should live. It also embeds a ready-to-copy prompt
template instructing an AI coding agent (Claude Code, Codex, etc. — something with
real source-code access) to read the actual app code and identify every visible
control rather than guess from the screenshot alone.

Per its own header comment, this page was "self-documented 2026-08-30 by running
this exact tool on a screenshot of itself" — i.e. its own numbered-pin UI was
built using the workflow it exists to support.

---

## Known Gaps / Open Items

- **Broken image reference, article id 19 ("Shaping your tags before you save"):**
  `help.html` points this article at `help-images/save-tag-longpress.png`, which
  does not exist and has never existed in this repo (confirmed via `git log
  --follow` on that path — no history at all). The correct file is almost
  certainly `help-images/sleeve-tag-longpress.png` (used by the similarly-named
  article id 18, "Hidden gesture — Long-press a tag to favorite or ignore," about
  the Cover Editor's version of the same gesture). **This is currently a broken
  image on the live help site** — the bottom sheet for that one article shows a
  broken-image icon instead of a screenshot. Fix: either point id 19 at the
  correct existing file or generate/add a real `save-tag-longpress.png`.

- **Many unreferenced images in `help-images/`** — the folder holds far more files
  than the 23 images `ARTICLES` actually uses. Some are clearly raw/unannotated
  screenshots kept alongside their finished `-annotated.png` counterpart (e.g.
  `storyboard-overview.png` next to the referenced `storyboard-overview-annotated.png`)
  — harmless working files. Others look like screenshots taken toward articles
  that were never finished or published: `catalog-information-modal.png`,
  `edit-metadata-below-the-fold.png`, `edit-metadata-confirmation-screen.png`,
  `edit-metadata-detail.png`, `presentation-editor-content.png`,
  `presentation-editor-info.png`, `presentation-editor-links.png`,
  `presentation-editor-tags.png`, `utilities-top.png`, `transcribe-screen.png`,
  `transcription-screen.png`, `Transcription-menu-option.php.png`,
  `transcribe-copy.php.png`. None of these have a purpose documented anywhere —
  before deleting or using any of them, check whether they were staged for a
  planned-but-unwritten article.

- **Test/debug images that aren't help content:** `black-beans-test.png` and
  `shrimp-annie-test.png` (per the git log, test photos for `nile_presentations`
  records — unrelated to this app's help content) and
  `debug-recording-studio-active-constraints.png` (explicitly a callout-algorithm
  debug visualization, not a real help image, per its own commit message). These
  are development artifacts left in the shipped `help-images/` folder rather than
  a separate `dev/` or `debug/` location — low priority, but they do get served
  publicly since GitHub Pages serves the whole repo root.

- **Duplicate-looking filename:** `help-images/index drawer.png` (space) exists
  alongside `help-images/index-drawer.png` (hyphen, the one actually referenced
  by article id 10). The space-named file is unreferenced — likely an earlier,
  unused save of the same screenshot. Worth confirming it's safe to delete rather
  than something with its own purpose.

- **`tools/callout_picker.html` is not committed to this repo.** It exists on
  this machine (and is documented above, since it's clearly a real, finished
  tool — self-documented, workable, referenced by its own file header) but
  `git ls-files` confirms it has never been added to version control. Same for
  two raw Storyboard screenshots (`help-images/storyboard add control
  numbers.png`, `help-images/storyboard control functions.png`) and a stray
  `.DS_Store`. **If this repo is cloned fresh on another machine, the callout
  picker tool will be missing.** This should be committed (or deliberately
  excluded, if there's a reason not to) rather than left as an untracked local
  file — check with David before assuming it's safe to just add.

- **No automated check that `ARTICLES` images resolve.** Because `help.html` has
  no build step, a typo'd or missing image path (like the id-19 case above) is
  silent until someone opens that specific article on the live site. If more
  articles get added by hand, a simple local script comparing every `image:`
  value against the contents of `help-images/` would catch this class of bug
  before it ships.

---

## Agent Coordination Notes

This repo follows the same multi-agent conventions as `onda-replay`,
`onda-archive`, and `pca-archive`: **before making changes, `git pull`**; **after
making changes, commit immediately** — don't hold uncommitted work across
sessions. It's a small, low-traffic repo (single-file site, no build), so
collisions are less likely here than in `onda-archive`, but the same discipline
applies since more than one machine/agent may touch it.
