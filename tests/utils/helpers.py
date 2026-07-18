from pathlib import Path


def repo_root():
    """Return repository root path (useful for tests and reporting)."""
    return Path(__file__).parents[2]


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)
    return p
