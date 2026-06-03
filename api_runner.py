import argparse
import sys
# main.py içindeki operasyonel fonksiyonu içeri aktarıyoruz
# (Bunun çalışması için main.py içindeki menü kodlarının kesinlikle
# if __name__ == '__main__': bloğu içinde olması gerekir)
from main import baslat

if __name__ == "__main__":
    # Sadece API'den gelecek argümanları dinleyen yapı
    parser = argparse.ArgumentParser(description="C# Backend İçin ETL Tetikleyicisi")
    parser.add_argument("--url", type=str, required=True, help="Kazınacak ürünün tam linki")
    args = parser.parse_args()

    try:
        print(f"INFO - [API RUNNER] C# üzerinden tetiklendi. URL: {args.url}")

        # Süreci tek bir link için başlat
        link_listesi = [args.url]
        baslat(link_listesi)

        # C# tarafına işlemin hatasız bittiğini bildirmek için 0 koduyla çık
        sys.exit(0)
    except Exception as e:
        print(f"ERROR - [API RUNNER] Kritik hata: {e}")
        # C# tarafına işlemin patladığını bildirmek için 1 koduyla çık
        sys.exit(1)