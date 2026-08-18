#!/usr/bin/env python3
"""
place_callouts.py — Numbered callout placement for ONDA Doc help screenshots.

Given a screenshot and a set of control center-points (as percentages of
image width/height), draws numbered circles that point at each control
without covering it, without crowding each other, and without leaving
the image canvas.

Developed live with David, 2026-08-18, by iterating on a real screenshot
and a debug visualization until the placement looked right. See
project_onda_doc_hardware_instructions.md (memory) for the full history.

THE ALGORITHM
--------------
Two rules, applied in order:

1. ROW / COLUMN DETECTION (handles evenly-spaced groups, e.g. a toolbar)
   Controls whose Y (or X) coordinates fall within ROW_TOLERANCE percent
   of each other are treated as one aligned group. The whole group is
   shifted by a single uniform offset, perpendicular to its own axis
   (a horizontal row shifts straight up or down; a vertical column
   shifts straight left or right). Because every member moves by the
   *same* amount, the group's own natural spacing is preserved exactly
   — no per-dot search needed, and no risk of two dots in the same row
   crowding each other.

2. RING SEARCH (handles everything else)
   For any control not part of a detected group, try placing its dot at
   points on rings between MIN_DIST and MAX_DIST pixels from the
   control's center, in a fixed priority order of directions (diagonals
   first, then cardinals). The first candidate that satisfies both
   constraints below is used:
     - stays at least EDGE_MARGIN pixels inside the image canvas
     - stays at least MIN_DOT_SPACING pixels from every already-placed dot

KNOWN EDGE CASE — accepted, not solved
----------------------------------------
A control very close to a corner (e.g. within MIN_DIST of two canvas
edges at once) can have no ring that both clears MIN_DIST from the
control AND stays fully inside the canvas. In practice the *chosen dot*
still lands correctly (the edge-margin check on the dot itself always
holds), but there's no guarantee of a "clean" ring for extreme corner
cases. David's call: this is fine — a human reviewer flags it via
`reviewer_note` on the Presentations record and the dot gets manually
adjusted, rather than adding more special-case logic for a rare corner.
"""

import math
from PIL import Image, ImageDraw, ImageFont

RADIUS = 10             # fixed pixel radius of the callout circle
MIN_DIST = 18           # closest a dot's center may sit to its control's center
MAX_DIST = 34           # farthest it may drift and still read as "pointing at this"
EDGE_MARGIN = 30         # closest a dot may sit to the image canvas boundary (widened for rounded phone-frame corners)
MIN_DOT_SPACING = 26     # minimum center-to-center distance between any two dots
ROW_TOLERANCE = 3        # percent — controls within this Y (or X) range count as one group

DIST_OPTIONS = [(MIN_DIST + MAX_DIST) / 2, MIN_DIST, MAX_DIST]
DIRS = [
    (0.707, -0.707), (0.707, 0.707), (-0.707, -0.707), (-0.707, 0.707),
    (1, 0), (-1, 0), (0, -1), (0, 1),
]


def _font(size=13):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except Exception:
        return ImageFont.load_default()


def _detect_rows(order, centers_pct):
    """Group controls whose Y-coordinates cluster together (3+ members)."""
    ys = {l: centers_pct[l][1] for l in order}
    xs = {l: centers_pct[l][0] for l in order}
    grouped = set()
    rows = []
    for l in order:
        if l in grouped:
            continue
        row = [m for m in order if m not in grouped and abs(ys[m] - ys[l]) <= ROW_TOLERANCE]
        if len(row) >= 3:
            rows.append(sorted(row, key=lambda m: xs[m]))
            grouped.update(row)
    return rows


