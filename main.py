import time
from scraper import linkten_veri_cek
from Transformer import donustur_ve_kaydet
from db_manager import DatabaseManager  # Veritabanı yöneticimizi dahil ediyoruz

# İşlenecek linklerin listesi (links.txt dosyasından da okutabilirsin)
link_listesi = [
]

def baslat():
    print(f" Toplam {len(link_listesi)} link sıraya alındı. ETL Operasyonu başlıyor...\n")
    db = DatabaseManager()

    for i, link in enumerate(link_listesi, 1):
        print(f"[{i}/{len(link_listesi)}] İŞLENİYOR: {link}")

        try:
            # --- 1. AŞAMA: KAZIMA (EXTRACT) ---
            kazima_mesaji, ham_dosya_yolu = linkten_veri_cek(link)
            print(f"   [Scraper] {kazima_mesaji}")

            # Eğer kazıma başarısızsa (None döndüyse) bir sonraki linke geç
            if not ham_dosya_yolu:
                print("   [Atlanıyor] Ham dosya yolu oluşmadı.")
                continue


            # --- 2. AŞAMA: DÖNÜŞTÜRME (TRANSFORM) ---
            urun_paketi, yorum_paketleri = donustur_ve_kaydet(ham_dosya_yolu)
            print(f"   [Transformer] Veri standardize edildi: {urun_paketi.get('product_name', 'Bilinmeyen Ürün')}")


            # --- 3. AŞAMA: YÜKLEME (LOAD) ---
            print("   [Database] PostgreSQL'e kayıt işlemi başlatılıyor...")
            db.save_product_and_reviews(urun_paketi, yorum_paketleri)
            print("   [Başarılı] Veritabanı işlemi tamamlandı.")


        except Exception as e:
            print(f"   [HATA] Bu link işlenirken bir sorun oluştu: {e}")

        print("-" * 60)

        if i < len(link_listesi):
            time.sleep(3)

    print("\n BÜTÜN GÖREVLER TAMAMLANDI!")


if __name__ == "__main__":
    baslat()