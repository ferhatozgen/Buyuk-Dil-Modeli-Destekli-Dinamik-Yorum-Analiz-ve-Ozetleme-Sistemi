from rapidfuzz import process, fuzz
from urllib.parse import urlparse, urlunparse
import urllib.parse
import hashlib
import re
import logging
import json
from config import URUN_GRUP_SEMALARI
import cloudinary.uploader
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from datetime import datetime, timedelta
import dateparser
import asyncio
import aiohttp
from pydantic import BaseModel
from functions.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

# .env dosyasını yükle
load_dotenv()

# Bilgileri .env'den güvenli bir şekilde çek
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

def upload_to_cloudinary(image_url: str) -> str:
    """Dışarıdan gelen resim linkini Cloudinary'ye yükler ve kalıcı linki döner."""
    if not image_url or image_url == "Görsel Bulunamadı":
        return "Görsel Bulunamadı"

    try:
        # Resmi URL üzerinden direkt Cloudinary sunucularına çekiyoruz
        response = cloudinary.uploader.upload(image_url, folder="vividai_products")
        return response.get("secure_url", image_url)
    except Exception as e:
        print(f"⚠️ Cloudinary Yükleme Hatası: {e}")
        # Yükleme başarısız olursa en azından orijinal URL'yi geri döndür
        return image_url

