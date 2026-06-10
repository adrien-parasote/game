"""
profile_game.py — Profiling harness 4 axes pour le moteur de jeu.

Produit un rapport structuré dans un seul fichier texte :
  - Frame timing   : avg, p50, p95, p99, spikes
  - CPU hotspots   : tottime + cumtime, filtré game/src
  - Mémoire        : delta total + top 20 allocations par fichier:ligne
  - GC pressure    : collections et objets collectés par génération

Usage:
    python scripts/dev/profile_game.py [--frames N] [--output FICHIER]

Arguments:
    --frames N       Nombre de frames à profiler (défaut : 1800 = 30 s à 60 fps)
    --output FICHIER Chemin du rapport (défaut : scripts/dev/profile_report.txt)

Pour analyser :
    Colle le contenu de profile_report.txt dans le chat.
"""
import argparse
import cProfile
import gc
import io
import os
import pstats
import sys
import tracemalloc
from typing import List, Tuple

import pygame

# ---------------------------------------------------------------------------
# Path setup : scripts/dev/ → workspace root → game/
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", "game"))
_GAME_SRC = os.path.join(_GAME_DIR, "src")
sys.path.append(_GAME_DIR)

from src.engine.game_state_manager import GameStateManager  # noqa: E402

_SEP = "-" * 72


# ---------------------------------------------------------------------------
# Boucle de jeu — collecte les frame times
# ---------------------------------------------------------------------------

def run_game_loop(frames: int) -> List[float]:
    """Lance le jeu pour *frames* frames. Retourne les temps de frame en ms."""
    pygame.init()
    manager = GameStateManager()
    manager._transition_to_playing(slot_id=None)

    frame_times: List[float] = []
    for _ in range(frames):
        dt_ms = manager._game.clock.tick(60)
        dt = dt_ms / 1000.0
        events = pygame.event.get()
        manager._process_global_events(events)
        manager._handle_playing(events, dt)
        pygame.display.update()
        frame_times.append(float(dt_ms))

    pygame.quit()
    return frame_times


# ---------------------------------------------------------------------------
# AXE 1 — Frame timing
# ---------------------------------------------------------------------------

def _percentile(data: List[float], p: float) -> float:
    s = sorted(data)
    idx = max(0, min(int(len(s) * p / 100), len(s) - 1))
    return s[idx]


def section_frame_timing(frame_times: List[float]) -> str:
    n = len(frame_times)
    avg = sum(frame_times) / n
    fps = 1000.0 / avg if avg > 0 else 0.0
    p50 = _percentile(frame_times, 50)
    p95 = _percentile(frame_times, 95)
    p99 = _percentile(frame_times, 99)
    ft_min = min(frame_times)
    ft_max = max(frame_times)
    spikes_33 = sum(1 for t in frame_times if t > 33.3)   # < 30 fps
    spikes_50 = sum(1 for t in frame_times if t > 50.0)   # < 20 fps

    return "\n".join([
        "=== AXE 1 — FRAME TIMING ===",
        f"Frames        : {n}",
        f"FPS moyen     : {fps:.1f}",
        f"avg           : {avg:.2f} ms",
        f"p50           : {p50:.2f} ms",
        f"p95           : {p95:.2f} ms   ← seuil confort",
        f"p99           : {p99:.2f} ms   ← worst-case joueur",
        f"min / max     : {ft_min:.2f} ms / {ft_max:.2f} ms",
        f"Spikes >33 ms : {spikes_33} frames ({spikes_33 / n * 100:.1f}%)  [< 30 fps]",
        f"Spikes >50 ms : {spikes_50} frames ({spikes_50 / n * 100:.1f}%)  [< 20 fps]",
    ])


# ---------------------------------------------------------------------------
# AXE 2 — CPU hotspots
# ---------------------------------------------------------------------------

def _pstats_table(profiler: cProfile.Profile, sort_key: str,
                  pattern: str, n: int) -> str:
    """Extrait le tableau pstats filtré sur *pattern*, trie par *sort_key*."""
    buf = io.StringIO()
    stats = pstats.Stats(profiler, stream=buf)
    stats.sort_stats(sort_key)
    stats.print_stats(pattern, n)
    raw = buf.getvalue()
    # Ne garder que les lignes utiles (à partir de la ligne d'en-tête ncalls)
    lines = raw.splitlines()
    start = next((i for i, l in enumerate(lines) if "ncalls" in l and "tottime" in l), 0)
    return "\n".join(lines[start:]).strip()


def section_cpu(profiler: cProfile.Profile) -> str:
    game_pattern = r"game[/\\]src"
    top_tot = _pstats_table(profiler, "tottime", game_pattern, 25)
    top_cum = _pstats_table(profiler, "cumtime", game_pattern, 25)
    return "\n".join([
        "=== AXE 2 — CPU HOTSPOTS (game/src uniquement) ===",
        "",
        "--- TOP 25 par tottime (temps PROPRE — où le CPU est réellement occupé) ---",
        top_tot,
        "",
        "--- TOP 25 par cumtime (temps CUMULÉ incl. appelés — révèle les chaînes coûteuses) ---",
        top_cum,
    ])


# ---------------------------------------------------------------------------
# AXE 3 — Mémoire
# ---------------------------------------------------------------------------

