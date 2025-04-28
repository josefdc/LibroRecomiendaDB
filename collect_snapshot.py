#!/usr/bin/env python3
"""
snapshot_clean.py ― Exporta un TXT con la estructura ***concisa*** y el contenido
de los archivos realmente útiles de un proyecto.

▫️ Filtros de directorio/archivo para ruido habitual (.venv, __pycache__, *.pyc…)
▫️ Lista blanca de extensiones relevantes (.py, .toml, .md, .yml…; ajustable)
▫️ Umbral de tamaño (bytes) para saltarse binarios enormes accidentalmente
▫️ Opciones CLI para personalizar filtros sin tocar el código

Ejemplo:
    python snapshot_clean.py . -o docs/snapshot.txt --only-ext .py,.md
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import fnmatch
import os
from pathlib import Path
from typing import Iterable, List

# ────────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN POR DEFECTO ─ modifícala si quieres, o usa las flags CLI
# ────────────────────────────────────────────────────────────────────────────────
DEFAULT_IGNORE_DIRS = [
    ".git", ".venv", ".mypy_cache", ".pytest_cache", ".idea", ".vscode",
    "__pycache__", "*.egg-info", ".cache", ".tox", "dist", "build",
]
DEFAULT_IGNORE_FILES = [
    "*.pyc", "*.pyo", "*.so", "*.dylib", "*.log", "*.db", "*.sqlite3",
    "*.DS_Store", "*.lock", "*.zip", "*.tar.gz",
]
DEFAULT_ONLY_EXT = [
    ".py", ".toml", ".md", ".txt", ".ini", ".json", ".yaml", ".yml",
    ".sql", ".html", ".js", ".ts", ".css",
]
DEFAULT_MAX_SIZE = 1_000_000            # 1 MB

# ────────────────────────────────────────────────────────────────────────────────
# DATA STRUCTS
# ────────────────────────────────────────────────────────────────────────────────
@dataclass
class Filters:
    ignore_dirs: List[str]
    ignore_files: List[str]
    only_ext:   List[str]
    max_size:   int


# ────────────────────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────────────────────
def _matches(path: Path, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(path.name, pat) for pat in patterns)

def must_ignore(path: Path, f: Filters) -> bool:
    if path.is_dir():
        return _matches(path, f.ignore_dirs)
    # archivo
    if _matches(path, f.ignore_files):
        return True
    if f.only_ext and path.suffix.lower() not in f.only_ext:
        return True
    if f.max_size and path.stat().st_size > f.max_size:
        return True
    return False


# ────────────────────────────────────────────────────────────────────────────────
# DISCOVERY
# ────────────────────────────────────────────────────────────────────────────────
def collect_files(root: Path, f: Filters) -> List[Path]:
    relevant: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # purga de subdirectorios irrelevantes in-place
        dirnames[:] = [d for d in dirnames if not must_ignore(Path(d), f)]
        for name in filenames:
            fp = Path(dirpath) / name
            if not must_ignore(fp, f):
                relevant.append(fp)
    return sorted(relevant)

def build_tree(root: Path, files: List[Path]) -> str:
    """Dibuja el árbol mostrando solo ramas que contengan archivos relevantes."""
    # Conjunto de carpetas que sí aportan algo
    keep_dirs = {root}
    for file in files:
        for parent in file.parents:
            keep_dirs.add(parent)
            if parent == root:
                break

    lines: List[str] = []
    for path in sorted(keep_dirs | set(files)):
        rel = path.relative_to(root)
        indent = "│   " * (len(rel.parts) - 1)
        prefix = "├── " if rel.parts else ""
        lines.append(f"{indent}{prefix}{path.name}{'/' if path.is_dir() else ''}")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Genera un snapshot limpio del proyecto.")
    ap.add_argument("root", nargs="?", default=".", help="Raíz del proyecto")
    ap.add_argument("-o", "--output", default="project_snapshot.txt", help="Archivo de salida")
    ap.add_argument("--ignore-dirs", help="Patrones coma-separados extra para ignorar")
    ap.add_argument("--ignore-files", help="Patrones coma-separados extra para ignorar")
    ap.add_argument("--only-ext", help="Extensiones permitidas (ej: .py,.md) ― vacío = todas")
    ap.add_argument("--max-size", type=int, default=DEFAULT_MAX_SIZE,
                    help=f"Tamaño máximo (bytes) de archivos a incluir (def {DEFAULT_MAX_SIZE})")
    args = ap.parse_args()

    filters = Filters(
        ignore_dirs=DEFAULT_IGNORE_DIRS + (args.ignore_dirs.split(",") if args.ignore_dirs else []),
        ignore_files=DEFAULT_IGNORE_FILES + (args.ignore_files.split(",") if args.ignore_files else []),
        only_ext=[e.lower() for e in (args.only_ext.split(",") if args.only_ext else DEFAULT_ONLY_EXT)],
        max_size=args.max_size,
    )

    root = Path(args.root).resolve()
    files = collect_files(root, filters)

    with open(args.output, "w", encoding="utf-8") as out:
        # 1. Árbol compacto
        out.write("# Estructura relevante del proyecto\n\n")
        out.write(build_tree(root, files) + "\n\n")

        # 2. Contenido de archivos
        out.write("# Contenido de archivos relevantes\n")
        for fp in files:
            rel = fp.relative_to(root)
            out.write("\n" + "-" * 80 + f"\n# {rel}\n\n")
            try:
                out.write(fp.read_text(encoding="utf-8", errors="replace") + "\n")
            except Exception as e:
                out.write(f"<<No se pudo leer este archivo: {e}>>\n")

    print(f"Snapshot listo → {args.output}")

if __name__ == "__main__":
    main()