def url_cleaning(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    cleaned_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', '')) # Sadece temel URL'yi alır, query ve fragment'ı atar
    return cleaned_url

# stringi utf-8 formatında byte dizisine çeviriyor çünkü hex fonksiyonları string değil byte dizileriyle çalışır.
def url_hashing(clean_url: str) -> str:
    return hashlib.sha256(clean_url.encode('utf-8')).hexdigest()


def ciceksepeti_kategori_hibrit(urun_adi):
    if not urun_adi:
        return "hediyelik_esya"

    # 1. ÖN İŞLEME (Normalization)
    # Küçük harf ve gereksiz boşluk temizliği
    text = urun_adi.lower().strip()

    # Kategori Anahtarları (Regex için | ile birleştirilmiş, Fuzzy için liste)
    keywords = {
        "yenilebilir_cicek": [
            "kek", "çikolata", "cikolata", "truf", "trüf", "draje", "kahve",
            "gurme", "lezzet", "bonnyfood", "atıştırmalık", "atıstırmalık",
            "atistirmalik", "dondurma", "meyve sepeti", "gurme"
        ],
        "cicek": [
            "gül", "gul", "papatya", "orkide", "buket", "saksı", "saksi",
            "aranjman", "teraryum", "gerbera", "lilyum", "bitki", "kalanchoe",
            "spatifilyum", "husnuyusuf", "hüsnüyusuf", "karanfil"
        ]
    }

    # --- KATMAN 1: REGEX (HIZLI YOL) ---
    # Eğer kelime tam doğru yazılmışsa Fuzzy ile vakit kaybetmeyelim.
    for cat_name, words in keywords.items():
        # Kelime köklerini yakalayan regex pattern (kek, kekler, kekli yakalar)
        pattern = r"\b(" + "|".join(words) + r")"
        if re.search(pattern, text):
            return cat_name

    # --- KATMAN 2: FUZZY MATCHING (GÜVENLİ YOL / FALLBACK) ---
    # Regex bulamadıysa, yazım hatası ihtimaline karşı bulanık eşleme yapalım.
    # Ürün adını kelimelere bölüp her kelimeyi kontrol ediyoruz.
    word_list = text.split()

    # Öncelik hiyerarşisini koruyoruz (Önce Yenilebilir)
    for cat_name in ["yenilebilir_cicek", "cicek"]:
        for target_word in keywords[cat_name]:
            # extractOne en yakın kelimeyi bulur. [1] skoru verir.
            # limit=90 yaparak yanlış eşleşmeleri (False Positive) engelliyoruz.
            match = process.extractOne(target_word, word_list, scorer=fuzz.WRatio)
            if match and match[1] >= 90:  # 90 yüksek doğruluk için idealdir
                return cat_name

    # --- KATMAN 3: VARSAYILAN ---
    return "hediyelik_esya"


def url_cozumle(url : str) -> tuple[str, str]  :
    url_lower = url.lower()
    platform = None

    if "tgo" in url_lower or "trendyol-yemek" in url_lower or "/go/" in url_lower:
        platform = "trendyol-go"
    elif "trendyol.com" in url_lower:
        platform = "trendyol"
    elif "hepsiburada.com" in url_lower:
        platform = "hepsiburada"
    elif "ciceksepeti.com" in url_lower:
        platform = "ciceksepeti"
    elif "steampowered.com" in url_lower:
        platform = "steam"
    elif "airbnb.com" in url_lower:
        platform = "airbnb"
    elif "yemeksepeti.com" in url_lower:
        platform = "yemeksepeti"
    elif "etstur.com" in url_lower:
        platform = "etstur"
    elif "googleusercontent.com/maps" in url_lower or "/maps/" in url_lower:
        platform = "maps"
    else:
        raise ValueError("Platform bulunamadı")

    if platform == "maps":
        # regex yöntemiyle id yakalama işlemi (ilk deneme)
        match = re.search(r'/place/([^/?]+)', url)
        if match:
            return platform, urllib.parse.unquote(match.group(1))

        # string parçalama yöntemiyle urlnin sonundan id yakalama işlemi (ikinci deneme)
        path_segment = url.strip('/').split('/')  #strip / işaretlerinden temizler,  splitte / işaretlerinden ayırır liste yapar urlyi
        if path_segment:
            last_segment = path_segment[-1]
            clean_id = last_segment.split('?')[0]     #linkin sonunda bazen idden sonra ?authuser=0 gibi uzun parametreler olur bu yazımdan urlyi temizlemek için
            return platform, (clean_id if clean_id else "unknown")

    patterns = {
        "trendyol": r"-p-(\d+)",
        "hepsiburada": r"-p[m]?-([A-Za-z0-9]+)",
        "ciceksepeti": r"-([a-zA-Z0-9]+)(?:\?|/|$)",
        "steam": r"/app/(\d+)",
        "airbnb": r"/rooms/(\d+)",
        "yemeksepeti": r"/restaurant/([a-zA-Z0-9]+)",
        "trendyol-go": r"(?:-|/)(\d+)(?:/|\?|$)",
        "etstur": r"etstur\.com/([^/?]+)"  # Etstur'da genelde otel adı ID yerine geçer
    }

    if platform in patterns:
        match = re.search(patterns[platform], url)
        if match:
            return platform, match.group(1)

    return platform, "Unknown"



def kategori_grupla(ham_liste):
    if not ham_liste:
        return "diger"
        
    tam_metin = " ".join(ham_liste).lower()
    
    if any(x in tam_metin for x in ["kedi", "köpek", "petshop", "maması", "catnip", "vitamini"]): return "pet_shop"
    if any(x in tam_metin for x in ["masa tenisi", "raketi", "futbol forması", "dambıl", "kondisyon"]): return "spor_outdoor"
    if any(x in tam_metin for x in ["akıllı saat", "akilli saat", "apple watch", "galaxy watch"]): return "elektronik_teknoloji"
    if any(x in tam_metin for x in ["bebek", "zıbın", "emzik", "puset", "oyuncak", "lego", "puzzle"]): return "anne_bebek_oyuncak"
    if any(x in tam_metin for x in ["toka", "kolye", "bileklik", "küpe", "yüzük", "tesbih", "takı","çanta", "cüzdan", "valiz", "bavul"]): return "aksesuar_taki"
    
    gruplar = {
        "giyim_ayakkabi": ["t-shirt", "jean", "pantolon", "ceket", "mont", "sweatshirt", "gömlek", "kazak", "tayt", "bot", "sneaker", "terlik", "ayakkabı", "pijama", "forma", "eşofman", "çorap", "korse", "şal", "bone","elbise","giyim"],
        "ev_yasam_mobilya": ["fırın", "tencere", "kahve makinesi", "su sebili", "ütü", "süpürge", "mobilya", "yatak", "havlu", "perde", "askılık", "dolap", "masa", "koltuk", "alez", "yastık", "ayna", "mutfak", "termos", "armatür", "sehpa","ev gereçleri","aydınlatma","yorgan","ev","teskstil"],
        "kirtasiye_kitap_hobi": ["kalem", "defter", "boya", "oyun", "enstrüman", "kitap", "ofis", "nargile", "plak", "mızıka", "kalimba", "tuval", "düğme", "ip", "kağıt", "dosya", "kar küresi", "hediyelik","bijuteri","hobi",],
        "kozmetik_kisisel_bakim": ["şampuan", "krem", "parfüm", "tıraş", "makyaj", "ruj", "cilt", "maskara", "oje", "fondöten", "manikür", "fırça", "parlatıcı", "deodorant", "diş", "bakım", "temizleme"],
        "elektronik_teknoloji": ["tablet", "laptop", "bilgisayar", "telefon", "kulaklık", "hoparlör", "tv", "kamera", "ssd", "usb", "bellek", "ekran koruyucu", "şarj", "batarya", "kumanda", "uydu", "kablo", "mouse", "klavye","elektrikli ev aletleri","ocak","davlumbaz","beyaz eşya","elektronik","ev elektroniği"],
        "spor_outdoor": ["futbol", "bisiklet", "kamp", "fitness", "dambıl", "scooter", "spor", "olta", "mat", "pompa", "raket", "voleybol", "fener", "dalış"],
        "supermarket_gida": ["kakao", "kahve", "zeytin", "peynir", "atıştırmalık", "çikolata", "bisküvi", "içecek", "su", "baharat", "zeytinyağı", "gıda", "deterjan","baharat"]
    }

    skorlar = {g: 0 for g in gruplar.keys()}
    
    for i, kat_adi in enumerate(reversed(ham_liste)):
        temiz_kat = kat_adi.lower().strip()
        agirlik = 25 if i == 0 else (15 if i == 1 else 1)
        
        for grup, anahtar_kelimeler in gruplar.items():
            for anahtar in anahtar_kelimeler:
                if anahtar in temiz_kat:
                    skorlar[grup] += agirlik

    max_skor = max(skorlar.values())
    return max(skorlar, key=skorlar.get) if max_skor > 0 else "diger"

def yorumlara_puan_ver(classifier, yorum_paketleri):
    if not yorum_paketleri:
        logger.warning("tahmin yapılacak yorum bulunamadı, boş liste dönd3ürülüyor.")
        return []

    texts = [yorum.get("clean_text", '') for yorum in yorum_paketleri]

    logger.info(f"MODEL {len(texts)} yorum için tahmin yapıyor...")
    results = classifier(texts, batch_size=32, truncation=True, max_length=512)

    for i in range(len(yorum_paketleri)):
        try:
            raw_label = results[i]['label']
            score = int(raw_label.split('_')[1]) + 1

            yorum_paketleri[i]['predicted_score'] = score
        except Exception as e:
            logger.error(f"Yorum puanlama hatası: {e}. Yorum: {yorum_paketleri[i]}")
            yorum_paketleri[i]['predicted_score'] = 0  # Hata durumunda puanı 0 yaparak devam ediyoruz

    test_scores = [y.get('predicted_score') for y in yorum_paketleri[:3]]
    logger.info(f"Örnek tahmin skorları: {test_scores} (ilk 3 yorum)")

    return yorum_paketleri


def parse_review_date(date_str) -> datetime:
    if not date_str:
        return datetime.now()

    # --- YENİ EKLENEN KISIM: Unix Timestamp Kontrolü ---
    # Gelen değer int, float veya sadece rakamlardan oluşan bir string ise:
    if isinstance(date_str, (int, float)) or (isinstance(date_str, str) and date_str.isdigit()):
        try:
            timestamp = float(date_str)
            # Eğer 13 haneli (milisaniye) bir değerse saniyeye çevir (Örn: Trendyol)
            if timestamp > 1e11:
                timestamp /= 1000.0
            return datetime.fromtimestamp(timestamp)
        except Exception as e:
            logger.warning(f"Timestamp dönüştürülemedi: {date_str} - Hata: {e}")
            pass # Hata olursa normal metin bazlı tarih mantığına devam etsin
    # ----------------------------------------------------

    date_str = str(date_str).lower().strip()

    # 1. Göreceli Tarih Kontrolü (Maps vb. platformlar için)
    match = re.search(r'(\d+)\s*(gün|hafta|ay|yıl|saat|dakika)\s*önce', date_str)
    if match:
        deger = int(match.group(1))
        birim = match.group(2)

        if birim == 'gün': return datetime.now() - timedelta(days=deger)
        elif birim == 'hafta': return datetime.now() - timedelta(weeks=deger)
        elif birim == 'ay': return datetime.now() - timedelta(days=deger * 30) # Ortalama 30 gün
        elif birim == 'yıl': return datetime.now() - timedelta(days=deger * 365)
        elif birim == 'saat': return datetime.now() - timedelta(hours=deger)
        elif birim == 'dakika': return datetime.now() - timedelta(minutes=deger)

    # 2. Normal Tarih Kontrolü (Trendyol, Hepsiburada vb.)
    # dateparser kütüphanesi Türkçe ayları (Mayıs, Ekim vb.) otomatik anlar
    parsed_date = dateparser.parse(date_str, languages=['tr', 'en'])
    if parsed_date:
        return parsed_date

    # Hiçbirine uymazsa anlık zamanı dön
    return datetime.now()

VLLM_QWEN_SERVER_URL = os.getenv("VLLM_QWEN_SERVER_URL", "http://0.0.0.0:8000")
VLLM_QWEN_MODEL_NAME = "Halitbkts/qwen-categorier"

async def _tekil_vllm_istegi(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, system_prompt:str, yorum_metni:str) -> dict:
    url = f"{VLLM_QWEN_SERVER_URL}/v1/chat/completions"

    payload = {
        "model" : VLLM_QWEN_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": yorum_metni}
        ],
        "temperature": 0.1,
        "top_p": 0.9,
        "max_tokens": 2048,
    }

    async with semaphore:
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as response:
                if response.status != 200:
                    hata_metni = await response.text()
                    logger.error(f"VLLM isteği başarısız oldu. Status: {response.status}, Hata: {hata_metni}")
                    return {"orijinal_yorum": yorum_metni, "kategoriler": []}
                sonuc_json = await response.json()
                icerik = sonuc_json["choices"][0]["message"]["content"]

                temiz_icerik = icerik.strip()
                if temiz_icerik.startswith("```json"):
                    temiz_icerik = temiz_icerik.replace("```json", "", 1).replace("```", "").strip()
                elif temiz_icerik.startswith("```"):
                    temiz_icerik = temiz_icerik.replace("```", "", 1).replace("```", "").strip()

                parcalanmis = json.loads(temiz_icerik)

                if isinstance(parcalanmis, dict):
                    parcalanmis = [parcalanmis]

                return {"orijinal_yorum": yorum_metni, "kategoriler": parcalanmis}

        except asyncio.TimeoutError:
            logger.warning(f"vLLM İsteği zaman aşımına uğradı. Yorum: {yorum_metni[:30]}...")
            return {"orijinal_yorum": yorum_metni, "kategoriler": []}
        except json.JSONDecodeError:
            logger.error(f"vLLM JSON döndürmedi. Gelen Yanıt: {icerik[:100]}")
            return {"orijinal_yorum": yorum_metni, "kategoriler": []}
        except Exception as e:
            logger.error(f"vLLM isteği sırasında hata: {e}")
            return {"orijinal_yorum": yorum_metni, "kategoriler": []}


