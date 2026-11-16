import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Set, Tuple

from config import FILE_CATEGORIES
from core.undo_manager import UndoManager

DOC_SUBTYPES = {
    ".pdf": "PDF",
    ".doc": "Word",
    ".docx": "Word",
    ".xls": "Excel",
    ".xlsx": "Excel",
    ".csv": "Excel",
    ".ppt": "Sunum",
    ".pptx": "Sunum",
    ".txt": "Metin",
}

TURKISH_MONTHS = {
    1: "01 - Ocak", 2: "02 - Şubat", 3: "03 - Mart", 4: "04 - Nisan",
    5: "05 - Mayıs", 6: "06 - Haziran", 7: "07 - Temmuz", 8: "08 - Ağustos",
    9: "09 - Eylül", 10: "10 - Ekim", 11: "11 - Kasım", 12: "12 - Aralık",
}

IGNORED_FILES = {"desktop.ini", "thumbs.db", ".ds_store"}


@dataclass
class PlannedMove:
    source: Path
    destination: Path
    category: str
    sub_category: str
    size_bytes: int


class FileOrganizer:
    """Seçili klasörleri analiz eder, hiyerarşik düzenleme planı kurar ve uygular."""

    def _classify_file(self, file_path: Path, base_folder: Path) -> Tuple[str, str, Path] | None:
        """Dosyanın uzantısına göre kategori, alt kategori ve hedef klasörü belirler."""
        ext = file_path.suffix.lower()
        if not ext:
            return None

        for category, rules in FILE_CATEGORIES.items():
            if ext in rules["extensions"]:
                # 1. Tarih bazlı hiyerarşi (Örn: Görseller > 2026 > 11 - Kasım)
                if rules.get("by_date"):
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    year_str = str(mtime.year)
                    month_str = TURKISH_MONTHS[mtime.month]
                    dest_dir = base_folder / category / year_str / month_str
                    return category, f"{year_str} / {month_str}", dest_dir

                # 2. Alt tür bazlı hiyerarşi (Örn: Belgeler > PDF)
                if rules.get("by_sub_type"):
                    sub = DOC_SUBTYPES.get(ext, ext.lstrip(".").upper())
                    dest_dir = base_folder / category / sub
                    return category, sub, dest_dir

                # 3. Tek seviye kategori (Örn: Arşivler, Kurulum Dosyaları)
                dest_dir = base_folder / category
                return category, category, dest_dir

        return None

    def analyze(self, selected_folders: List[Path]) -> List[PlannedMove]:
        """
        Dry-Run: Dosyalara dokunmadan taşınacakları hiyerarşik hedefleri hesaplar.
        Yalnızca seçilen klasörlerin kökündeki dağınık dosyaları tarar;
        zaten oluşturulmuş kategori klasörlerine veya kısayollara (.lnk) dokunmaz.
        """
        planned_moves: List[PlannedMove] = []
        reserved_destinations: Set[Path] = set()

        for folder in selected_folders:
            if not folder.exists() or not folder.is_dir():
                continue

            try:
                entries = list(folder.iterdir())
            except PermissionError:
                continue

            for entry in entries:
                # Klasörleri, gizli/sistem dosyalarını ve sembolik linkleri atla
                if not entry.is_file() or entry.is_symlink():
                    continue
                if entry.name.lower() in IGNORED_FILES or entry.name.startswith("~$"):
                    continue

                classification = self._classify_file(entry, folder)
                if not classification:
                    continue

                category, sub_category, dest_dir = classification
                dest_path = self._resolve_collision(dest_dir, entry.name, reserved_destinations)
                reserved_destinations.add(dest_path)

                try:
                    size_bytes = entry.stat().st_size
                except OSError:
                    size_bytes = 0

                planned_moves.append(
                    PlannedMove(
                        source=entry,
                        destination=dest_path,
                        category=category,
                        sub_category=sub_category,
                        size_bytes=size_bytes,
                    )
                )

        return planned_moves

    @staticmethod
    def _resolve_collision(dest_dir: Path, filename: str, reserved: Set[Path]) -> Path:
        """Diskte veya aynı işlem planında çakışan dosya adlarını numaralandırır."""
        candidate = dest_dir / filename
        if not candidate.exists() and candidate not in reserved:
            return candidate

        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while True:
            candidate = dest_dir / f"{stem} ({counter}){suffix}"
            if not candidate.exists() and candidate not in reserved:
                return candidate
            counter += 1

    def execute_plan(self, moves: List[PlannedMove], undo_manager: UndoManager) -> Tuple[int, List[str]]:
        """Onaylanan planı uygular ve geri alınabilmesi için UndoManager'a kaydeder."""
        completed_moves: List[Tuple[Path, Path]] = []
        errors: List[str] = []

        for move in moves:
            try:
                move.destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(move.source), str(move.destination))
                completed_moves.append((move.source, move.destination))
            except Exception as e:
                errors.append(f"{move.source.name}: {e}")

        if completed_moves:
            undo_manager.record_batch(
                action_type="organize",
                description=f"{len(completed_moves)} dosya hiyerarşik olarak düzenlendi",
                moves=completed_moves,
            )

        return len(completed_moves), errors