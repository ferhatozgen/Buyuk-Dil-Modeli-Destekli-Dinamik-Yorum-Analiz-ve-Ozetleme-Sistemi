from functions.scraper import linkten_veri_cek
from functions.Transformer import donustur_ve_kaydet
from functions.db_manager import DatabaseManager
from functions.utils import url_cleaning, url_hashing, url_cozumle, yorumlara_puan_ver
import os
import concurrent.futures
from functions.logger import setup_logger
from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import pipeline, AutoTokenizer
import concurrent.futures

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


def tek_link_isle(ham_link: str, db: DatabaseManager, classifier) -> str:
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
        if not ham_dosya_yolu or not os.path.exists(ham_dosya_yolu):
            logger.error(f"   [HATA] Veri çekilemedi: {kazima_mesaji}")
            return "   [Atlanıyor] Ham veri dosyası bulunamadı."

        # --- 2. AŞAMA: DÖNÜŞTÜRME (TRANSFORM) ---
        urun_paketi, yorum_paketleri = donustur_ve_kaydet(
            ham_dosya_yolu,
            platform=platform,
            platform_id=platform_id,
            temiz_url=temiz_url,
            url_hash=url_hash
        )
        logger.info(f"   [Transformer] Veri dönüştürme işlemi tamamlandı: {urun_paketi.get('product_name', 'Bilinmeyen Ürün')}")
        #--- 3. Yorumlara puan verme işlemi
        if yorum_paketleri:
            logger.info(f"   [Predictor] {len(yorum_paketleri)} yorum ONNX modelinden geçiriliyor...")
            yorum_paketleri = yorumlara_puan_ver(classifier, yorum_paketleri)
            gecerli_puanlar = [y['predicted_score'] for y in yorum_paketleri if y.get('predicted_score') is not None]

            if gecerli_puanlar:
                ortalama = sum(gecerli_puanlar) / len(gecerli_puanlar)
                urun_paketi['avg_model_score'] = round(ortalama, 2)
                logger.info(f"   [Predictor] Ortalama model puanı hesaplandı: {urun_paketi['avg_model_score']}")
        else:
            logger.error("   [Predictor] Yorum paketi boş olduğu için model puanı hesaplanamadı.")
            urun_paketi['avg_model_score'] = None


        # --- 4. AŞAMA: YÜKLEME (LOAD) ---
        logger.info(f"   [Database] PostgreSQL'e kayıt işlemi başlatılıyor...")
        db.save_product_and_reviews(urun_paketi, yorum_paketleri)
        return "   [Başarılı] Veritabanı işlemi tamamlandı."
    except Exception as e:
        return f"   [HATA] Bu link işlenirken bir sorun oluştu: {e}"

def baslat(link_listesi):
    logger.info(f"Toplam {len(link_listesi)} link sıraya alındı. ETL Operasyonu başlıyor...")
    db = DatabaseManager()
    logger.info("ONNX modeli HF'den çekiliyor")
    MODEL_ID = "Halitbkts/berturk-review-score-predicter-model-onnx"
    try:
        model = ORTModelForSequenceClassification.from_pretrained(MODEL_ID)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)
    except Exception as e:
        logger.error(f"ONNX modeli yüklenirken bir hata oluştu: {e}")
        return
    MAX_WORKERS = 1

    #--- Paralel işleme için ThreadPoolExecutor kullanarak her linki tek_link_isle fonksiyonuna gönderiyoruz ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        # 1. Her link için tek_link_isle fonksiyonunu çalıştıracak şekilde görevler oluşturuyoruz
        future_to_link = {executor.submit(tek_link_isle, ham_link, db,classifier): ham_link for ham_link in link_listesi}

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
    manuel_liste = ["https://www.yemeksepeti.com/restaurant/jel7/lavas-center-jel7",
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

