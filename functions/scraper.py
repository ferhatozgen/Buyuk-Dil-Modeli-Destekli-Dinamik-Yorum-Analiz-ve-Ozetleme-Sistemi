from bs4 import BeautifulSoup
from curl_cffi import requests
from pathlib import Path
from langdetect import detect
import urllib.parse
import json
import os
import re
import emoji
import base64
from functions.logger import setup_logger
import time

logger = setup_logger()
# ==========================================
# 1. VERİ TEMİZLEME SINIFI (PREPROCESSOR)
# ==========================================
def kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar_seti, min_kelime=4):
    """
    Yorumun veritabanına girmeye hak kazanıp kazanmadığını test eder.
    True dönerse yorum kalitelidir, False dönerse çöptür.
    """
    # 1. Kelime Sayısı Filtresi
    if len(temiz_metin.split()) < min_kelime:
        return False

    # 2. Tekrar Eden (Duplicate) Yorum Filtresi
    if temiz_metin in gorulen_yorumlar_seti:
        return False

    # 3. Yabancı Dil Filtresi
    try:
        if detect(temiz_metin) != 'tr':
            return False
    except:
        return False # Dil anlaşılamayacak kadar bozuksa direkt ele

    # Bütün zorlu testleri geçtiyse onay ver
    return True

