import hashlib
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from core.path_helper import get_safe_trash_path
from core.safe_trash import move_to_safe_trash
from core.undo_manager import UndoManager

PROTECTED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "venv", ".venv",
    "env", "__pycache__", ".idea", ".vscode", ".vs", "site-packages"
}


@dataclass
class DuplicateGroup:
    file_hash: str
    size_bytes: int
    files: List[Path]  # En eski tarihli orijinal dosya en başta yer alır


@dataclass
class LargeFile:
    path: Path
    name: str
    size_bytes: int
    age_days: int


class DuplicateAndLargeFinder:
    """Seçili klasörlerde birebir kopya dosyaları ve büyük dosyaları tespit eder."""

    @staticmethod
    def _iter_safe_files(selected_folders: List[Path]):
        safe_trash = get_safe_trash_path().resolve()
        for folder in selected_folders:
            if not folder.exists() or not folder.is_dir():
                continue
            for root, dirs, files in os.walk(folder, onerror=lambda _e: None):
                root_path = Path(root)
                # Güvenli Çöp Kutusu, gizli (.) klasörler ve yazılım proje klasörlerini koru
                dirs[:] = [
                    d for d in dirs
                    if (root_path / d).resolve() != safe_trash
                    and not d.startswith("$")
                    and not d.startswith(".")
                    and d.lower() not in PROTECTED_DIRS
                ]
                for fname in files:
                    fpath = root_path / fname
                    if fpath.is_file() and not fpath.is_symlink():
                        yield fpath

    @staticmethod
    def _hash_file(path: Path, first_chunk_only: bool = False) -> str:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            if first_chunk_only:
                hasher.update(f.read(65536))
            else:
                while chunk := f.read(65536):
                    hasher.update(chunk)
        return hasher.hexdigest()

    def find_duplicates(self, selected_folders: List[Path]) -> List[DuplicateGroup]:
        by_size: Dict[int, List[Path]] = defaultdict(list)
        for fpath in self._iter_safe_files(selected_folders):
            try:
                sz = fpath.stat().st_size
                if sz > 0:
                    by_size[sz].append(fpath)
            except OSError:
                continue

        partial_groups: Dict[Tuple[int, str], List[Path]] = defaultdict(list)
        for sz, paths in by_size.items():
            if len(paths) < 2:
                continue
            for p in paths:
                try:
                    ph = self._hash_file(p, first_chunk_only=True)
                    partial_groups[(sz, ph)].append(p)
                except OSError:
                    continue

        exact_groups: Dict[str, Tuple[int, List[Path]]] = {}
        for (sz, _), paths in partial_groups.items():
            if len(paths) < 2:
                continue
            for p in paths:
                try:
                    full_h = self._hash_file(p, first_chunk_only=False)
                    if full_h not in exact_groups:
                        exact_groups[full_h] = (sz, [])
                    exact_groups[full_h][1].append(p)
                except OSError:
                    continue

        results: List[DuplicateGroup] = []
        for full_h, (sz, paths) in exact_groups.items():
            if len(paths) > 1:
                paths.sort(key=lambda p: p.stat().st_mtime)
                results.append(DuplicateGroup(file_hash=full_h, size_bytes=sz, files=paths))

        results.sort(key=lambda g: g.size_bytes * (len(g.files) - 1), reverse=True)
        return results

    def find_large_files(self, selected_folders: List[Path], min_size_mb: int = 100) -> List[LargeFile]:
        min_bytes = min_size_mb * 1024 * 1024
        now = datetime.now()
        results: List[LargeFile] = []

        for fpath in self._iter_safe_files(selected_folders):
            try:
                st = fpath.stat()
                if st.st_size >= min_bytes:
                    mtime = datetime.fromtimestamp(st.st_mtime)
                    results.append(
                        LargeFile(
                            path=fpath,
                            name=fpath.name,
                            size_bytes=st.st_size,
                            age_days=max(0, (now - mtime).days),
                        )
                    )
            except OSError:
                continue

        results.sort(key=lambda x: x.size_bytes, reverse=True)
        return results

    @staticmethod
    def move_files_to_trash(
        paths: List[Path], description_prefix: str, undo_manager: UndoManager
    ) -> Tuple[int, List[str]]:
        moved: List[Tuple[Path, Path]] = []
        errors: List[str] = []

        for p in paths:
            try:
                dest = move_to_safe_trash(p)
                moved.append((p, dest))
            except Exception as e:
                errors.append(f"{p.name}: {e}")

        if moved:
            undo_manager.record_batch(
                action_type="safe_trash",
                description=f"{len(moved)} {description_prefix} Güvenli Çöp Kutusuna taşındı",
                moves=moved,
            )

        return len(moved), errors