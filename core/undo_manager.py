import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from config import HISTORY_FILE, LOGS_DIR


class UndoManager:
    """Dosya taşıma ve güvenli silme işlemlerinin kaydını tutar ve geri alır."""

    def __init__(self, history_file: Path = HISTORY_FILE):
        self.history_file = history_file
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._save_data([])

    def _load_data(self) -> List[Dict]:
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _save_data(self, data: List[Dict]):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def record_batch(self, action_type: str, description: str, moves: List[Tuple[Path, Path]]):
        """
        Başarıyla tamamlanan bir işlem grubunu kaydeder.
        moves: [(eski_yol, yeni_yol), ...]
        """
        if not moves:
            return

        now = datetime.now()
        batch = {
            "id": now.strftime("%Y%m%d_%H%M%S_%f"),
            "timestamp": now.strftime("%d.%m.%Y %H:%M:%S"),
            "action_type": action_type,
            "description": description,
            "moves": [{"src": str(src), "dst": str(dst)} for src, dst in moves],
        }

        data = self._load_data()
        data.insert(0, batch)  # En son yapılan işlem en üstte olsun
        self._save_data(data)

    def get_history(self) -> List[Dict]:
        return self._load_data()

    def undo_batch(self, batch_id: str) -> Tuple[int, List[str]]:
        """
        Belirtilen işlem grubunu tersine çevirerek dosyaları eski konumuna taşır.
        Dönüş: (geri_alınan_dosya_sayısı, hata_mesajları)
        """
        data = self._load_data()
        target_batch = next((b for b in data if b["id"] == batch_id), None)
        if not target_batch:
            return 0, ["İşlem kaydı bulunamadı."]

        restored_count = 0
        errors: List[str] = []
        created_dirs_to_check = set()

        for item in reversed(target_batch["moves"]):
            src = Path(item["src"])  # Orijinal konum
            dst = Path(item["dst"])  # Taşındığı mevcut konum

            if not dst.exists():
                errors.append(f"Mevcut konumda bulunamadı: {dst.name}")
                continue

            try:
                src.parent.mkdir(parents=True, exist_ok=True)
                target_restore = src
                if target_restore.exists():
                    # Orijinal konumda aynı isimde yeni bir dosya oluşmuşsa üzerine yazma
                    target_restore = src.parent / f"{src.stem}_gerialindi{src.suffix}"

                created_dirs_to_check.add(dst.parent)
                shutil.move(str(dst), str(target_restore))
                restored_count += 1
            except Exception as e:
                errors.append(f"{dst.name} geri alınamadı: {e}")

        # Düzenleme sırasında oluşmuş ve şimdi boş kalan alt klasörleri temizle
        for folder in sorted(created_dirs_to_check, key=lambda p: len(p.parts), reverse=True):
            self._cleanup_empty_parents(folder)

        # Kaydı geçmişten kaldır
        updated_data = [b for b in data if b["id"] != batch_id]
        self._save_data(updated_data)

        return restored_count, errors

    @staticmethod
    def _cleanup_empty_parents(folder: Path, max_depth: int = 3):
        """Geri alma sonrası tamamen boş kalan kategori klasörlerini temizler."""
        current = folder
        for _ in range(max_depth):
            try:
                if current.exists() and current.is_dir() and not any(current.iterdir()):
                    current.rmdir()
                    current = current.parent
                else:
                    break
            except OSError:
                break