import os
import psycopg2
import json
import time
import re
from dotenv import load_dotenv
from google import genai
from psycopg2.extras import RealDictCursor

# .env dosyasını yükle
load_dotenv()

# Gemini Yapılandırması
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = 'models/gemini-3.1-flash-lite-preview'

# Veritabanı Yapılandırması
db_config = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

# Çiçeksepeti'nin o meşhur geçersiz metni
GECERSIZ_METIN = "bu ürün için yalnızca puan verilmiştir yorum yapılmamıştır"

def gemini_puanla(yorum_metni):
    """Metni analiz eder ve 1-5 arası puan döndürür."""
    prompt = f"""
    Aşağıdaki kullanıcı yorumunu analiz et. 
    Metindeki duygu durumuna göre 1 ile 5 arasında bir puan ver.
    1: Çok Kötü, 2: Kötü, 3: Nötr, 4: İyi, 5: Mükemmel.
    
    KURAL: Sadece tek bir rakam döndür. Başka kelime yazma.
    
    Yorum: "{yorum_metni}"
    """
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        puan = response.text.strip()
        match = re.search(r'[1-5]', puan)
        return int(match.group()) if match else None
    except Exception as e:
        print(f"⚠️ API Hatası: {e}")
        return None

def eksikleri_tespit_et(dataset):
    """Mevcut veride her puandan kaç adet olduğunu sayar."""
    sayac = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for veri in dataset:
        puan = veri.get('orijinal_puan')
        if puan in sayac:
            sayac[puan] += 1

    eksikler = {puan: 1000 - adet for puan, adet in sayac.items() if adet < 1000}
    return eksikler

def operasyonu_tamamla():
    dosya_adi = "temizlenmis_egitim_verisi.json"

    # 1. Mevcut temizlenmiş veriyi yükle
    if os.path.exists(dosya_adi):
        with open(dosya_adi, "r", encoding="utf-8") as f:
            dataset = json.load(f)
    else:
        print("❌ Hata: 'etiketli_egitim_verisi.json' bulunamadı!")
        return

    # 2. Kaç tane eksik var hesapla
    eksik_tablosu = eksikleri_tespit_et(dataset)
    if not eksik_tablosu:
        print("✅ Veri seti zaten tam (her puandan 1000 adet var).")
        return

    print(f"📊 Eksik tablosu tespit edildi: {eksik_tablosu}")
    print("🔄 Eksikler Çiçeksepeti verileriyle tamamlanıyor...")

    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        for puan, miktar in eksik_tablosu.items():
            if miktar <= 0: continue

            # SQL: Çiçeksepeti'nden, geçersiz metin içermeyen, rastgele veriler
            sql = """
            WITH RankedReviews AS (
                SELECT p.product_name, p.platform, r.clean_text, r.rating_int,
                ROW_NUMBER() OVER (ORDER BY RANDOM()) as sira
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                WHERE p.platform = 'ciceksepeti'
                  AND r.rating_int = %s
                  AND r.clean_text IS NOT NULL
                  AND length(r.clean_text) > 15
                  AND r.clean_text NOT ILIKE %s
            )
            SELECT product_name, platform, clean_text, rating_int
            FROM RankedReviews WHERE sira <= %s;
            """

            cur.execute(sql, (puan, f"%{GECERSIZ_METIN}%", miktar))
            rows = cur.fetchall()

            print(f"📥 {puan} puan için {len(rows)} yeni veri çekildi. Gemini işliyor...")

            for i, row in enumerate(rows):
                # Python tarafında son bir güvenlik kontrolü
                if GECERSIZ_METIN in row['clean_text'].lower():
                    continue

                ai_puani = gemini_puanla(row['clean_text'])
                if ai_puani is not None:
                    dataset.append({
                        "urun_adi": row['product_name'],
                        "platform": row['platform'],
                        "yorum": row['clean_text'],
                        "orijinal_puan": row['rating_int'],
                        "gemini_puani": ai_puani
                    })

                # İlerleme kaydı (Her 10 veride bir)
                if i % 10 == 0 and i > 0:
                    with open(dosya_adi, "w", encoding="utf-8") as f:
                        json.dump(dataset, f, ensure_ascii=False, indent=4)

                time.sleep(0.1) # API limit koruması

        # 3. Final Kaydı
        with open(dosya_adi, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=4)

        print(f"🎉 Operasyon Başarıyla Tamamlandı! Toplam veri sayısı: {len(dataset)}")

    except Exception as e:
        print(f"❌ Hata oluştu: {e}")
    finally:
        if 'conn' in locals():
            cur.close()
            conn.close()

if __name__ == "__main__":
    operasyonu_tamamla()