class ReviewPreprocessor:
    def __init__(self, typo_file="duzeltmeler.json", bad_words_file="bad_words.json"):
        self.typo_mapping = self._load_json(typo_file, dict)
        self.bad_words = set(self._load_json(bad_words_file, list))

    def _load_json(self, filename, default_type):
        path = Path(filename)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception: pass
        return default_type()

    def lowercase_turkish(self, text):
        lookup = {'I': 'ı', 'İ': 'i', 'Ş': 'ş', 'Ç': 'ç', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö'}
        return "".join([lookup.get(char, char) for char in text]).lower()

    def clean_text(self, text, platform="general"):
        if not isinstance(text, str) or not text.strip(): return ""

        text = text.replace('\n', ' ').replace('\r', '')
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        text = re.sub(r'<.*?>', '', text)
        text = emoji.replace_emoji(text, replace='')

        if platform in ["trendyol", "hepsiburada", "ciceksepeti"]:
            ignore_list = ["değerlendirme faydalı mı", "kullanıcı bu ürünü", "satıcısından alındı", "yanıtla"]
            if any(x in text.lower() for x in ignore_list): return ""

        text = self.lowercase_turkish(text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'([a-zçğıöşü])\1{2,}', r'\1', text)

        words = text.split()
        text = " ".join([self.typo_mapping.get(word, word) for word in words])

        words = text.split()
        text = " ".join([w for w in words if not (re.search(r'[aeıioöuü]{3,}', w) or re.search(r'[bcçdfgğhjklmnprsştvyz]{4,}', w))])

        if self.bad_words:
            for bad_word in self.bad_words:
                text = re.sub(r'\b' + re.escape(bad_word) + r'\b', '', text, flags=re.IGNORECASE)

        return re.sub(r'\s+', ' ', text).strip()

# ==========================================
# 2. YARDIMCI VE DEDEKTİF FONKSİYONLAR
# ==========================================
def get_og_image(url):
    """Verilen URL'nin kaynak koduna girip sosyal medya (og:image) görselini çeker."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    try:
        res = requests.get(url, headers=headers, impersonate="chrome120", timeout=10, verify=False)
        match = re.search(r'<meta\s+(?:property|name)=["\']og:image["\']\s+content=["\']([^"\']+)["\']', res.text, re.IGNORECASE)
        return match.group(1) if match else "Görsel Bulunamadı"
    except: return "Görsel Bulunamadı"

def yorum_metnini_bul(yorum):
    """Farklı JSON formatlarındaki asıl yorum metnini otomatik bulur."""
    if isinstance(yorum, str): return yorum
    olasi_anahtarlar = ["metin", "comment", "review", "text", "customerDescription", "comments", "reviewText", "content"]
    if isinstance(yorum, dict):
        for key in olasi_anahtarlar:
            if key in yorum and isinstance(yorum[key], str): return yorum[key]
        string_degerler = [v for v in yorum.values() if isinstance(v, str) and len(v) > 5]
        if string_degerler: return max(string_degerler, key=len)
    return ""

def yemeksepeti_gorsel_bul(json_verisi):
    """Yemeksepeti'nin devasa Next.js JSON'ı içinde logo veya afiş arar."""
    if isinstance(json_verisi, dict):
        # Öncelik sıramız: Önce logo, yoksa afiş, yoksa herhangi bir resim
        olasi_anahtarlar = ["logo", "heroImageUrl", "hero_listing_image", "hero_image", "image", "vendorPicture"]
        for key in olasi_anahtarlar:
            val = json_verisi.get(key)
            # Değerin geçerli bir Yemeksepeti/DeliveryHero resim linki olduğundan emin olalım
            if isinstance(val, str) and val.startswith("http") and ("deliveryhero" in val or "yemeksepeti" in val):
                return val

        # Bulamazsa alt sözlüklere in (Recursive)
        for _, deger in json_verisi.items():
            sonuc = yemeksepeti_gorsel_bul(deger)
            if sonuc: return sonuc

    elif isinstance(json_verisi, list):
        for eleman in json_verisi:
            sonuc = yemeksepeti_gorsel_bul(eleman)
            if sonuc: return sonuc
    return None

def trendyol_yorum_bul(json_verisi):
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict) and "comment" in json_verisi[0]: return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = trendyol_yorum_bul(deger)
            if sonuc: return sonuc
    return []

def hb_yorum_bul(json_verisi):
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "review" in json_verisi[0] or "star" in json_verisi[0] or "customerName" in json_verisi[0]: return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = hb_yorum_bul(deger)
            if sonuc: return sonuc
    return []

def yemeksepeti_yorum_bul(json_verisi):
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "rating" in json_verisi[0] or "customerDescription" in json_verisi[0]:
            return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = yemeksepeti_yorum_bul(deger)
            if sonuc: return sonuc
    return []


def handle_response(response):
    if "vendor" in response.url and response.status == 200:
        try:
            data = response.json()
            # Buradaki JSON içinde görsel linkini ara
            potential_img = yemeksepeti_gorsel_bul(data)
            if potential_img:
                logger.info(f"🎯 API'den Görsel Yakalandı: {potential_img}")
        except: pass

def trendyol_go_yorum_bul(json_verisi):
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "comment" in json_verisi[0] or "rate" in json_verisi[0] or "customerName" in json_verisi[0]:
            return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = trendyol_go_yorum_bul(deger)
            if sonuc: return sonuc
    return []

def etstur_yorum_bul(json_verisi):
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "text" in json_verisi[0] or "comment" in json_verisi[0] or "reviewText" in json_verisi[0] or "customer" in json_verisi[0]:
            return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = etstur_yorum_bul(deger)
            if sonuc: return sonuc
    return []

def airbnb_yorum_bul(json_verisi):
    try:
        reviews_data = json_verisi.get("data", {}).get("presentation", {}).get("stayProductDetailPage", {}).get("reviews", {}).get("reviews", [])
        if reviews_data: return reviews_data
    except Exception: pass
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "comments" in json_verisi[0] or "commentV2" in json_verisi[0]: return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = airbnb_yorum_bul(deger)
            if sonuc: return sonuc
    return []

# ==========================================
# 3. PLATFORM FONKSİYONLARI
# ==========================================
def trendyol_veri_cek(urun_linki, max_sayfa) -> str:
    match = re.search(r'-p-(\d+)', urun_linki)
    if not match: return
    urun_id = match.group(1)
    isim_match = re.search(r'/([^/]+)-p-\d+', urun_linki)
    urun_adi = isim_match.group(1).replace('-', ' ').title() if isim_match else "Trendyol Ürünü"

    dosya_yolu = f"cekilen_veriler/trendyol/trendyol_{urun_id}.json"

    logger.info(f"🔍 Trendyol ID Çözümleniyor: {urun_id}")
    gorsel_url = get_og_image(urun_linki)

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set() # Tekrar kontrolü için hafıza
    MAX_YORUM_SINIRI = 500   # Hedef limit

    headers = {"Accept": "application/json", "Origin": "https://www.trendyol.com", "Referer": urun_linki}

    for sayfa in range(max_sayfa):
        # HEDEF KONTROLÜ
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        api_url = f"https://apigw.trendyol.com/discovery-storefront-trproductgw-service/api/review-read/product-reviews/detailed?channelId=1&contentId={urun_id}&page={sayfa}"
        try:
            res = requests.get(api_url, headers=headers, impersonate="chrome120", timeout=10, verify=False)
            if res.status_code != 200: break

            yorum_listesi = trendyol_yorum_bul(res.json())
            if not yorum_listesi: break

            for yrm in yorum_listesi:
                # İÇ DÖNGÜ KONTROLÜ
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    break

                ham_metin = yorum_metnini_bul(yrm)
                temiz_metin = preprocessor.clean_text(ham_metin, "trendyol")

                # KALİTE KONTROL
                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            time.sleep(0.5)
        except Exception: break

    if tum_yorumlar:
        veri_seti = {"platform": "trendyol", "baslik": urun_adi, "link": urun_linki, "gorsel_url": gorsel_url, "yorumlar": tum_yorumlar}

        hedef_klasor = "cekilen_veriler/trendyol"
        os.makedirs(hedef_klasor, exist_ok=True)

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)

        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None

def hepsiburada_veri_cek(urun_linki, max_sayfa) -> str:
    match = re.search(r'-p[m]?-([A-Za-z0-9]+)', urun_linki)
    if not match: return
    urun_sku = match.group(1).upper()
    isim_match = re.search(r'/([^/]+)-p[m]?-', urun_linki)
    urun_adi = isim_match.group(1).replace('-', ' ').title() if isim_match else "Hepsiburada Ürünü"

    dosya_yolu = f"cekilen_veriler/hepsiburada/hepsiburada_{urun_sku}.json"

    logger.info(f"🔍 Hepsiburada SKU Çözümleniyor: {urun_sku}")
    gorsel_url = "Görsel Bulunamadı" # Başlangıçta boş

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set() # Tekrar kontrolü için hafıza
    MAX_YORUM_SINIRI = 500   # Limitimiz
    headers = {"Accept": "application/json", "Origin": "https://www.hepsiburada.com", "Referer": urun_linki}

    for sayfa in range(max_sayfa):
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break
        offset = sayfa * 20
        api_url = f"https://user-content-gw-hermes.hepsiburada.com/queryapi/v2/ApprovedUserContents?sku={urun_sku}&from={offset}&size=20"
        try:
            res = requests.get(api_url, headers=headers, impersonate="chrome120", timeout=10, verify=False)
            if res.status_code != 200: break

            data = res.json()
            yorum_listesi = data.get("approvedUserContents", [])
            if not yorum_listesi: yorum_listesi = hb_yorum_bul(data)
            if not yorum_listesi: break

            # SİHİR 1: Görseli JSON'ın kendisinden çekiyoruz (Sadece ilk sayfada 1 kere yapması yeterli)
            if sayfa == 0 and yorum_listesi and gorsel_url == "Görsel Bulunamadı":
                ilk_yorum = yorum_listesi[0]
                img_raw = ilk_yorum.get("product", {}).get("imageUrl", "")
                if img_raw:
                    gorsel_url = img_raw.replace("{size}", "500") # {size} yerine 500 piksel yazıyoruz

            for yrm in yorum_listesi:
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    break

                ham_metin = yrm.get("review", {}).get("content", "")
                temiz_metin = preprocessor.clean_text(ham_metin, "hepsiburada")

                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin) # Bir daha gelirse diye hafızaya kazı
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)
            time.sleep(1)
        except Exception: break

    if tum_yorumlar:
        veri_seti = {"platform": "hepsiburada", "baslik": urun_adi, "link": urun_linki, "gorsel_url": gorsel_url, "yorumlar": tum_yorumlar}

        # 1. Platforma özel alt klasörü oluştur
        hedef_klasor = "cekilen_veriler/hepsiburada"
        os.makedirs(hedef_klasor, exist_ok=True)

        # 2. Dosyayı kaydet
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)
        logger.info(f"Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None

def ciceksepeti_veri_cek(urun_linki, max_sayfa) -> str:
    match_code = re.search(r'-([a-zA-Z0-9]+)(?:\?|/|$)', urun_linki)
    urun_kodu = match_code.group(1).lower() if match_code else str(int(time.time()))
    isim_match = re.search(r'/([^/]+)-[a-zA-Z0-9]+(?:\?|/|$)', urun_linki)
    urun_adi = isim_match.group(1).replace('-', ' ').title() if isim_match else "Çiçeksepeti Ürünü"

    dosya_yolu = f"cekilen_veriler/ciceksepeti/ciceksepeti_{urun_kodu}.json"

    logger.info(f"🔍 Çiçeksepeti Kodu Çözümleniyor: {urun_kodu}")

    gorsel_url = get_og_image(urun_linki)
    headers_main = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

    try:
        res = requests.get(urun_linki, headers=headers_main, impersonate="chrome120", timeout=15, verify=False)
        if res.status_code != 200: return
        id_match = re.search(r'data-productid=["\'](\d+)["\']', res.text, re.IGNORECASE) or re.search(r'"productId"\s*:\s*(\d+)', res.text, re.IGNORECASE)
        if not id_match: return
        gercek_urun_id = id_match.group(1)
    except Exception: return

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set() # Tekrar kontrolü
    MAX_YORUM_SINIRI = 500   # Hedef limit

    api_headers = {"X-Requested-With": "XMLHttpRequest", "User-Agent": headers_main["User-Agent"]}

    for sayfa in range(1, max_sayfa + 1):
        # HEDEF KONTROLÜ
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        api_url = f"https://www.ciceksepeti.com/Review/GetReviews?productId={gercek_urun_id}&page={sayfa}"
        try:
            response = requests.get(api_url, headers=api_headers, impersonate="chrome120", timeout=10, verify=False)
            if response.status_code != 200: break

            soup = BeautifulSoup(response.text, 'html.parser')
            yorum_kutulari = soup.find_all("div", class_="ns-reviews--item-wrapper")
            if not yorum_kutulari: break

            for kutu in yorum_kutulari:
                # İÇ DÖNGÜ KONTROLÜ
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    break

                metin_span = kutu.find("span", class_="js-review-detail")
                ham_metin = metin_span.get("data-value", "").strip() if metin_span else ""
                temiz_metin = preprocessor.clean_text(ham_metin, "ciceksepeti")

                # KALİTE KONTROL
                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)

                    isim_p = kutu.find("p", class_="js-review-name")
                    tarih_p = kutu.find("p", class_="js-review-date")
                    yildiz_alani = kutu.find("div", class_="js-review-stars")
                    dolu_yildizlar = [y for y in yildiz_alani.find_all("span", class_="products-stars__icon") if "is-passive" not in y.get("class", [])] if yildiz_alani else []

                    yrm = {
                        "isim": isim_p.text.strip() if isim_p else "Bilinmiyor",
                        "tarih": tarih_p.text.strip() if tarih_p else "Bilinmiyor",
                        "puan": f"{len(dolu_yildizlar)} Yıldız",
                        "orijinal_metin": ham_metin,
                        "temiz_metin": temiz_metin
                    }
                    tum_yorumlar.append(yrm)
            time.sleep(0.5)
        except Exception: break

    if tum_yorumlar:
        veri_seti = {"platform": "ciceksepeti", "baslik": urun_adi, "link": urun_linki, "gorsel_url": gorsel_url, "yorumlar": tum_yorumlar}

        hedef_klasor = "cekilen_veriler/ciceksepeti"
        os.makedirs(hedef_klasor, exist_ok=True)

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)
        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None

def steam_veri_cek(oyun_linki, max_sayfa) -> str:
    match = re.search(r'/app/(\d+)', oyun_linki)
    if not match: return
    app_id = match.group(1)
    isim_match = re.search(r'/app/\d+/([^/?]+)', oyun_linki)
    urun_adi = isim_match.group(1).replace('_', ' ').title() if isim_match else "Steam Oyunu"

    dosya_yolu = f"cekilen_veriler/steam/steam_{app_id}.json"

    logger.info(f"🔍 Steam ID Çözümleniyor: {app_id}")
    gorsel_url = f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set() # Tekrar kontrolü
    MAX_YORUM_SINIRI = 500   # Hedef limit
    cursor = "*"

    for sayfa in range(max_sayfa):
        # HEDEF KONTROLÜ
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        encoded_cursor = urllib.parse.quote(cursor)
        api_url = f"https://store.steampowered.com/appreviews/{app_id}?json=1&language=turkish&filter=recent&num_per_page=100&cursor={encoded_cursor}"
        try:
            res = requests.get(api_url, impersonate="chrome120", timeout=10, verify=False)
            if res.status_code != 200: break

            data = res.json()
            yorum_listesi = data.get("reviews", [])
            if not yorum_listesi: break

            for yrm in yorum_listesi:
                # İÇ DÖNGÜ KONTROLÜ
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    break

                ham_metin = yorum_metnini_bul(yrm)
                temiz_metin = preprocessor.clean_text(ham_metin, "steam")

                # KALİTE KONTROL
                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            yeni_cursor = data.get("cursor")
            if not yeni_cursor or yeni_cursor == cursor: break
            cursor = yeni_cursor
            time.sleep(0.5)
        except Exception: break

    if tum_yorumlar:
        veri_seti = {"platform": "steam", "baslik": urun_adi, "link": oyun_linki, "gorsel_url": gorsel_url, "yorumlar": tum_yorumlar}

        hedef_klasor = "cekilen_veriler/steam"
        os.makedirs(hedef_klasor, exist_ok=True)

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)
        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None

def etstur_veri_cek(otel_linki, max_sayfa) -> str:
    logger.info(f"🔍 Etstur ID'leri Çözümleniyor: {otel_linki}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    try:
        html_res = requests.get(otel_linki, headers=headers, impersonate="chrome120", timeout=15, verify=False)
        if html_res.status_code != 200: return
        hotel_id_match = re.search(r'data-hotel-id=["\']([^"\']+)["\']', html_res.text) or re.search(r'"hotelId"\s*:\s*["\']([^"\']+)["\']', html_res.text)
        hotel_code_match = re.search(r'data-vendor-code=["\']([^"\']+)["\']', html_res.text) or re.search(r'"vndCode"\s*:\s*["\']([^"\']+)["\']', html_res.text)
        if not hotel_code_match or not hotel_id_match: return
        hotel_code = hotel_code_match.group(1)
        hotel_id = hotel_id_match.group(1)
    except Exception: return

    isim_match = re.search(r'etstur\.com/([^/?]+)', otel_linki)
    urun_adi = isim_match.group(1).replace('-', ' ').title() if isim_match else "Etstur Oteli"

    dosya_yolu = f"cekilen_veriler/etstur/etstur_{hotel_code}.json"

    logger.info(f"🔍 Etstur Kodu Çözümleniyor: {hotel_code}")

    gorsel_url = get_og_image(otel_linki)

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set() # Tekrar kontrolü için hafıza
    MAX_YORUM_SINIRI = 500   # Hedef limit

    api_url = "https://www.etstur.com/services/api/review"
    api_headers = {"Content-Type": "application/json", "Origin": "https://www.etstur.com", "Referer": otel_linki}

    for sayfa in range(max_sayfa):
        # DIŞ KONTROL
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        payload = {"hotelCode": hotel_code, "hotelId": hotel_id, "offset": sayfa, "sort": "BOOKING_DESC", "period": "", "categoryType": "OVERALL", "searchText": ""}
        try:
            response = requests.post(api_url, headers=api_headers, json=payload, impersonate="chrome120", timeout=15, verify=False)
            if response.status_code != 200: break

            data = response.json()
            yorum_listesi = data.get("reviews", [])
            if not yorum_listesi: yorum_listesi = etstur_yorum_bul(data)
            if not yorum_listesi: break

            for yrm in yorum_listesi:
                # İÇ KONTROL
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    break

                ham_metin = yorum_metnini_bul(yrm)
                temiz_metin = preprocessor.clean_text(ham_metin, "etstur")

                # KALİTE KONTROL
                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            time.sleep(0.5)
        except Exception: break

    if tum_yorumlar:
        veri_seti = {"platform": "etstur", "baslik": urun_adi, "link": otel_linki, "gorsel_url": gorsel_url, "yorumlar": tum_yorumlar}

        hedef_klasor = "cekilen_veriler/etstur"
        os.makedirs(hedef_klasor, exist_ok=True)

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)

        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None

def airbnb_veri_cek(oda_linki, max_sayfa) -> str:
    match = re.search(r'/rooms/(\d+)', oda_linki)
    if not match: return
    oda_id = match.group(1)

    dosya_yolu = f"cekilen_veriler/airbnb/airbnb_{oda_id}.json"

    logger.info(f" Airbnb ID Çözümleniyor: {oda_id}")
    gorsel_url = "Görsel Bulunamadı"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36", "Accept-Language": "tr-TR,tr;q=0.9"}
    try:
        html_res = requests.get(oda_linki, headers=headers, impersonate="chrome120", timeout=15, verify=False)
        temiz_html = html_res.text.replace('\\u002F', '/')

        urun_adi = "Airbnb Evi"

        title_match = re.search(r'<title>([^<]+)</title>', temiz_html, re.IGNORECASE)
        if title_match and "Kiralık" not in title_match.group(1) and "Vacation Rentals" not in title_match.group(1) and "Airbnb" not in title_match.group(1):
            urun_adi = title_match.group(1).split(' - ')[0].strip()
        else:
            isim_match = re.search(r'"pdp_listing_title"\s*:\s*"([^"]+)"', temiz_html)
            if not isim_match:
                isim_match = re.search(r'"p3_summary_title"\s*:\s*"([^"]+)"', temiz_html)
            if not isim_match:
                isim_match = re.search(r'"name"\s*:\s*"([^"]+)"', temiz_html)

            if isim_match:
                olasi_isim = isim_match.group(1).replace('\\u0026', '&').replace('\\u002F', '/')
                if len(olasi_isim) > 3 and "Kiralık" not in olasi_isim:
                    urun_adi = olasi_isim

        api_key_match = re.search(r'"api_config"\s*:\s*{[^}]*"key"\s*:\s*"([^"]+)"', temiz_html)
        if not api_key_match: return
        api_key = api_key_match.group(1)

        pic_match = re.findall(r'(https://a0\.muscache\.com/im/pictures/[^"\'\?\\]+\.(?:jpg|jpeg|png|webp))', temiz_html)

        for pic in pic_match:
            if any(x in pic for x in ["/hosting/", "/miso/", "/pro/", "/prohost/"]):
                gorsel_url = pic
                logger.info(f"🖼️ Airbnb Ev Görseli Nokta Atışı Çekildi: {gorsel_url}")
                break

    except Exception: return

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set() # Tekrar kontrolü
    MAX_YORUM_SINIRI = 500   # Hedef limit

    base64_id = base64.b64encode(f"StayListing:{oda_id}".encode('utf-8')).decode('utf-8')
    sha256Hash = "2ed951bfedf71b87d9d30e24a419e15517af9fbed7ac560a8d1cc7feadfa22e6"
    api_headers = {"Accept": "application/json", "x-airbnb-api-key": api_key, "User-Agent": headers["User-Agent"], "Origin": "https://www.airbnb.com.tr", "Referer": oda_linki}

    for sayfa in range(max_sayfa):
        # DIŞ KONTROL
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        limit = 24 if sayfa == 0 else 10
        offset = 0 if sayfa == 0 else 24 + ((sayfa - 1) * 10)
        variables = {"id": base64_id, "pdpReviewsRequest": {"fieldSelector": "for_p3_translation_only", "forPreview": False, "limit": limit, "offset": str(offset), "showingTranslationButton": False, "first": limit, "sortingPreference": "BEST_QUALITY"}}
        extensions = {"persistedQuery": {"version": 1, "sha256Hash": sha256Hash}}
        params = {"operationName": "StaysPdpReviewsQuery", "locale": "tr", "currency": "TRY", "variables": json.dumps(variables, separators=(',', ':')), "extensions": json.dumps(extensions, separators=(',', ':'))}
        full_url = f"https://www.airbnb.com.tr/api/v3/StaysPdpReviewsQuery/{sha256Hash}?{urllib.parse.urlencode(params)}"

        try:
            response = requests.get(full_url, headers=api_headers, impersonate="chrome120", timeout=15, verify=False)
            if response.status_code != 200: break

            data = response.json()
            yorum_listesi = airbnb_yorum_bul(data)
            if not yorum_listesi: break

            for yrm in yorum_listesi:
                # İÇ KONTROL
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    break

                ham_metin = yorum_metnini_bul(yrm)
                temiz_metin = preprocessor.clean_text(ham_metin, "airbnb")

                # KALİTE KONTROLÜ
                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            time.sleep(1.5)
        except Exception: break

    if tum_yorumlar:
        veri_seti = {"platform": "airbnb", "baslik": urun_adi, "link": oda_linki, "gorsel_url": gorsel_url, "yorumlar": tum_yorumlar}

        hedef_klasor = "cekilen_veriler/airbnb"
        os.makedirs(hedef_klasor, exist_ok=True)

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)

        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None


def yemeksepeti_veri_cek(restoran_linki, max_sayfa) -> str:
    match = re.search(r'/restaurant/([a-zA-Z0-9]+)', restoran_linki)
    if not match: return
    vendor_id = match.group(1)
    isim_match = re.search(r'/restaurant/[^/]+/([^/?]+)', restoran_linki)
    if isim_match:
        ham_isim = isim_match.group(1).replace('-', ' ').title()
        # İsmin sonundaki satıcı ID'sini temizle
        urun_adi = ham_isim.replace(f" {vendor_id.title()}", "").strip()
    else:
        urun_adi = "Yemeksepeti Restoranı"

    dosya_yolu = f"cekilen_veriler/yemeksepeti/yemeksepeti_{vendor_id}.json"

    logger.info(f"🔍 Yemeksepeti Vendor ID Çözümleniyor: {vendor_id}")
    gorsel_url = "Görsel Bulunamadı"

    # ==========================================
    # SİHİR 1: PLAYWRIGHT (KALICI PROFIL İLE GÖRSEL ÇALMA)
    # ==========================================
    logger.info("🔍 Restoran sayfasına kalıcı profil ile erişiliyor...")
    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth

        profil_klasoru = os.path.join(os.getcwd(), "../saved_ys_profile")
        os.makedirs(profil_klasoru, exist_ok=True)

        with Stealth().use_sync(sync_playwright()) as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profil_klasoru,
                headless=False,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="tr-TR",
                ignore_default_args=["--enable-automation"],
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                viewport={'width': 1600, 'height': 900}
            )

            page = context.pages[0] if context.pages else context.new_page()

            try:
                page.goto(restoran_linki, wait_until="domcontentloaded", timeout=90000)
                logger.info("   ⏳ Sayfa yüklendi. Captcha/Güvenlik ekranı varsa çözmeniz için 90 saniye bekleniyor...")
                page.wait_for_selector("img[data-testid='vendor-logo'], img.vendor-logo__image", timeout=90000)

                kapat_btn = page.locator('button:has-text("Kabul Et"), button:has-text("Anladım"), button:has-text("Kapat")')
                if kapat_btn.count() > 0:
                    kapat_btn.first.click(timeout=3000)
            except Exception as e:
                logger.warning(f"   [Uyarı] Sayfa yüklenirken veya Captcha çözülürken sorun oluştu: {e}")

            page.mouse.wheel(0, 500)
            time.sleep(1.5)

            try:
                bulunan_resim = page.evaluate('''() => {
                    const images = Array.from(document.querySelectorAll('img'));
                    const logo = images.find(img => {
                        const src = img.src.toLowerCase();
                        const alt = img.alt.toLowerCase();
                        return src.includes('deliveryhero') || src.includes('logo') || alt.includes('logo');
                    });
                    return logo ? (logo.src || logo.dataset.src) : null;
                }''')

                if bulunan_resim:
                    if bulunan_resim.startswith("//"):
                        bulunan_resim = "https:" + bulunan_resim
                    gorsel_url = bulunan_resim.replace('\\u002F', '/')
                    logger.info(f" ✅ Görsel Playwright ile Yakalandı: {gorsel_url}")
                else:
                    element = page.locator("img[data-testid='vendor-logo'], img.vendor-logo__image").first
                    if element.count() > 0:
                        gorsel_url = element.get_attribute("src") or element.get_attribute("data-src")
                        logger.info(f" ✅ Görsel (B Planı) Playwright ile Yakalandı: {gorsel_url}")

            except Exception as img_err:
                logger.warning(f"   [Uyarı] Görsel aranırken sorun oluştu: {img_err}")

            page.close()
            context.close()

    except Exception as py_err:
        logger.warning(f"   [Uyarı] Playwright ana işleminde sorun oluştu: {py_err}")

    # ==========================================
    # SİHİR 2: YORUMLARI API'DEN IŞIK HIZINDA ÇEKME
    # ==========================================
    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set() # Tekrar kontrolü
    MAX_YORUM_SINIRI = 500   # Hedef limit
    next_page_key = ""
    headers = {"Accept": "application/json", "Origin": "https://www.yemeksepeti.com", "Referer": restoran_linki}

    for sayfa in range(max_sayfa):
        # DIŞ KONTROL
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        api_url = f"https://reviews-api-tr.fd-api.com/reviews/vendor/{vendor_id}?global_entity_id=YS_TR&limit=50&has_dish=true"
        if next_page_key: api_url += f"&nextPageKey={urllib.parse.quote(next_page_key)}"

        try:
            res = requests.get(api_url, headers=headers, impersonate="chrome120", timeout=15, verify=False)
            if res.status_code != 200: break

            data = res.json()
            yorum_listesi = data.get("data", [])
            if not yorum_listesi: yorum_listesi = yemeksepeti_yorum_bul(data)
            if not yorum_listesi: break

            for yrm in yorum_listesi:
                # İÇ KONTROL
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    break

                ham_metin = yorum_metnini_bul(yrm)
                temiz_metin = preprocessor.clean_text(ham_metin, "yemeksepeti")

                # KALİTE KONTROLÜ
                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            yeni_next_page_key = data.get("pageKey")
            if not yeni_next_page_key or yeni_next_page_key == next_page_key: break
            next_page_key = yeni_next_page_key
            time.sleep(0.5)
        except Exception: break

    # ==========================================
    # SİHİR 3: BİRLEŞTİR VE KAYDET
    # ==========================================
    if tum_yorumlar:
        veri_seti = {"platform": "yemeksepeti", "baslik": urun_adi, "link": restoran_linki, "gorsel_url": gorsel_url, "yorumlar": tum_yorumlar}

        hedef_klasor = "cekilen_veriler/yemeksepeti"
        os.makedirs(hedef_klasor, exist_ok=True)

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)

        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None

def trendyol_go_veri_cek(restoran_linki, max_sayfa) -> str:
    match = re.search(r'(?:-|/)(\d+)(?:/|\?|$)', restoran_linki)
    if not match: return
    vendor_id = match.group(1)

    dosya_yolu = f"cekilen_veriler/tygo/tygo_{vendor_id}.json"

    logger.info(f"🔍 Trendyol Go Vendor ID Çözümleniyor: {vendor_id}")
    gorsel_url = "Görsel Bulunamadı"
    headers_main = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

    try:
        html_res = requests.get(restoran_linki, headers=headers_main, impersonate="chrome120", timeout=10, verify=False)
        isim_match = re.search(r'<title>([^<]+)</title>', html_res.text, re.IGNORECASE)
        if isim_match:
            urun_adi = isim_match.group(1).split('|')[0].replace('Sipariş', '').strip()
        else:
            urun_adi = "Trendyol Go Restoranı"

        cdn_match = re.search(r'(https://cdn\.tgoapps\.com/[^"\']+\.(?:jpeg|jpg|png|webp))', html_res.text, re.IGNORECASE)
        if cdn_match:
            gorsel_url = cdn_match.group(1)
            logger.info(f"🖼️ Trendyol Go Görseli CDN'den Bulundu: {gorsel_url}")
    except Exception:
        urun_adi = "Trendyol Go Restoranı"

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set() # Tekrar kontrolü
    MAX_YORUM_SINIRI = 500   # Hedef limit
    headers = {"Accept": "application/json", "Origin": "https://www.trendyol.com", "Referer": restoran_linki}

    for sayfa in range(1, max_sayfa + 1):
        # DIŞ KONTROL
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        api_url = f"https://api.tgoapis.com/web-restaurant-apirestaurant-santral/restaurants/{vendor_id}/comments?page={sayfa}&pageSize=20&latitude=41.07087&longitude=28.996586&tagVersion=2"
        try:
            res = requests.get(api_url, headers=headers, impersonate="chrome120", timeout=10, verify=False)
            if res.status_code != 200: break

            data = res.json()
            yorum_listesi = trendyol_go_yorum_bul(data)
            if not yorum_listesi: break

            for yrm in yorum_listesi:
                # İÇ KONTROL
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    break

                ham_metin = yorum_metnini_bul(yrm)
                temiz_metin = preprocessor.clean_text(ham_metin, "trendyol_go")

                # KALİTE KONTROLÜ
                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            time.sleep(0.5)
        except Exception: break

    if tum_yorumlar:
        veri_seti = {"platform": "trendyol-go", "baslik": urun_adi, "link": restoran_linki, "gorsel_url": gorsel_url, "yorumlar": tum_yorumlar}

        hedef_klasor = "cekilen_veriler/tygo"
        os.makedirs(hedef_klasor, exist_ok=True)

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)
        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None

def google_maps_veri_cek(mekan_linki, max_kaydirma) -> str:
    match = re.search(r'/place/([^/]+)/', mekan_linki)
    if match:
        urun_adi = urllib.parse.unquote(match.group(1)).replace('+', ' ').title()
        urun_id = urun_adi[:30].replace(' ', '_')
    else:
        urun_adi = "Google Maps Mekanı"
        urun_id = str(int(time.time()))

    dosya_yolu = f"cekilen_veriler/maps/maps_{urun_id}.json"

    logger.info(f"🔍 Google Maps ID Çözümleniyor: {urun_id}")
    gorsel_url = "Görsel Bulunamadı"

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set() # Tekrar kontrolü için hafıza
    MAX_YORUM_SINIRI = 500   # Hedef limit

    logger.info("🔍 Google Maps yorumlarına erişmek için Playwright başlatılıyor...")
    try:
        from playwright.sync_api import sync_playwright

        profil_klasoru = os.path.join(os.getcwd(), "../saved_maps_profile")
        os.makedirs(profil_klasoru, exist_ok=True)

        with sync_playwright() as p:
            # SİHİR: Test tarayıcısı uyarısını tamamen gizleyen parametre eklendi!
            context = p.chromium.launch_persistent_context(
                user_data_dir=profil_klasoru,
                headless=False,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
                locale="tr-TR",
                ignore_default_args=["--enable-automation"], # O sinir bozucu banner'ı siler
                args=["--disable-blink-features=AutomationControlled"]
            )

            page = context.pages[0] if context.pages else context.new_page()

            try:
                from playwright_stealth import stealth_sync
                stealth_sync(page)
            except Exception:
                pass

            page.goto(mekan_linki, timeout=30000)

            # --- SİHİR 0: Çerez / KVKK Pop-up Kapatıcı ---
            try:
                cerez_btn = page.locator('button:has-text("Tümünü kabul et"), button:has-text("Accept all")')
                if cerez_btn.count() > 0:
                    cerez_btn.first.click(timeout=3000)
                    time.sleep(1)
            except: pass

            # --- SİHİR 1: AKILLI GÖRSEL AVCISI (AVATARLAR YASAKLANDI) ---
            try:
                page.wait_for_selector('img[src*="googleusercontent.com"]', timeout=10000)
                time.sleep(2)  # JS'nin görseli işlemesi için ek süre
                gorsel_url = page.evaluate('''() => {
                    const images = Array.from(document.querySelectorAll('img'));
                    
                    const validImages = images.filter(img => {
                        const src = img.src || "";
                        return src.includes('googleusercontent.com') && 
                               !src.includes('staticmap') && 
                               !src.includes('streetview') &&
                               !src.includes('/mo/') && 
                               !src.includes('/profile/') && 
                               !src.includes('/a/') &&       
                               img.width > 120; 
                    });
                    
                    if(validImages.length > 0) {
                        const bestMatch = validImages.find(img => img.src.includes('/p/') || img.src.includes('/places/'));
                        return bestMatch ? bestMatch.src : validImages[0].src;
                    }
                    return "Görsel Bulunamadı";
                }''')

                if gorsel_url != "Görsel Bulunamadı":
                    gorsel_url = re.sub(r'=w\d+-h\d+.*', '=w800-h800-k-no', gorsel_url)
                    logger.info(f"🖼️ Maps Mekan Görseli Akıllıca Çekildi: {gorsel_url}")
                else:
                    logger.warning("⚠️ Maps mekan görseli bulunamadı, alternatif yöntemler denenebilir.")
            except Exception as e:
                logger.warning(f"   [Uyarı] Maps görseli çekilirken sorun oluştu: {e}")

            # --- SİHİR 2: KURŞUN GEÇİRMEZ SEKME TIKLAYICI ---
            try:
                sekme_bulundu = False
                for rol in ["tab", "button"]:
                    for isim in [re.compile(r"^Yorumlar$", re.IGNORECASE), re.compile(r"^Reviews$", re.IGNORECASE)]:
                        sekme = page.get_by_role(rol, name=isim)
                        if sekme.count() > 0 and sekme.first.is_visible():
                            sekme.first.click(timeout=3000)
                            sekme_bulundu = True
                            logger.info(f"   👉 Yorumlar sekmesine tıklandı (Taktik 1: Rol={rol}, İsim={isim.pattern}).")
                            break
                    if sekme_bulundu: break

                if not sekme_bulundu:
                    yedek_sekme = page.locator('button:has-text("Yorumlar"), div[role="tab"]:has-text("Yorumlar")').first
                    if yedek_sekme.count() > 0 and yedek_sekme.is_visible():
                        yedek_sekme.click(timeout=3000)
                        logger.info("   👉 Yorumlar sekmesine tıklandı (Taktik 2: Yedek Seçici).")
                time.sleep(2)
            except Exception: pass

            # --- SİHİR 3: AKILLI KAYDIRMA (SCROLL) ---
            try:
                page.wait_for_selector('.wiI7pd', timeout=15000)
                for i in range(max_kaydirma):
                    page.evaluate('''() => {
                        const panels = Array.from(document.querySelectorAll('div[role="main"], div.m6QErb'));
                        let mainPanel = panels.find(p => p.scrollHeight > 1000) || panels[panels.length - 1];
                        if(mainPanel) mainPanel.scrollBy(0, 10000);
                    }''')
                    time.sleep(1.5)
                    logger.info(f"   ⬇️ Panel kaydırıldı ({i+1}/{max_kaydirma})")
            except Exception: pass

            # --- SİHİR 4: VERİLERİ DETAYLI TOPLAMA ---
            more_buttons = page.locator("button.w8nwRe")
            for i in range(more_buttons.count()):
                try: more_buttons.nth(i).click(timeout=500)
                except: pass
            time.sleep(1)

            ham_yorumlar = page.evaluate('''() => {
                let results = [];
                let seenSignatures = new Set(); 

                let reviewBlocks = document.querySelectorAll('.jftiEf, div[data-review-id]');

                for(let block of reviewBlocks) {
                    let nameEl = block.querySelector('.d4r55') || block.querySelector('.WNxzHc');
                    let isim = nameEl ? nameEl.innerText.trim() : "Bilinmiyor";

                    let textEl = block.querySelector('.wiI7pd');
                    let metin = textEl ? textEl.innerText.trim() : "";

                    let imza = isim + "_" + metin;

                    if(metin.length > 0 && !seenSignatures.has(imza)) {
                        let dateEl = block.querySelector('.rsqaWe');
                        let tarih = dateEl ? dateEl.innerText.trim() : "Bilinmiyor";

                        let ratingEl = block.querySelector('.kvMYJc') || block.querySelector('span[role="img"]');
                        let puan = "Bilinmiyor";
                        if(ratingEl && ratingEl.getAttribute('aria-label')) {
                            puan = ratingEl.getAttribute('aria-label');
                        }

                        results.push({
                            isim: isim, 
                            tarih: tarih, 
                            puan: puan, 
                            orijinal_metin: metin
                        });
                        seenSignatures.add(imza);
                    }
                }
                return results;
            }''')

            # 4.3 Python tarafında MÜHENDİSLİK ZIRHI ile temizliği yap ve kaydet
            for yrm in ham_yorumlar:
                # KONTROL 1: Limit doldu mu?
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
                    break

                temiz_metin = preprocessor.clean_text(yrm["orijinal_metin"], "maps")

                # KONTROL 2: Kalite testlerini geçiyor mu?
                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            page.close()
            context.close()
    except Exception as e:
        logger.warning(f"   [Uyarı] Playwright Maps'te bir engele takıldı veya beklenmedik bir hata oluştu: {e}")

    if tum_yorumlar:
        veri_seti = {"platform": "maps", "baslik": urun_adi, "link": mekan_linki, "gorsel_url": gorsel_url, "yorumlar": tum_yorumlar}

        hedef_klasor = "cekilen_veriler/maps"
        os.makedirs(hedef_klasor, exist_ok=True)

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)
        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None

# ==========================================
# 4. EVRENSEL YÖNLENDİRİCİ (ANA MOTOR)
# ==========================================
def linkten_veri_cek(url, platform, max_sayfa=15, max_kaydirma=15):
    try:
        if platform == "trendyol-go":
            dosya_yolu = trendyol_go_veri_cek(url, max_sayfa=max_sayfa)
            return "Trendyol Go verileri başarıyla çekildi.", dosya_yolu

        elif platform == "trendyol":
            dosya_yolu = trendyol_veri_cek(url, max_sayfa=max_sayfa)
            return "Trendyol verileri başarıyla çekildi.", dosya_yolu

        elif platform == "hepsiburada":
            dosya_yolu = hepsiburada_veri_cek(url, max_sayfa=max_sayfa)
            return "Hepsiburada verileri başarıyla çekildi.", dosya_yolu

        elif platform == "ciceksepeti":
            dosya_yolu = ciceksepeti_veri_cek(url, max_sayfa=max_sayfa)
            return "Çiçeksepeti verileri başarıyla çekildi.", dosya_yolu

        elif platform == "steam":
            dosya_yolu = steam_veri_cek(url, max_sayfa=max_sayfa)
            return "Steam verileri başarıyla çekildi.", dosya_yolu

        elif platform == "yemeksepeti":
            dosya_yolu = yemeksepeti_veri_cek(url, max_sayfa=max_sayfa)
            return "Yemeksepeti verileri başarıyla çekildi.", dosya_yolu

        elif platform == "etstur":
            dosya_yolu = etstur_veri_cek(url, max_sayfa=max_sayfa)
            return "Etstur verileri başarıyla çekildi.", dosya_yolu

        elif platform == "airbnb":
            dosya_yolu = airbnb_veri_cek(url, max_sayfa=max_sayfa)
            return "Airbnb verileri başarıyla çekildi.", dosya_yolu

        elif platform == "maps":
            dosya_yolu = google_maps_veri_cek(url, max_kaydirma=max_kaydirma)
            return "Google Maps verileri başarıyla çekildi.", dosya_yolu

        else:
            return f"❌ Bilinmeyen veya desteklenmeyen platform: '{platform}'", None

    except Exception as e:
        return f"❌ Kazıma işlemi sırasında kritik bir hata oluştu: {str(e)}", None