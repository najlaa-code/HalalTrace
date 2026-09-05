"""Shared path constants so every pipeline writes/reads from the same places."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = ROOT_DIR / "datasets"
CACHE_DIR = DATASETS_DIR / "_cache"
RESULTS_DIR = ROOT_DIR / "results"

DATASETS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)
