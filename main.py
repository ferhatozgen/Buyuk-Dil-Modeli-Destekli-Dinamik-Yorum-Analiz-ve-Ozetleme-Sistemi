import time
from scraper import linkten_veri_cek
from Transformer import donustur_ve_kaydet
from db_manager import DatabaseManager
from utils import url_cleaning, url_hashing, url_cozumle
import os
import concurrent.futures
from logger import setup_logger

logger = setup_logger()


def linkleri_dosyadan_oku(dosya_yolu: str) -> list[str]:
    if not os.path.exists(dosya_yolu):
        logger.error(f"'{dosya_yolu}' dosyası bulunamadı. Lütfen dosya yolunu kontrol edin.")
        return []

    temiz_linkler = []
    try:
        with open(dosya_yolu, 'r', encoding='utf-8') as dosya:
            for satir in dosya:
                link = satir.strip()

                if link and not link.startswith('#'):
                    temiz_linkler.append(link)

        return temiz_linkler

    except Exception as e:
        logger.error(f"Dosya okuma hatası: {e}")
        return []


def tek_link_isle(ham_link: str, db: DatabaseManager) -> str:
    try:
        temiz_url = url_cleaning(ham_link)
        url_hash = url_hashing(temiz_url)
        platform, platform_id = url_cozumle(temiz_url)
        if not platform:
            return "   [Atlanıyor] Platform tanımlanamadı."
        if db.is_exist_in_db(url_hash):
            return "   [Atlanıyor] Bu ürün zaten veritabanında mevcut."

        #--- 1. AŞAMA: ÇEKME (EXTRACT) ---
        kazima_mesaji, ham_dosya_yolu = linkten_veri_cek(temiz_url, platform)
        if not ham_dosya_yolu:
            return "   [Atlanıyor] Ham dosya yolu oluşmadı."

        # --- 2. AŞAMA: DÖNÜŞTÜRME (TRANSFORM) ---
        urun_paketi, yorum_paketleri = donustur_ve_kaydet(
            ham_dosya_yolu,
            platform=platform,
            platform_id=platform_id,
            temiz_url=temiz_url,
            url_hash=url_hash
        )
        logger.info(f"   [Transformer] Veri dönüştürme işlemi tamamlandı: {urun_paketi.get('product_name', 'Bilinmeyen Ürün')}")
        # --- 3. AŞAMA: YÜKLEME (LOAD) ---
        logger.info(f"   [Database] PostgreSQL'e kayıt işlemi başlatılıyor...")
        db.save_product_and_reviews(urun_paketi, yorum_paketleri)
        return "   [Başarılı] Veritabanı işlemi tamamlandı."
    except Exception as e:
        return f"   [HATA] Bu link işlenirken bir sorun oluştu: {e}"

def baslat(link_listesi):
    logger.info(f"Toplam {len(link_listesi)} link sıraya alındı. ETL Operasyonu başlıyor...")
    db = DatabaseManager()

    MAX_WORKERS = 4

    #--- Paralel işleme için ThreadPoolExecutor kullanarak her linki tek_link_isle fonksiyonuna gönderiyoruz ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        # 1. Her link için tek_link_isle fonksiyonunu çalıştıracak şekilde görevler oluşturuyoruz
        future_to_link = {executor.submit(tek_link_isle, ham_link, db): ham_link for ham_link in link_listesi}

        # 2. Görevler tamamlandıkça sonuçları alıyoruz
        finished_count = 0
        for finished_task in concurrent.futures.as_completed(future_to_link):
            finished_count += 1
            original_link = future_to_link[finished_task]
            try:
                result_message = finished_task.result()
                logger.info(f"[{finished_count}/{len(link_listesi)}] {original_link} - {result_message}")
            except Exception as e:
                logger.error(f"[{finished_count}/{len(link_listesi)}] {original_link} - [HATA] İşlem sırasında bir hata oluştu: {e}")



    print("\n BÜTÜN GÖREVLER TAMAMLANDI!")

    db.close_pool()


if __name__ == "__main__":
    manuel_liste = [
    ]
    txt_dosya_yolu = "linkler.txt"

    print("\n" + "*" * 50)
    print("  BÜYÜK DİL MODELİ DESTEKLİ ETL BORU HATTI")
    print("*" * 50)
    print("Lütfen veri kaynağını seçin:")
    print("1 - Kodun içindeki Manuel Listeden Oku (Test)")
    print(f"2 - '{txt_dosya_yolu}' Dosyasından Oku (Production)")
    print("0 - Çıkış")
    print("*" * 50)
    while True:
        secim = input("Seçiminiz (0/1/2): ").strip()

        if secim == "1":
            print("\n🔄 Manuel liste seçildi. Hazırlanıyor...")
            baslat(manuel_liste)
            break

        elif secim == "2":
            print(f"\n🔄 {txt_dosya_yolu} dosyası okunuyor...")
            okunan_linkler = linkleri_dosyadan_oku(txt_dosya_yolu)
            baslat(okunan_linkler)
            break

        elif secim == "0":
            print("\n👋 Çıkış yapılıyor. İyi çalışmalar!")
            break

        else:
            print("❌ Geçersiz seçim! Lütfen 0, 1 veya 2 tuşlayın.")

