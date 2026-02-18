#!/usr/bin/env python3
"""
GitHub Heatmap Pixel Art: Ghost fleeing Pac-Man (mirrored scene)
-----------------------------------------------------------------
Usage:
  python draw.py            → preview the art (no commits)
  python draw.py --commit   → create the git commits

The grid is 7 rows (Sun–Sat) × 52 columns (weeks).
Commits are backdated to fill the past year's heatmap.

Cell shading (inverted):
  background cells → COMMITS_FILL commits (darkest green)
  character cells  → 0 commits            (light / empty)

To undo before pushing:  git reset --hard HEAD~<N>
"""

import os
import sys
import subprocess
from datetime import datetime, timedelta

# -- Sprites (7 rows × 7 cols) ---------------------------------------------

# Pac-Man facing LEFT (mouth opens on the left side)
PACMAN_LEFT = [
    [0, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 1, 1, 1, 1],  # ← open mouth (left)
    [0, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 0],
]

GHOST = [
    [0, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 0, 1, 0, 1, 1],  # ← eyes
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 0, 1, 0, 1, 0, 1],  # ← wiggly skirt
]

# -- Build the 7×52 grid ---------------------------------------------------

COLS = 52
grid = [[0] * COLS for _ in range(7)]

def place(sprite, start_col):
    for r, row in enumerate(sprite):
        for c, val in enumerate(row):
            col = start_col + c
            if col < COLS:
                grid[r][col] = 1 if val else 0

# Ghost on the left, fleeing
place(GHOST, 3)

# Dot trail on row 3 between ghost and Pac-Man
for col in range(11, 40, 2):   # cols 11, 13, 15, … 39
    grid[3][col] = 1

# Pac-Man on the right, facing left (chasing)
place(PACMAN_LEFT, 41)

# Invert: characters become empty (0), background becomes lit (1)
for _r in range(7):
    for _c in range(COLS):
        grid[_r][_c] = 1 - grid[_r][_c]

# -- Shading ---------------------------------------------------------------

COMMITS_FILL = 10   # darkest green shade — used for all background cells

def compute_shading():
    """
    Convert the inverted binary grid (0/1) to commit counts.
    All lit cells (background) get COMMITS_FILL; character cells stay 0.
    """
    for r in range(7):
        for c in range(COLS):
            if grid[r][c]:
                grid[r][c] = COMMITS_FILL

compute_shading()

# -- Date helpers ----------------------------------------------------------

def get_heatmap_start() -> datetime:
    """
    Return the Sunday that begins the leftmost column of the
    GitHub 'last year' heatmap (52 columns wide).
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days_since_sunday = (today.weekday() + 1) % 7
    current_sunday = today - timedelta(days=days_since_sunday)
    return current_sunday - timedelta(weeks=51)

def col_row_to_date(start: datetime, col: int, row: int) -> datetime:
    return start + timedelta(days=col * 7 + row)

# -- Preview ---------------------------------------------------------------

def preview():
    DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    lit_fill      = sum(1 for r in range(7) for c in range(COLS) if grid[r][c] == COMMITS_FILL)
    total_commits = lit_fill * COMMITS_FILL

    print("\nHeatmap preview  (# = background  . = character)\n")
    print("         " + "".join(str(c // 10) if c % 10 == 0 else " " for c in range(COLS)))
    print("         " + "".join(str(c % 10) for c in range(COLS)))
    print("         " + "-" * COLS)
    for r in range(7):
        row_str = "".join(
            "#" if grid[r][c] == COMMITS_FILL else "."
            for c in range(COLS)
        )
        label = f"({DAYS[r]})" if r in (1, 3, 5) else "      "
        print(f"  {label}  {row_str}")
    print("         " + "-" * COLS)

    start = get_heatmap_start()
    end   = col_row_to_date(start, COLS - 1, 6)
    print(f"\n  Heatmap range    : {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    print(f"  Background cells : {lit_fill}  × {COMMITS_FILL} commits")
    print(f"  Total commits    : {total_commits}")
    print(f"\n  To create commits: python draw.py --commit\n")

# -- Commit generator ------------------------------------------------------

def make_commits():
    start = get_heatmap_start()
    total_needed = sum(grid[r][c] for r in range(7) for c in range(COLS))

    print(f"\nHeatmap start date : {start.strftime('%Y-%m-%d')}")
    print(f"Commits to create  : {total_needed}\n")

    count  = 0
    errors = 0

    for col in range(COLS):
        for row in range(7):
            commits_for_cell = grid[row][col]
            if not commits_for_cell:
                continue
            date     = col_row_to_date(start, col, row)
            date_str = date.strftime('%Y-%m-%dT12:00:00')
            env      = {**os.environ,
                        'GIT_AUTHOR_DATE':    date_str,
                        'GIT_COMMITTER_DATE': date_str}

            for _ in range(commits_for_cell):
                count += 1
                result = subprocess.run(
                    ['git', 'commit', '--allow-empty', '-m', f'pixel #{count}'],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print(f"  ERROR on commit {count}: {result.stderr.strip()}")
                    errors += 1

            if count % 200 == 0:
                print(f"  {count} / {total_needed} commits done...")

    print(f"\nDone!  {count} commits created,  {errors} errors.")
    if errors == 0:
        print("Run:  git push")

# -- Entry point -----------------------------------------------------------

if __name__ == '__main__':
    if '--commit' in sys.argv:
        make_commits()
    else:
        preview()
