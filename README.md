# Akıllı Bilgisayar Düzenleyici (BFM CORE)

Windows 10 ve 11 için Python & CustomTkinter ile geliştirilmiş; dosya düzenleme, kopya/büyük dosya temizliği, görsel masaüstü yerleşimi ve kullanılmayan kurulum/program temizliği sunan masaüstü aracı.

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![Geliştirici](https://img.shields.io/badge/Geli%C5%9Ftirici-BFM%20CORE-0ea5e9)

---

## Öne Çıkan Özellikler

* **Kullanıcı Tanımlı Klasör Seçimi:** Yalnızca seçtiğiniz klasörleri (Masaüstü, İndirilenler, Belgeler veya özel klasörler) tarar.
* **Akıllı & Hiyerarşik Düzenleyici:** Görselleri ve videoları `Yıl / Ay` klasörlerine, belgeleri ise `PDF`, `Word`, `Excel`, `Sunum`, `Metin` alt klasörlerine ayırır.
* **Önizleme (Dry-Run) & Geri Al (Undo):** Dosyaları taşımadan önce kategori bazlı önizleme ve onay sunar; yapılan tüm işlemleri tek tıkla geri alabilir.
* **Güvenli Çöp Kutusu:** Silinen kurulum veya kopya dosyalarını kalıcı silmek yerine Masaüstündeki `Güvenli Çöp Kutusu` klasörüne taşır.
* **Kopya & Büyük Dosya Bulucu:** SHA-256 ile birebir kopya dosyaları bulur, büyük dosyaların ne işe yaradığını ve bilgisayarda kurulu olup olmadığını analiz eder. (`.git`, `venv`, `node_modules` gibi proje klasörlerini otomatik korur.)
* **Görsel Masaüstü Tasarımcısı:** Masaüstü önizlemesi üzerinde fareyle kutular çizerek masaüstü simgelerini taşmadan yan yana hizalar; eski düzene tek tıkla geri döner.
* **Kurulum & Uygulama Temizleyici:** Eski `.exe` / `.msi` kurulum paketlerini temizler ve uzun süredir kullanılmayan programları listeler (sistem sürücülerini korur).

---

## İndirme ve Kurulumsuz Kullanım (.exe)

Python kurmanıza gerek kalmadan doğrudan kullanmak için:
1. [Releases sayfasından](https://github.com/BFM-lab/akilli-pc-duzenleyici/releases) **`AkilliPCDuzenleyici.exe`** dosyasını indirin.
2. Çift tıklayarak çalıştırın.

> **Windows SmartScreen Notu:** Uygulama bireysel olarak geliştirildiği ve ücretli dijital yayıncı sertifikası bulunmadığı için Windows ilk açılışta *"Bilinmeyen Yayıncı"* uyarısı gösterebilir. **"Ek bilgi > Yine de çalıştır"** seçeneğiyle açabilirsiniz. Tüm kaynak kodu incelemeniz için bu depoda açıktır.

---

## Geliştiriciler İçin Kaynak Koddan Çalıştırma

```bash
git clone https://github.com/BFM-lab/akilli-pc-duzenleyici.git
cd akilli-pc-duzenleyici
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py