async def vllm_ile_toplu_isleme(yorum_listesi: list[str], urun_grubu: str, max_concurrency: int = 50) -> list:
    if not yorum_listesi:
        logger.warning("vLLM ile işlenecek yorum bulunamadı, boş liste döndürülüyor.")
        return []

    gecerli_sema = URUN_GRUP_SEMALARI.get(urun_grubu,"Kullanım Kalitesi, Kargo ve Teslimat, Fiyat Performans, Genel")

    system_prompt = f"Yorumu parçalara ayır ve şu kategorilerden biriyle eşleştir: {gecerli_sema}"

    semaphore = asyncio.Semaphore(max_concurrency)

    async with aiohttp.ClientSession() as session:
        tasks = [_tekil_vllm_istegi(session, semaphore, system_prompt, yorum) for yorum in yorum_listesi]
        logger.info(f"vLLM ile {len(yorum_listesi)} yorum için istekler oluşturuldu, işleniyor...")
        results = await asyncio.gather(*tasks)

    return results


def oransal_yorum_secimi(db, urun_id, max_sayi):
    """
    Yorumları puanlarına göre oranlayarak seçer.
    Geriye metinle birlikte puan bilgisini de içeren bir sözlük listesi döner.
    """
    sorgu = "SELECT id, clean_text, predicted_score FROM reviews WHERE product_id = %s AND clean_text IS NOT NULL;"
    tum_yorumlar = db.fetch_query(sorgu, (urun_id,))

    if not tum_yorumlar:
        return []

    puan_gruplari = {1: [], 2: [], 3: [], 4: [], 5: [], 0: []}
    for r_id, metin, puan in tum_yorumlar:
        puan_val = int(puan) if puan is not None else 0
        yorum_paketi = {"id": r_id, "clean_text": metin, "puan": puan_val}

        if puan_val in puan_gruplari:
            puan_gruplari[puan_val].append(yorum_paketi)
        else:
            puan_gruplari[0].append(yorum_paketi)

    for p in puan_gruplari:
        puan_gruplari[p].sort(key=lambda x: len(x["clean_text"]), reverse=True)

    toplam_yorum = len(tum_yorumlar)
    secilen_yorumlar = []

    for p, yorum_paketleri in puan_gruplari.items():
        if not yorum_paketleri:
            continue
        oran = len(yorum_paketleri) / toplam_yorum
        secilecek_adet = int(round(oran * max_sayi))

        # 2. GÜNCELLEME: endpoint'e uyumlu 'clean_text' ve 'id' ile paketleyerek ekliyoruz
        for paket in yorum_paketleri[:secilecek_adet]:
            secilen_yorumlar.append({
                "id": str(paket["id"]),  # UUID ise string'e güvenli cast
                "clean_text": paket["clean_text"],
                "puan": paket["puan"]
            })

    if len(secilen_yorumlar) > max_sayi:
        secilen_yorumlar = secilen_yorumlar[:max_sayi]

    return secilen_yorumlar

