import time
from scraper import linkten_veri_cek
from Transformer import donustur_ve_kaydet
from db_manager import DatabaseManager  # Veritabanı yöneticimizi dahil ediyoruz

# İşlenecek linklerin listesi (links.txt dosyasından da okutabilirsin)
link_listesi = [
    "https://www.google.com/maps/place/ER-VET+VETER%C4%B0NER+KL%C4%B0N%C4%B0K/@40.656557,29.2773589,18.01z/data=!4m6!3m5!1s0x14cae529f19ddcef:0x9f2f6df25573435f!8m2!3d40.6569338!4d29.2771099!16s%2Fg%2F11dfjb8qtw?entry=ttu&g_ep=EgoyMDI2MDQxNC4wIKXMDSoASAFQAw%3D%3D",
    "https://www.ciceksepeti.com/sari-kurdeleli-yesil-vazoda-rengarenk-gerberalar-at5801",
    "https://www.yemeksepeti.com/restaurant/vqv7/kofteci-yusuf-vqv7",
    "https://tgoyemek.com/restoranlar/145132",
    "https://store.steampowered.com/app/730/CounterStrike_2/"

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