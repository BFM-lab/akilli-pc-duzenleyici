import shutil
from pathlib import Path
from core.path_helper import get_safe_trash_path


def ensure_safe_trash_exists() -> Path:
    """Masaüstündeki 'Güvenli Çöp Kutusu' klasörünü yoksa oluşturur ve yolunu döner."""
    trash_dir = get_safe_trash_path()
    trash_dir.mkdir(parents=True, exist_ok=True)
    return trash_dir


def get_unique_destination(dest_dir: Path, filename: str) -> Path:
    """Hedef klasörde aynı isimde dosya varsa sonuna (1), (2) ekleyerek benzersiz yol üretir."""
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def move_to_safe_trash(file_path: Path) -> Path:
    """
    Verilen dosyayı kalıcı olarak silmek yerine Masaüstündeki
    'Güvenli Çöp Kutusu' klasörüne taşır. Yeni yolu döndürür.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

    trash_dir = ensure_safe_trash_exists()
    dest_path = get_unique_destination(trash_dir, file_path.name)
    shutil.move(str(file_path), str(dest_path))
    return dest_path