VLLM_LLAMA_SERVER_URL = os.getenv("VLLM_LLAMA_SERVER_URL", "http://0.0.0.0:8000")
VLLM_LLAMA_MODEL_NAME = "ecommerce-adapter"


async def _tekil_llama_istegi(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, system_prompt: str,
                              user_content: str, meta_data: dict) -> dict:
    url = f"{VLLM_LLAMA_SERVER_URL}/v1/chat/completions"

    payload = {
        "model": VLLM_LLAMA_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 512,
        "presence_penalty": 0.1,
        "frequency_penalty": 0.1
    }

    print("\n" + "=" * 60)
    print(f"🚀 [GENEL ÖZET] MODELE GİDEN USER CONTENT:\n{user_content}")
    print("=" * 60 + "\n")

    async with semaphore:
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=180)) as response:
                if response.status != 200:
                    hata_metni = await response.text()
                    logger.error(f"LLAMA isteği başarısız oldu. Status: {response.status}, Hata: {hata_metni}")
                    return {"meta": meta_data, "ozet": None}

                sonuc_json = await response.json()
                ozet_metni = sonuc_json["choices"][0]["message"]["content"].strip()

                print("\n" + "*" * 60)
                print(f"📥 [GENEL ÖZET] MODELDEN GELEN YANIT:\n{ozet_metni}")
                print("*" * 60 + "\n")

                return {"meta": meta_data, "ozet": ozet_metni}

        except asyncio.TimeoutError:
            logger.warning(f"LLAMA İsteği zaman aşımına uğradı. Meta: {meta_data}")
            return {"meta": meta_data, "ozet": None}
        except Exception as e:
            logger.error(f"LLAMA isteği sırasında hata: {e}. Meta: {meta_data}")
            return {"meta": meta_data, "ozet": None}

