import os
import json
import time
import requests
from functions.db_manager import DatabaseManager
from functions.logger import setup_logger

logger = setup_logger()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-3.1-flash-lite"  # Şema desteği v1beta endpointlerinde bu modelle kusursuz çalışır


def get_aspects(kategori):
    """Kategoriye ait aspect havuzunu JSON dosyasından çeker."""
    dosya_yolu = os.path.join("Dicts", "yorum_kategorileri.json")
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(kategori, [])
    except Exception as e:
        logger.error(f"❌ Aspect dosyası okunamadı: {e}")
        return []


def prompt_olustur(aspect_havuzu, yorum_batch):
    """Gemini için 5'li batch promptu hazırlar."""
    yorumlar_json = json.dumps([{"id": i, "metin": y} for i, y in enumerate(yorum_batch)], ensure_ascii=False, indent=2)
    aspects_str = ", ".join(aspect_havuzu)

    prompt = f"""
Sen bir Veri Etiketleme ve NLP uzmanısın. Görevin, verilen müşteri yorumlarını anlamsal bütünlüğüne göre alt parçalara (chunk) bölmek ve her bir parçayı belirtilen "Kategori Havuzu"ndan en uygun olanıyla eşleştirmektir.

KATEGORİ HAVUZU:
[{aspects_str}]

KURALLAR:
1. Yorumu sadece anlamın değiştiği yerlerden böl (Örn: bağlaçlar, different konulara geçiş).
2. Her parça için havuzdan SADECE BİR kategori seç. Havuza uymayan genel ifadeler veya selamlama varsa "Genel" kategorisini kullan.

GİRDİ YORUMLARI:
{yorumlar_json}
"""
    return prompt


