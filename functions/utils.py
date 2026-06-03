from rapidfuzz import process, fuzz
from urllib.parse import urlparse, urlunparse
import urllib.parse
import hashlib
import re
import logging
import json
from gradio_client import Client
from config import URUN_GRUP_SEMALARI

logger = logging.getLogger(__name__)


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


def bulut_model_analiz_et(yorum_metni: str, urun_grubu: str) -> list:
    """
    Hugging Face Spaces üzerindeki parcalayici modelimize config.py içindeki
    korumalı kategori şemalarını enjekte ederek istek atar.

    :param yorum_metni: Ham müşteri veya mekan yorumu
    :param urun_grubu: config.py içindeki sözlük anahtarı (Örn: 'aksesuar_taki', 'gezilecek_yer')
    :return: Modelin parçalayıp eşleştirdiği JSON listesi
    """
    if not yorum_metni:
        return []

    # 1. Sözlükten ürün grubuna ait izin verilen kategorileri çekiyoruz
    if urun_grubu in URUN_GRUP_SEMALARI:
        gecerli_sema = URUN_GRUP_SEMALARI[urun_grubu]
    else:
        logger.warning(f"'{urun_grubu}' şeması config.py içinde bulunamadı. Genel şema devrede.")
        gecerli_sema = "Kullanım Kalitesi, Kargo ve Teslimat, Fiyat Performans, Genel"

    try:
        # Bu kısım bulut köprüsünü kurmak deniyor.
        client = Client("eroglufurkaan/uzman_parcaliyici")

        response = client.predict(
            yorum=yorum_metni,
            gecerli_kategoriler=gecerli_sema,
            api_name="/predict"
        )

        # Buluttan gelen JSON'u Python listesine parse et
        parcalanmis_veri = json.loads(response)
        return parcalanmis_veri

    except json.JSONDecodeError:
        logger.error("Buluttan dönen veri geçerli bir JSON formatında değil!")
        return []
    except Exception as e:
        logger.error(f"Bulut model sorgulanırken utils katmanında hata oluştu: {e}")
        return []