def section_memory(
    snap_before: tracemalloc.Snapshot,
    snap_after: tracemalloc.Snapshot,
    mem_before_kb: float,
    mem_after_kb: float,
    frames: int,
) -> str:
    delta_kb = mem_after_kb - mem_before_kb
    delta_per_frame_kb = delta_kb / frames if frames > 0 else 0.0

    lines = [
        "=== AXE 3 — MÉMOIRE (Python heap via tracemalloc) ===",
        f"Début         : {mem_before_kb / 1024:.2f} MB",
        f"Fin           : {mem_after_kb / 1024:.2f} MB",
        f"Delta total   : {delta_kb:+.1f} KB  ({delta_per_frame_kb:+.2f} KB/frame)",
        "",
        "--- TOP 20 ALLOCATIONS par fichier:ligne (delta, filtré game/src) ---",
        f"{'delta':>12}  {'taille totale':>14}  localisation",
        _SEP,
    ]

    diffs = snap_after.compare_to(snap_before, "lineno")
    # Filtrer game/src; fallback sur tout si vide
    game_diffs = [
        d for d in diffs
        if d.traceback and _GAME_SRC in d.traceback[0].filename
    ]
    target = game_diffs if game_diffs else diffs
    target = sorted(target, key=lambda d: d.size_diff, reverse=True)[:20]

    for diff in target:
        if not diff.traceback:
            continue
        frame = diff.traceback[0]
        rel_path = os.path.relpath(frame.filename, _GAME_DIR)
        loc = f"{rel_path}:{frame.lineno}"
        size_kb = diff.size / 1024
        delta_sign = f"{diff.size_diff / 1024:+.1f} KB"
        size_str = f"{size_kb:.1f} KB"
        lines.append(f"{delta_sign:>12}  {size_str:>14}  {loc}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# AXE 4 — GC pressure
# ---------------------------------------------------------------------------

GcStats = List[dict]


def _gc_snapshot() -> GcStats:
    return [dict(s) for s in gc.get_stats()]


def section_gc(before: GcStats, after: GcStats) -> str:
    lines = [
        "=== AXE 4 — GC PRESSURE ===",
        f"{'génération':>12}  {'collections':>12}  {'objets collectés':>18}  {'uncollectable':>14}",
        _SEP,
    ]
    has_warning = False
    for gen_idx, (b, a) in enumerate(zip(before, after)):
        collections = a["collections"] - b["collections"]
        collected = a["collected"] - b["collected"]
        uncollectable = a["uncollectable"] - b["uncollectable"]
        warn = "  ⚠️  UNCOLLECTABLE — fuite probable" if uncollectable > 0 else ""
        if uncollectable > 0:
            has_warning = True
        lines.append(
            f"{'gen' + str(gen_idx):>12}  {collections:>12}  {collected:>18,}  {uncollectable:>14}{warn}"
        )

    if has_warning:
        lines.append("")
        lines.append("⚠️  Des objets uncollectable indiquent un cycle de référence non cassable.")
        lines.append("   Chercher : __del__ + références circulaires dans game/src.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI + orchestration
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    default_output = os.path.join(_SCRIPT_DIR, "profile_report.txt")
    parser = argparse.ArgumentParser(
        description="Profiler 4-axes pour le moteur de jeu."
    )
    parser.add_argument(
        "--frames", type=int, default=1800,
        help="Nombre de frames (défaut : 1800 = 30 s à 60 fps).",
    )
    parser.add_argument(
        "--output", default=default_output,
        help=f"Fichier de sortie (défaut : {default_output})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    sys.stdout.write(f"[profiler] Démarrage ({args.frames} frames)…\n")

    # --- Baselines ---
    gc.collect()
    gc_before = _gc_snapshot()

    tracemalloc.start(10)  # 10 niveaux de traceback pour localiser précisément
    snap_before = tracemalloc.take_snapshot()
    mem_before_kb = tracemalloc.get_traced_memory()[0] / 1024

    # --- Profiling CPU ---
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        frame_times = run_game_loop(args.frames)
    except Exception as exc:
        profiler.disable()
        tracemalloc.stop()
        sys.stderr.write(f"[profiler] Abandon : {exc}\n")
        raise

    profiler.disable()

    # --- Snapshots post-run ---
    snap_after = tracemalloc.take_snapshot()
    mem_after_kb = tracemalloc.get_traced_memory()[0] / 1024
    tracemalloc.stop()
    gc_after = _gc_snapshot()

    # --- Construction du rapport ---
    sys.stdout.write("[profiler] Construction du rapport…\n")
    header = "\n".join([
        "=" * 72,
        "  RAPPORT DE PROFILING — MOTEUR DE JEU",
        f"  {args.frames} frames  |  ~{args.frames / 60:.0f} secondes simulées",
        "  Colle ce fichier dans le chat pour une analyse et des corrections.",
        "=" * 72,
    ])

    report = "\n\n".join([
        header,
        section_frame_timing(frame_times),
        _SEP,
        section_cpu(profiler),
        _SEP,
        section_memory(snap_before, snap_after, mem_before_kb, mem_after_kb, args.frames),
        _SEP,
        section_gc(gc_before, gc_after),
    ])

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    sys.stdout.write(f"[profiler] Rapport sauvegardé → {args.output}\n")
    sys.stdout.write("[profiler] Colle le contenu du fichier dans le chat pour l'analyse.\n")