def gemini_rest_call(prompt):
    """Google'ın Structured Outputs (Response Schema) mimarisini kullanarak istek atar."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}

    # --- KRİTİK ADIM: Gemini'ı Sadece Bu JSON Şemasını Üretmeye Zorluyoruz ---
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "id": {"type": "INTEGER"},
                        "analiz": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "parca": {"type": "STRING"},
                                    "kategori": {"type": "STRING"}
                                },
                                "required": ["parca", "kategori"]
                            }
                        }
                    },
                    "required": ["id", "analiz"]
                }
            }
        }
    }

    response = requests.post(url, headers=headers, json=payload, timeout=45.0)

    if response.status_code == 200:
        res_json = response.json()
        text_output = res_json['candidates'][0]['content']['parts'][0]['text']
        return text_output
    else:
        raise Exception(f"Google API Hatası (Kod: {response.status_code}): {response.text}")


def veri_seti_uret(kategori="elektronik_teknoloji", limit=2000, batch_size=5):
    aspect_havuzu = get_aspects(kategori)
    if not aspect_havuzu:
        logger.warning(f"⚠️ {kategori} için aspect havuzu bulunamadı, işlem iptal ediliyor.")
        return

    os.makedirs("Datasets", exist_ok=True)
    dosya_yolu = os.path.join("Datasets", f"{kategori}_train.jsonl")

    zaten_uretilen = 0
    if os.path.exists(dosya_yolu):
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            zaten_uretilen = sum(1 for _ in f)

    kalan_limit = limit - zaten_uretilen
    if kalan_limit <= 0:
        logger.info(f"✅ {kategori} zaten tamamen tamamlanmış ({zaten_uretilen}/{limit}). Atlanıyor.")
        return

    db = DatabaseManager()

    query = f"""
        SELECT r.clean_text 
        FROM reviews r
        JOIN products p ON r.product_id = p.id
        WHERE p.category = '{kategori}'
        AND LENGTH(r.clean_text) > 30 
        ORDER BY r.id
        LIMIT {kalan_limit} OFFSET {zaten_uretilen}
    """

    try:
        logger.info(f"📊 {kategori} için veritabanından kalan {kalan_limit} yorum çekiliyor... (Mevcut: {zaten_uretilen})")
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                yorumlar = [row[0] for row in cur.fetchall()]

        if not yorumlar:
            logger.warning(f"⚠️ {kategori} için işlenecek yeni veri bulunamadı.")
            return

        basarili_kayit = zaten_uretilen
        i = 0
        retry_count = 0
        max_retries = 3

        while i < len(yorumlar):
            batch = yorumlar[i:i + batch_size]
            prompt = prompt_olustur(aspect_havuzu, batch)

            # İlerleme logunu hem listenin indisine (i) hem de mevcut konuma göre netleştiriyoruz
            logger.info(f"🚀 Batch işleniyor: {zaten_uretilen + i} - {zaten_uretilen + i + len(batch)} / {limit} (Deneme: {retry_count + 1})")

            try:
                # Şemalı çağrı yaptığımız için gelen veri doğrudan tertemiz bir JSON stringidir
                raw_response_text = gemini_rest_call(prompt)
                analiz_sonuclari = json.loads(raw_response_text)

                with open(dosya_yolu, "a", encoding="utf-8") as f:
                    for sonuc in analiz_sonuclari:
                        idx = sonuc.get("id")
                        if idx is not None and idx < len(batch):
                            orijinal_yorum = batch[idx]
                            etiketler = sonuc.get("analiz", [])

                            egitim_satiri = {
                                "messages": [
                                    {"role": "system",
                                     "content": f"Yorumu parçalara ayır ve şu kategorilerden biriyle eşleştir: {', '.join(aspect_havuzu)}"},
                                    {"role": "user", "content": orijinal_yorum},
                                    {"role": "assistant", "content": json.dumps(etiketler, ensure_ascii=False)}
                                ]
                            }
                            f.write(json.dumps(egitim_satiri, ensure_ascii=False) + "\n")
                            basarili_kayit += 1

                # Başarılı geçiş
                i += batch_size
                retry_count = 0
                time.sleep(1.2)

            except Exception as batch_err:
                retry_count += 1
                logger.error(f"❌ Batch Hatası ({zaten_uretilen + i}-{zaten_uretilen + i + len(batch)}): {batch_err}")

                if retry_count >= max_retries:
                    # BURASI DÜZELTİLDİ: Atlanan batch durumunda sayaçların doğru kayması sağlandı
                    logger.warning(f"⚠️ {zaten_uretilen + i} konumundaki batch çözülemedi. Pas geçiliyor!")
                    i += batch_size
                    retry_count = 0
                    time.sleep(2)
                else:
                    logger.info("⏳ 5 saniye sonra tekrar denenecek...")
                    time.sleep(5)
                    continue

        logger.info(f"✅ {kategori} için toplam {basarili_kayit} adet eğitim verisi hazır.")

    except Exception as e:
        logger.error(f"❌ Veritabanı Hatası: {e}")
    finally:
        if hasattr(db, 'close_pool'):
            db.close_pool()


def tum_verisetlerini_uret(hedef_limit=2000, batch_size=5):
    """Kalan kategoriler için sırayla eğitim veri seti üretir."""
    kategoriler = [
        "gezilecek_yer", "egitim_eglence", "kurumsal", "pet_shop"
    ]

    toplam_kategori = len(kategoriler)
    logger.info(f"🚀 ÜRETİM BAŞLIYOR: Kalan {toplam_kategori} kategori işlenecek.")

    for index, kategori in enumerate(kategoriler, 1):
        logger.info(f"\n{'=' * 50}\n[{index}/{toplam_kategori}] 🟢 SIRADAKİ KATEGORİ: {kategori.upper()}\n{'=' * 50}")

        try:
            veri_seti_uret(kategori=kategori, limit=hedef_limit, batch_size=batch_size)

            if index < toplam_kategori:
                bekleme_suresi = 10
                logger.info(f"⏳ {kategori} aşaması geçildi. Sıradaki için {bekleme_suresi} saniye bekleniyor...")
                time.sleep(bekleme_suresi)

        except Exception as e:
            logger.error(f"❌ {kategori} üretiminde KRİTİK HATA: {e}. Diğer kategoriye geçiliyor.")
            continue

    print("\n🎉 BÜTÜN KATEGORİLER İÇİN ALTIN VERİ SETİ ÜRETİMİ BAŞARIYLA TAMAMLANDI!")


if __name__ == "__main__":
    tum_verisetlerini_uret(hedef_limit=2000, batch_size=5)