async def llama_ile_toplu_ozet(istek_listesi: list[dict], max_concurrency: int = 4) -> list:
    if not istek_listesi:
        logger.warning("LLAMA ile özetlenecek veri bulunamadı, boş liste döndürülüyor.")
        return []

    semaphore = asyncio.Semaphore(max_concurrency)

    async with aiohttp.ClientSession() as session:
        tasks = [
            _tekil_llama_istegi(session, semaphore, req["system_prompt"], req["user_content"], req["meta"])
            for req in istek_listesi
        ]
        logger.info(f"LLAMA ile {len(istek_listesi)} özetleme isteği oluşturuldu, işleniyor...")
        results = await asyncio.gather(*tasks)

    return results
class ChatRequest(BaseModel):
    productId: str
    user_message: str


def get_product_rag_context(product_id: str, db_manager: DatabaseManager) -> str:
    """
    Veritabanı tablolarından ürün genel özetini, kategorik özetleri (aspects),
    çelişki skorunu ve ham yorumları eksiksiz çeken güncel RAG sorgusu.
    """
    # 1. Ürünün Temel Bilgilerini Çek
    prod_query = """
                 SELECT product_name, platform, avg_orj_score, avg_model_score, celiski_score
                 FROM products
                 WHERE id = %s; \
                 """
    product_data = db_manager.fetch_query(prod_query, (product_id,))
    if not product_data:
        return "Ürün analitik verileri veritabanında bulunamadı."

    p_name, platform, avg_orj, avg_model, celiski = product_data[0]
    temiz_celiski = int(float(celiski) * 100) if celiski is not None else 0

    # 2. Ürüne Ait Llama Tarafından Üretilmiş Özetleri Çek (Yeni Tablo)
    sum_query = """
                SELECT summary_type, category_name, summary_text, average_score
                FROM product_summaries
                WHERE product_id = %s; \
                """
    summaries_data = db_manager.fetch_query(sum_query, (product_id,))

    genel_ozet = "Genel özet henüz oluşturulmadı."
    kategori_ozetleri = []

    for row in summaries_data:
        s_type, cat_name, s_text, avg_score = row
        # Eğer Llama'dan gelen özet tipi veya kategorisi "genel" ise ana özet kabul et
        if str(s_type).lower() == "genel" or str(cat_name).lower() == "genel":
            genel_ozet = s_text
        else:
            # Diğer spesifik kategorileri (Örn: Lezzet, Kargo, Kullanım) listeye ekle
            score_str = f"{avg_score}/5" if avg_score else "N/A"
            kategori_ozetleri.append(f"- {cat_name} (Puan: {score_str}): {s_text}")

    kategori_ozetleri_str = "\n".join(
        kategori_ozetleri) if kategori_ozetleri else "Kategorik analiz henüz mevcut değil."

    # 3. Modele kanıt niteliğinde sunulacak en güncel gerçek ham kullanıcı yorumları
    review_query = """
                   SELECT original_rating, raw_text
                   FROM reviews
                   WHERE product_id = %s
                     AND raw_text IS NOT NULL
                     AND raw_text != '' 
        LIMIT 4; \
                   """
    yorumlar = db_manager.fetch_query(review_query, (product_id,))
    yorum_metinleri = "".join([f"- [{r[0]} Yıldız]: {r[1].strip()}\n" for r in yorumlar])

    # 4. RAG Bağlamını (Context) Chatbot İçin Birleştir
    context = f"""
    [ÜRÜN KİMLİĞİ VE SKORLAR]
    Ürün Adı: {p_name} | Platform: {platform}
    Müşteri Puan Ortalaması: {avg_orj}/5 | Yapay Zeka Memnuniyet Skoru: {avg_model}/5
    Müşteri Fikir Ayrılığı (Çelişki) Oranı: %{temiz_celiski}

    [VİVİDAİ GENEL ÖZETİ]
    {genel_ozet}

    [KATEGORİK YAPAY ZEKA ANALİZLERİ (ASPECTS)]
    {kategori_ozetleri_str}

    [SİSTEMDEKİ GERÇEK KULLANICI YORUMLARI (Örneklem)]
    {yorum_metinleri if yorum_metinleri else 'Henüz ham yorum metni yüklenmemiş.'}
    """

    return context