def place_callouts(image_path, centers_pct, order, output_path):
    """
    image_path:   source screenshot
    centers_pct:  {label: (x_percent, y_percent)} — one center point per control
    order:        list of labels, drawing/priority order (also numbering order)
    output_path:  where to save the annotated PNG
    """
    im = Image.open(image_path).convert("RGBA")
    W, H = im.size
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _font()

    placed = []  # (label, x, y)

    # 1) Row/column groups first — uniform perpendicular shift.
    # The shift only ever moves the group along its perpendicular axis
    # (vertical for a row), so the *along-axis* coordinate (X for a row)
    # is never touched by that shift — it still needs its own edge-margin
    # check, or a row whose members sit near the left/right canvas edge
    # (e.g. the leftmost/rightmost icon in a toolbar) will silently keep
    # an out-of-bounds X forever, no matter how wide EDGE_MARGIN is set.
    rows = _detect_rows(order, centers_pct)
    for row in rows:
        ctr_ys = [centers_pct[m][1] / 100 * H for m in row]
        shift = None
        for dy in (-((MIN_DIST + MAX_DIST) / 2), (MIN_DIST + MAX_DIST) / 2):
            if all((RADIUS + EDGE_MARGIN) <= (cy + dy) <= H - (RADIUS + EDGE_MARGIN) for cy in ctr_ys):
                shift = dy
                break
        if shift is None:
            shift = -((MIN_DIST + MAX_DIST) / 2)

        # Along-axis (X) correction: a uniform SHIFT can only fix one end
        # of the row at a time — if both the leftmost and rightmost
        # members are simultaneously too close to their respective edges
        # (a row whose natural width doesn't fit inside the margins at
        # all), sliding the row sideways fixes one end and leaves the
        # other exactly as cramped as before, breaking even spacing.
        # Instead, scale every member's distance from the row's own
        # center point inward by the same factor, only if needed — this
        # compresses the row symmetrically around its middle rather than
        # translating it, so both ends clear the margin at once and
        # relative spacing stays proportional and even.
        ctr_xs = [centers_pct[m][0] / 100 * W for m in row]
        row_center = (min(ctr_xs) + max(ctr_xs)) / 2
        half_width = (max(ctr_xs) - min(ctr_xs)) / 2
        room_left = row_center - (RADIUS + EDGE_MARGIN)
        room_right = (W - (RADIUS + EDGE_MARGIN)) - row_center
        available_half = min(room_left, room_right)
        scale = 1.0 if half_width <= available_half or half_width == 0 else available_half / half_width

        for m in row:
            cx = row_center + (centers_pct[m][0] / 100 * W - row_center) * scale
            cy = centers_pct[m][1] / 100 * H + shift
            placed.append((m, cx, cy))

    # 2) Everything else — ring search against edge margin + dot spacing
    for label in order:
        if any(m == label for m, _, _ in placed):
            continue
        px, py = centers_pct[label]
        ctr_x, ctr_y = px / 100 * W, py / 100 * H
        chosen = None
        for dist in DIST_OPTIONS:
            for dx, dy in DIRS:
                cx, cy = ctr_x + dx * dist, ctr_y + dy * dist
                if not ((RADIUS + EDGE_MARGIN) <= cx <= W - (RADIUS + EDGE_MARGIN)
                        and (RADIUS + EDGE_MARGIN) <= cy <= H - (RADIUS + EDGE_MARGIN)):
                    continue
                if any(math.hypot(cx - px2, cy - py2) < MIN_DOT_SPACING for _, px2, py2 in placed):
                    continue
                chosen = (cx, cy)
                break
            if chosen:
                break
        cx, cy = chosen if chosen else (ctr_x, ctr_y)
        placed.append((label, cx, cy))

    placed_dict = {m: (x, y) for m, x, y in placed}
    for label in order:
        cx, cy = placed_dict[label]
        draw.ellipse([cx - RADIUS, cy - RADIUS, cx + RADIUS, cy + RADIUS],
                     fill=(0, 150, 136, 255), outline=(255, 255, 255, 255), width=2)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw / 2, cy - th / 2 - bbox[1]), label, fill=(255, 255, 255, 255), font=font)

    out = Image.alpha_composite(im, overlay).convert("RGB")
    out.save(output_path)
    return output_path


if __name__ == "__main__":
    import sys
    print(__doc__)
    print("Import place_callouts() and call it with your own image path, "
          "centers_pct dict, and order list — see the docstring above.")
