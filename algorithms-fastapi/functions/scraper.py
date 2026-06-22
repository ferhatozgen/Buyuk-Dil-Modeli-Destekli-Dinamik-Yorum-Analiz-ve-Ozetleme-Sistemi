from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
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
import random
from functions.utils import upload_to_cloudinary
logger = setup_logger()

# Projenin kök dizinini bulur ve dicts klasörünü sabitleriz.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICTS_DIR = os.path.join(BASE_DIR, "functions", "dicts")

def kategori_verilerini_yukle():
    dosya_yolu = os.path.join(DICTS_DIR, "maps_ham_kategoriler.json")
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["ana_kategori_haritasi"], data["varsayilan_kategori"]
    except Exception as e:
        logger.error(f"⚠️ Kategori haritası yüklenemedi: {e}")
        return {}, "Diğer"

# Sadece 1 kere çalışır ve hafızada tutar
KATEGORI_HARITASI, VARSAYILAN_KATEGORI = kategori_verilerini_yukle()


def kategoriyi_eslestir(ham_kategori, urun_adi):
    # Türkçe karakterleri tolere etmek için basit temizlik
    aranacak_metin = f"{ham_kategori} {urun_adi}".lower()
    aranacak_metin = aranacak_metin.replace('i̇', 'i').replace('ı', 'i').replace('I', 'ı')

    for ana_kategori, kelimeler in KATEGORI_HARITASI.items():
        for kelime in kelimeler:
            if kelime in aranacak_metin:
                return ana_kategori

    return VARSAYILAN_KATEGORI


# ==========================================
# 1. VERİ TEMİZLEME SINIFI (PREPROCESSOR)
# ==========================================
def kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar_seti, min_kelime=4):
    if len(temiz_metin.split()) < min_kelime:
        return False
    if temiz_metin in gorulen_yorumlar_seti:
        return False
    try:
        if detect(temiz_metin) != 'tr':
            return False
    except:
        return False
    return True

class ReviewPreprocessor:
    def __init__(self, typo_file="duzeltmeler.json", bad_words_file="bad_words.json"):
        typo_path = os.path.join(DICTS_DIR, typo_file)
        bad_words_path = os.path.join(DICTS_DIR, bad_words_file)

        self.typo_mapping = self._load_json(typo_path, dict)
        self.bad_words = set(self._load_json(bad_words_path, list))

    def _load_json(self, path, default_type):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ Sözlük dosyası okunamadı ({path}): {e}")
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
        text = " ".join(
            [w for w in words if not (re.search(r'[aeıioöuü]{3,}', w) or re.search(r'[bcçdfgğhjklmnprsştvyz]{4,}', w))])

        if self.bad_words:
            for bad_word in self.bad_words:
                text = re.sub(r'\b' + re.escape(bad_word) + r'\b', '', text, flags=re.IGNORECASE)

        return re.sub(r'\s+', ' ', text).strip()


# ==========================================
# 2. YARDIMCI VE DEDEKTİF FONKSİYONLAR
# ==========================================
def get_og_image(url):
    """Verilen URL'nin kaynak koduna girip sosyal medya (og:image) görselini çeker."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}
    try:
        res = curl_requests.get(url, headers=headers, impersonate="chrome124", timeout=10, verify=False)

        # Regex yerine BeautifulSoup kullandık (Daha az hata verir)
        soup = BeautifulSoup(res.text, 'html.parser')
        og_img = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'og:image'})

        if og_img and og_img.get('content'):
            orijinal_link = og_img['content']
            # Buluta yükle ve kalıcı linki dön
            return upload_to_cloudinary(orijinal_link)

        return "Görsel Bulunamadı"
    except Exception as e:
        logger.warning(f"⚠️ Görsel çekilemedi ({url}): {e}")
        return "Görsel Bulunamadı"


def yorum_metnini_bul(yorum):
    """Farklı JSON formatlarındaki asıl yorum metnini otomatik bulur."""
    if isinstance(yorum, str): return yorum
    olasi_anahtarlar = ["metin", "comment", "review", "text", "customerDescription", "comments", "reviewText",
                        "content"]
    if isinstance(yorum, dict):
        for key in olasi_anahtarlar:
            if key in yorum and isinstance(yorum[key], str): return yorum[key]
        string_degerler = [v for v in yorum.values() if isinstance(v, str) and len(v) > 5]
        if string_degerler: return max(string_degerler, key=len)
    return ""


def json_icinde_ara(veri, aranan_anahtar):
    """JSON içinde herhangi bir derinlikteki anahtarı bulur (Recursive Search)"""
    if isinstance(veri, dict):
        if aranan_anahtar in veri:
            return veri[aranan_anahtar]
        for v in veri.values():
            sonuc = json_icinde_ara(v, aranan_anahtar)
            if sonuc is not None:
                return sonuc
    elif isinstance(veri, list):
        for eleman in veri:
            sonuc = json_icinde_ara(eleman, aranan_anahtar)
            if sonuc is not None:
                return sonuc
    return None


def genel_yorum_bul(json_verisi, hedef_anahtarlar):
    """
    Bütün platformlardaki 'yorum_bul' fonksiyonlarının anasıdır.
    Verilen anahtarlardan (liste) herhangi birini içeren sözlük listesini bulur.
    """
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        # Listedeki ilk eleman aradığımız anahtarlardan birini içeriyor mu?
        if any(anahtar in json_verisi[0] for anahtar in hedef_anahtarlar):
            return json_verisi

    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = genel_yorum_bul(deger, hedef_anahtarlar)
            if sonuc: return sonuc

    return []

# --- PLATFORM FONKSİYONLARI (Wrapper / Sarıcı) ---
# Orijinal fonksiyon isimlerini koruduk ki ana scraper kodların bozulmasın.

def trendyol_yorum_bul(json_verisi):
    return genel_yorum_bul(json_verisi, ["comment"])

def hb_yorum_bul(json_verisi):
    return genel_yorum_bul(json_verisi, ["review", "star", "customerName"])

def yemeksepeti_yorum_bul(json_verisi):
    return genel_yorum_bul(json_verisi, ["rating", "customerDescription"])

def trendyol_go_yorum_bul(json_verisi):
    return genel_yorum_bul(json_verisi, ["comment", "rate", "customerName"])

def etstur_yorum_bul(json_verisi):
    return genel_yorum_bul(json_verisi, ["text", "comment", "reviewText", "customer"])

def airbnb_yorum_bul(json_verisi):
    # Airbnb'nin bilinen tam yolunu (fast-path) önce deniyoruz, daha hızlı sonuç verir.
    try:
        reviews_data = json_verisi.get("data", {}).get("presentation", {}).get("stayProductDetailPage", {}).get("reviews", {}).get("reviews", [])
        if reviews_data: return reviews_data
    except Exception:
        pass
    # Eğer yapı değişmişse veya üstteki yoldan bulunamazsa genel tarama devreye girer.
    return genel_yorum_bul(json_verisi, ["comments", "commentV2"])


# --- GÖRSEL VE EVENT LISTENER ---

def yemeksepeti_gorsel_bul(json_verisi):
    """Yemeksepeti'nin devasa Next.js JSON'ı içinde logo veya afiş arar."""
    if isinstance(json_verisi, dict):
        olasi_anahtarlar = ["logo", "heroImageUrl", "hero_listing_image", "hero_image", "image", "vendorPicture"]
        for key in olasi_anahtarlar:
            val = json_verisi.get(key)
            if isinstance(val, str) and val.startswith("http") and ("deliveryhero" in val or "yemeksepeti" in val):
                return val

        for _, deger in json_verisi.items():
            sonuc = yemeksepeti_gorsel_bul(deger)
            if sonuc: return sonuc

    elif isinstance(json_verisi, list):
        for eleman in json_verisi:
            sonuc = yemeksepeti_gorsel_bul(eleman)
            if sonuc: return sonuc
    return None

def handle_response(response):
    if "vendor" in response.url and response.status == 200:
        try:
            data = response.json()
            potential_img = yemeksepeti_gorsel_bul(data)
            if potential_img:
                logger.info(f"🎯 API'den Görsel Yakalandı: {potential_img}")
                # DİKKAT: Burada görseli sadece logluyorsun ama dışarıya döndürmüyorsun.
                # Playwright içinde bunu kullanabilmek için bu konuyu Yemeksepeti scraper'ında çözeceğiz.
        except Exception:
            pass


# ==========================================
# 3. PLATFORM FONKSİYONLARI
# ==========================================
def trendyol_veri_cek(urun_linki, max_sayfa) -> str:
    match = re.search(r'-p-(\d+)', urun_linki)
    if not match: return None
    urun_id = match.group(1)

    isim_match = re.search(r'/([^/]+)-p-\d+', urun_linki)
    urun_adi = isim_match.group(1).replace('-', ' ').title() if isim_match else "Trendyol Ürünü"

    logger.info(f"🔍 Trendyol ID Çözümleniyor: {urun_id}")
    gorsel_url = get_og_image(urun_linki)

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hedef_klasor = os.path.join(BASE_DIR, "cekilen_veriler", "trendyol")
    os.makedirs(hedef_klasor, exist_ok=True)
    dosya_yolu = os.path.join(hedef_klasor, f"trendyol_{urun_id}.json")

    # --- KATEGORİ ÇEKME (JSON-LD ve Güncel HTML Hibrit) ---
    kategori_agaci = []
    try:
        # HATA DÜZELTME 1: HTML çekerken de Anti-Bot (impersonate) korumasını ekledik!
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}
        html_res = curl_requests.get(urun_linki, headers=headers, timeout=15, impersonate="chrome124", verify=False)
        soup = BeautifulSoup(html_res.text, 'html.parser')

        urun_adi_html_icinde = ""
        try:
            urun_baslik = soup.find('h1')
            if urun_baslik:
                urun_adi_html_icinde = urun_baslik.text.strip().lower()
        except:
            pass

        kategoriler = []

        # HATA DÜZELTME 2: JSON-LD okuma mantığı Trendyol'un WebPage -> breadcrumb yapısına uyarlandı
        for script in soup.find_all('script', type='application/ld+json'):
            if not script.string: continue
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]

                for obj in items:
                    # İç içe geçmiş 'breadcrumb' objesini yakalıyoruz
                    breadcrumb_data = obj.get('breadcrumb', {})
                    if breadcrumb_data.get('@type') == 'BreadcrumbList':
                        for el in breadcrumb_data.get('itemListElement', []):
                            cat_name = el.get('item', {}).get('name') or el.get('name')
                            if cat_name and cat_name.strip() != "Trendyol":
                                isim = cat_name.strip()
                                if urun_adi_html_icinde and isim.lower() in urun_adi_html_icinde and len(isim) > 20:
                                    continue
                                if isim not in kategoriler:
                                    kategoriler.append(isim)

                        if kategoriler: break
                if kategoriler: break
            except Exception:
                continue

        # 2. TAKTİK: JSON-LD'den bulunamadıysa HTML yapısından çekme
        if not kategoriler:
            breadcrumb_ul = soup.find('ul', class_='breadcrumb')
            if breadcrumb_ul:
                kategori_etiketleri = breadcrumb_ul.find_all('li')
                for li in kategori_etiketleri:
                    isim = li.text.strip()
                    if isim and isim != "Trendyol":
                        if urun_adi_html_icinde and isim.lower() in urun_adi_html_icinde and len(isim) > 20:
                            continue
                        if isim not in kategoriler:
                            kategoriler.append(isim)

        if kategoriler and len(kategoriler[-1]) > 35:
            kategoriler.pop()

        if kategoriler:
            kategori_agaci = kategoriler

        logger.info(f"📁 Kategori Bulundu: {kategori_agaci}")
    except Exception as e:
        logger.warning(f"⚠️ Kategori çekilemedi: {e}")
    # -----------------------------------------------------

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set()
    MAX_YORUM_SINIRI = 200

    headers = {"Accept": "application/json", "Origin": "https://www.trendyol.com", "Referer": urun_linki}

    for sayfa in range(max_sayfa):
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        api_url = f"https://apigw.trendyol.com/discovery-storefront-trproductgw-service/api/review-read/product-reviews/detailed?channelId=1&contentId={urun_id}&page={sayfa}"
        try:
            res = curl_requests.get(api_url, headers=headers, impersonate="chrome124", timeout=10, verify=False)
            if res.status_code != 200: break

            yorum_listesi = trendyol_yorum_bul(res.json())
            if not yorum_listesi: break

            for yrm in yorum_listesi:
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI: break

                ham_metin = yorum_metnini_bul(yrm)
                temiz_metin = preprocessor.clean_text(ham_metin, "trendyol")

                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            time.sleep(0.5)
        except Exception:
            break

    if tum_yorumlar:
        veri_seti = {
            "platform": "trendyol",
            "baslik": urun_adi,
            "kategori": kategori_agaci,
            "link": urun_linki,
            "gorsel_url": gorsel_url,
            "yorumlar": tum_yorumlar
        }

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)

        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None

def hepsiburada_veri_cek(urun_linki, max_sayfa) -> str:
    match = re.search(r'-p[m]?-([A-Za-z0-9]+)', urun_linki)
    if not match: return None
    urun_sku = match.group(1).upper()

    isim_match = re.search(r'/([^/]+)-p[m]?-', urun_linki)
    urun_adi = isim_match.group(1).replace('-', ' ').title() if isim_match else "Hepsiburada Ürünü"

    logger.info(f"🔍 Hepsiburada SKU Çözümleniyor: {urun_sku}")
    gorsel_url = "Görsel Bulunamadı"

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hedef_klasor = os.path.join(BASE_DIR, "cekilen_veriler", "hepsiburada")
    os.makedirs(hedef_klasor, exist_ok=True)
    dosya_yolu = os.path.join(hedef_klasor, f"hepsiburada_{urun_sku}.json")

    # --- KATEGORİ ÇEKME (TAMAMEN SENİN ORİJİNAL KODUN) ---
    kategori_agaci = []
    try:
        html_res = curl_requests.get(
            urun_linki,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"},
            timeout=15,
            impersonate="chrome124",
            verify=False
        )
        soup = BeautifulSoup(html_res.text, 'html.parser')

        next_data_script = soup.find('script', id='__NEXT_DATA__')
        if next_data_script and next_data_script.string:
            try:
                data = json.loads(next_data_script.string)

                bc_data = json_icinde_ara(data, 'breadcrumb')
                if isinstance(bc_data, dict) and 'itemListElement' in bc_data:
                    breadcrumbs_list = bc_data['itemListElement']
                    kategoriler = [el.get('name') for el in breadcrumbs_list if el.get('name') and el.get('name') != "Anasayfa"]
                    if 0 < len(kategoriler) <= 10:
                        kategori_agaci = kategoriler

                if not kategori_agaci:
                    bcs_list = json_icinde_ara(data, 'breadcrumbs')
                    if bcs_list and isinstance(bcs_list, list):
                        kategoriler = [b.get('name') for b in bcs_list if isinstance(b, dict) and b.get('name')]
                        if kategoriler and 0 < len(kategoriler) <= 10:
                            kategori_agaci = kategoriler

                if not kategori_agaci:
                    category_str = json_icinde_ara(data, 'category')
                    if isinstance(category_str, str) and " > " in category_str:
                        kategori_agaci = category_str.split(" > ")

            except Exception:
                pass

        if not kategori_agaci:
            for script in soup.find_all('script', type='application/ld+json'):
                if script.string:
                    try:
                        data = json.loads(script.string)
                        items = data.get('@graph', []) if isinstance(data, dict) and '@graph' in data else (
                            data if isinstance(data, list) else [data])

                        for obj in items:
                            if isinstance(obj, dict) and obj.get('@type') == 'BreadcrumbList':
                                kategoriler = []
                                for el in obj.get('itemListElement', []):
                                    cat_name = el.get('name')
                                    if not cat_name and isinstance(el.get('item'), dict):
                                        cat_name = el.get('item').get('name')
                                    if cat_name and cat_name.lower() != "anasayfa":
                                        kategoriler.append(cat_name)

                                if 0 < len(kategoriler) <= 10:
                                    kategori_agaci = kategoriler
                                    break

                            elif isinstance(obj, dict) and obj.get('@type') == 'Product' and obj.get('category'):
                                cat_str = obj.get('category')
                                if " > " in cat_str:
                                    kategori_agaci = cat_str.split(" > ")
                                    break

                        if kategori_agaci:
                            break
                    except Exception:
                        continue

        logger.info(f"📁 Kategori Bulundu: {kategori_agaci}")

    except Exception as e:
        logger.warning(f"⚠️ Hepsiburada Kategori çekilemedi: {e}")
    # -----------------------------------------------------

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set()
    MAX_YORUM_SINIRI = 200
    headers = {"Accept": "application/json", "Origin": "https://www.hepsiburada.com", "Referer": urun_linki}

    for sayfa in range(max_sayfa):
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break
        offset = sayfa * 20
        api_url = f"https://user-content-gw-hermes.hepsiburada.com/queryapi/v2/ApprovedUserContents?sku={urun_sku}&from={offset}&size=20"
        try:
            res = curl_requests.get(api_url, headers=headers, impersonate="chrome124", timeout=10, verify=False)
            if res.status_code != 200: break

            data = res.json()
            yorum_listesi = data.get("approvedUserContents", [])
            if not yorum_listesi: yorum_listesi = hb_yorum_bul(data)
            if not yorum_listesi: break

            if sayfa == 0 and yorum_listesi and gorsel_url == "Görsel Bulunamadı":
                ilk_yorum = yorum_listesi[0]
                img_raw = ilk_yorum.get("product", {}).get("imageUrl", "")
                if img_raw:
                    gorsel_url = img_raw.replace("{size}", "500")

            for yrm in yorum_listesi:
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    break

                ham_metin = yrm.get("review", {}).get("content", "")
                temiz_metin = preprocessor.clean_text(ham_metin, "hepsiburada")

                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)
            time.sleep(1)
        except Exception:
            break

    if tum_yorumlar:
        veri_seti = {
            "platform": "hepsiburada",
            "baslik": urun_adi,
            "kategori": kategori_agaci,
            "link": urun_linki,
            "gorsel_url": gorsel_url,
            "yorumlar": tum_yorumlar
        }

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)
        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None


def ciceksepeti_veri_cek(urun_linki, max_sayfa) -> str:
    # 1. URL'den ürün kodu ve ismini çıkar
    match_code = re.search(r'-([a-zA-Z0-9]+)(?:\?|/|$)', urun_linki)
    urun_kodu = match_code.group(1).lower() if match_code else str(int(time.time()))

    isim_match = re.search(r'/([^/]+)-[a-zA-Z0-9]+(?:\?|/|$)', urun_linki)
    urun_adi = isim_match.group(1).replace('-', ' ').title() if isim_match else "Çiçeksepeti Ürünü"

    # --- MUTLAK YOL GÜNCELLEMESİ ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hedef_klasor = os.path.join(BASE_DIR, "cekilen_veriler", "ciceksepeti")
    os.makedirs(hedef_klasor, exist_ok=True)
    dosya_yolu = os.path.join(hedef_klasor, f"ciceksepeti_{urun_kodu}.json")
    # -------------------------------

    logger.info(f"🔍 Çiçeksepeti Kodu Çözümleniyor: {urun_kodu}")

    # 2. Session (Oturum) Başlatma
    session = curl_requests.Session()
    headers_main = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        # Ana sayfadan Product ID'yi çek
        res = session.get(urun_linki, headers=headers_main, impersonate="chrome124", timeout=20, verify=False)
        if res.status_code != 200:
            logger.error(f"❌ Ürün sayfasına ulaşılamadı. Statü: {res.status_code}")
            return None

        id_match = re.search(r'data-productid=["\'](\d+)["\']', res.text, re.IGNORECASE) or \
                   re.search(r'"productId"\s*:\s*(\d+)', res.text, re.IGNORECASE)
        if not id_match:
            logger.error(f"❌ Product ID bulunamadı!")
            return None
        gercek_urun_id = id_match.group(1)
        logger.info(f"🆔 Gerçek Ürün ID Tespit Edildi: {gercek_urun_id}")
    except Exception as e:
        logger.error(f"❌ Bağlantı Hatası: {e}")
        return None

    gorsel_url = "Görsel Bulunamadı"
    try:
        gorsel_url = get_og_image(urun_linki)
    except:
        pass

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set()
    MAX_YORUM_SINIRI = 200

    api_headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": urun_linki,
        "Accept": "*/*"
    }

    # --- SİHİRLİ ANAHTAR: BAŞLANGIÇ CURSOR'I ---
    cursor = ""

    # 3. Döngü: Yorumları Sayfa Sayfa Çek
    for sayfa in range(1, max_sayfa + 1):
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        # Cursor URL encode edilerek API linkine ekleniyor!
        cursor_param = urllib.parse.quote(cursor) if cursor else ""
        api_url = f"https://www.ciceksepeti.com/Review/GetReviews?productId={gercek_urun_id}&page={sayfa}&cursor={cursor_param}&hideRatingandOrderButtons=false"

        try:
            response = session.get(api_url, headers=api_headers, impersonate="chrome124", timeout=20, verify=False)

            if response.status_code != 200:
                logger.error(f"❌ Sayfa {sayfa} çekilemedi. Statü: {response.status_code}")
                break

            html_text = response.text
            soup = BeautifulSoup(html_text, 'html.parser')
            yorum_kutulari = soup.find_all("div", class_="ns-reviews--item-wrapper")

            if not yorum_kutulari:
                logger.warning(f"⚠️ Sayfa {sayfa} boş döndü. Yorumlar bitti.")
                break

            for kutu in yorum_kutulari:
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI: break

                metin_span = kutu.find("span", class_="js-review-detail")
                ham_metin = metin_span.get("data-value", "").strip() if metin_span else ""
                gecersiz_metin = "bu ürün için yalnızca puan verilmiştir yorum yapılmamıştır"
                if gecersiz_metin in ham_metin.lower():
                    continue

                temiz_metin = preprocessor.clean_text(ham_metin, "ciceksepeti")

                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)

                    isim_p = kutu.find("p", class_="js-review-name")
                    tarih_p = kutu.find("p", class_="js-review-date")
                    yildiz_alani = kutu.find("div", class_="js-review-stars")
                    dolu_yildizlar = [y for y in yildiz_alani.find_all("span", class_="products-stars__icon") if
                                      "is-passive" not in y.get("class", [])] if yildiz_alani else []

                    yrm = {
                        "isim": isim_p.text.strip() if isim_p else "Bilinmiyor",
                        "tarih": tarih_p.text.strip() if tarih_p else "Bilinmiyor",
                        "puan": f"{len(dolu_yildizlar)} Yıldız",
                        "orijinal_metin": ham_metin,
                        "temiz_metin": temiz_metin
                    }
                    tum_yorumlar.append(yrm)

            # --- SİHİR 2: HTML İÇİNDEKİ SONRAKİ SAYFA CURSOR'INI YAKALAMA ---
            cursor_match = re.search(r'data-cursor=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
            if cursor_match:
                cursor = cursor_match.group(1)
            else:
                logger.info("📄 Sonraki sayfa için imleç (cursor) bulunamadı. Yorumların sonu.")
                break  # Yeni cursor yoksa sayfalama bitmiştir!

            # İnsani davranış için bekleme
            time.sleep(random.uniform(1.5, 3.0))

        except Exception as e:
            logger.error(f"⚠️ Sayfa {sayfa} çekilirken hata oluştu: {e}")
            break

    # 4. Dosyayı Kaydet
    if tum_yorumlar:
        veri_seti = {
            "platform": "ciceksepeti",
            "baslik": urun_adi,
            "link": urun_linki,
            "gorsel_url": gorsel_url,
            "yorumlar": tum_yorumlar
        }

        try:
            with open(dosya_yolu, "w", encoding="utf-8") as f:
                json.dump(veri_seti, f, ensure_ascii=False, indent=4)
            logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
            return dosya_yolu
        except Exception as e:
            logger.error(f"❌ Dosya yazma hatası: {e}")
            return None
    else:
        logger.warning(f"⚠️ Çekilecek yorum bulunamadı: {urun_adi}")
        return None


def steam_veri_cek(oyun_linki, max_sayfa) -> str:
    match = re.search(r'/app/(\d+)', oyun_linki)
    if not match: return None
    app_id = match.group(1)
    isim_match = re.search(r'/app/\d+/([^/?]+)', oyun_linki)
    urun_adi = isim_match.group(1).replace('_', ' ').title() if isim_match else "Steam Oyunu"

    # --- MUTLAK YOL GÜNCELLEMESİ ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hedef_klasor = os.path.join(BASE_DIR, "cekilen_veriler", "steam")
    os.makedirs(hedef_klasor, exist_ok=True)
    dosya_yolu = os.path.join(hedef_klasor, f"steam_{app_id}.json")
    # -------------------------------

    logger.info(f"🔍 Steam ID Çözümleniyor: {app_id}")
    gorsel_url = f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set()  # Tekrar kontrolü
    MAX_YORUM_SINIRI = 200  # Hedef limit
    cursor = "*"

    for sayfa in range(max_sayfa):
        # HEDEF KONTROLÜ
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        encoded_cursor = urllib.parse.quote(cursor)
        api_url = f"https://store.steampowered.com/appreviews/{app_id}?json=1&language=turkish&filter=recent&num_per_page=100&cursor={encoded_cursor}"
        try:
            res = curl_requests.get(api_url, impersonate="chrome124", timeout=10, verify=False)
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
        except Exception:
            break

    if tum_yorumlar:
        veri_seti = {"platform": "steam", "baslik": urun_adi, "link": oyun_linki, "gorsel_url": gorsel_url,
                     "yorumlar": tum_yorumlar}

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)
        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None


def etstur_veri_cek(otel_linki, max_sayfa) -> str:
    logger.info(f"🔍 Etstur ID'leri Çözümleniyor: {otel_linki}")

    session = curl_requests.Session(impersonate="chrome124")
    try:
        html_res = session.get(otel_linki, timeout=15, verify=False)
        if html_res.status_code != 200: return None

        hotel_id_match = re.search(r'data-hotel-id=["\']([^"\']+)["\']', html_res.text) or re.search(
            r'"hotelId"\s*:\s*["\']([^"\']+)["\']', html_res.text)
        hotel_code_match = re.search(r'data-vendor-code=["\']([^"\']+)["\']', html_res.text) or re.search(
            r'"vndCode"\s*:\s*["\']([^"\']+)["\']', html_res.text)
        if not hotel_code_match or not hotel_id_match: return None
        hotel_code = hotel_code_match.group(1)
        hotel_id = hotel_id_match.group(1)
    except Exception:
        return None

    isim_match = re.search(r'etstur\.com/([^/?]+)', otel_linki)
    urun_adi = isim_match.group(1).replace('-', ' ').title() if isim_match else "Etstur Oteli"

    # --- MUTLAK YOL GÜNCELLEMESİ ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hedef_klasor = os.path.join(BASE_DIR, "cekilen_veriler", "etstur")
    os.makedirs(hedef_klasor, exist_ok=True)
    dosya_yolu = os.path.join(hedef_klasor, f"etstur_{hotel_code}.json")
    # -------------------------------

    logger.info(f"🔍 Etstur Kodu Çözümleniyor: {hotel_code}")

    gorsel_url = get_og_image(otel_linki)

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set()  # Tekrar kontrolü için hafıza
    MAX_YORUM_SINIRI = 200  # Hedef limit

    api_url = "https://www.etstur.com/services/api/review"
    api_headers = {"Content-Type": "application/json", "Origin": "https://www.etstur.com", "Referer": otel_linki}

    for sayfa in range(max_sayfa):
        # DIŞ KONTROL
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        payload = {"hotelCode": hotel_code, "hotelId": hotel_id, "offset": sayfa, "sort": "BOOKING_DESC", "period": "",
                   "categoryType": "OVERALL", "searchText": ""}
        try:
            response = session.post(api_url, headers=api_headers, json=payload, timeout=20, verify=False)
            if response.status_code != 200:
                logger.warning(f"🛑 Etstur Bot Engeli! Status Code: {response.status_code} (Sayfa: {sayfa})")
                break

            data = response.json()
            yorum_listesi = data.get("reviews", [])
            if not yorum_listesi: yorum_listesi = etstur_yorum_bul(data)
            if not yorum_listesi:
                logger.info(f"ℹ️ Etstur'da daha fazla yorum kalmadı veya bitti. (Sayfa: {sayfa})")
                break
            logger.info(f"📄 Sayfa {sayfa} - API'den {len(yorum_listesi)} ham yorum geldi.")
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

            bekleme = random.uniform(2.5, 5.2)
            time.sleep(bekleme)

        except Exception as e:
            logger.error(f"❌ Etstur API Hatası (Sayfa {sayfa}): {e}")
            break

    session.close()
    if tum_yorumlar:
        veri_seti = {"platform": "etstur", "baslik": urun_adi, "link": otel_linki, "gorsel_url": gorsel_url,
                     "yorumlar": tum_yorumlar}

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)

        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None


def airbnb_veri_cek(oda_linki, max_sayfa) -> str:
    match = re.search(r'/rooms/(\d+)', oda_linki)
    if not match: return None
    oda_id = match.group(1)

    # --- MUTLAK YOL GÜNCELLEMESİ ---
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hedef_klasor = os.path.join(BASE_DIR, "cekilen_veriler", "airbnb")
    os.makedirs(hedef_klasor, exist_ok=True)
    dosya_yolu = os.path.join(hedef_klasor, f"airbnb_{oda_id}.json")
    # -------------------------------

    logger.info(f" 🔍 Airbnb ID Çözümleniyor: {oda_id}")
    gorsel_url = "Görsel Bulunamadı"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
               "Accept-Language": "tr-TR,tr;q=0.9"}
    try:
        max_deneme = 3
        html_res = None
        for deneme in range(max_deneme):
            try:
                html_res = curl_requests.get(oda_linki, headers=headers, impersonate="chrome124", timeout=30,
                                             verify=False)
                break
            except Exception as e:
                if deneme < max_deneme - 1:
                    logger.warning(
                        f"⚠️ Airbnb sayfası yanıt vermedi (Zaman Aşımı). Tekrar deneniyor ({deneme + 1}/{max_deneme})...")
                    time.sleep(3)
                else:
                    raise e

        temiz_html = html_res.text.replace('\\u002F', '/')

        urun_adi = "Airbnb Evi"
        title_match = re.search(r'<title>([^<]+)</title>', temiz_html, re.IGNORECASE)
        if title_match and "Kiralık" not in title_match.group(1) and "Vacation Rentals" not in title_match.group(
                1) and "Airbnb" not in title_match.group(1):
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
        if not api_key_match:
            api_key_match = re.search(r'("key"|"apiKey")\s*:\s*"([^"]+)"', temiz_html)

        if api_key_match:
            api_key = api_key_match.group(2) if len(api_key_match.groups()) > 1 else api_key_match.group(1)
        else:
            logger.error(f"❌ Airbnb API Key Bulunamadı: {oda_id}")
            return None

        sha256Hash = "2ed951bfedf71b87d9d30e24a419e15517af9fbed7ac560a8d1cc7feadfa22e6"
        hash_match = re.search(r'StaysPdpReviewsQuery.*?sha256Hash":"([^"]+)"', temiz_html)
        if hash_match:
            sha256Hash = hash_match.group(1)

        pic_match = re.findall(r'(https://a0\.muscache\.com/im/pictures/[^"\'\?\\]+\.(?:jpg|jpeg|png|webp))',
                               temiz_html)

        for pic in pic_match:
            if any(x in pic for x in ["/hosting/", "/miso/", "/pro/", "/prohost/"]):
                gorsel_url = pic
                break

    except Exception as e:
        logger.error(f"❌ Airbnb Sayfa Hatası: {e}")
        return None

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set()
    MAX_YORUM_SINIRI = 200

    base64_id = base64.b64encode(f"StayListing:{oda_id}".encode('utf-8')).decode('utf-8')
    api_headers = {"Accept": "application/json", "x-airbnb-api-key": api_key, "User-Agent": headers["User-Agent"],
                   "Origin": "https://www.airbnb.com.tr"}

    for sayfa in range(max_sayfa):
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        limit = 24
        offset = sayfa * limit

        variables = {
            "id": base64_id,
            "pdpReviewsRequest": {
                "fieldSelector": "for_p3_translation_only",
                "forPreview": False,
                "limit": limit,
                "first": limit,
                "offset": str(offset),
                "showingTranslationButton": False,
                "sortingPreference": "MOST_RECENT"
            }
        }

        extensions = {"persistedQuery": {"version": 1, "sha256Hash": sha256Hash}}
        params = {
            "operationName": "StaysPdpReviewsQuery",
            "locale": "tr",
            "currency": "TRY",
            "variables": json.dumps(variables, separators=(',', ':')),
            "extensions": json.dumps(extensions, separators=(',', ':'))
        }
        full_url = f"https://www.airbnb.com.tr/api/v3/StaysPdpReviewsQuery/{sha256Hash}?{urllib.parse.urlencode(params)}"

        try:
            response = curl_requests.get(full_url, headers=api_headers, impersonate="chrome124", timeout=15,
                                         verify=False)

            if response.status_code != 200:
                logger.error(f"❌ Airbnb API Hatası (Kod: {response.status_code})")
                break

            data = response.json()

            if "errors" in data:
                logger.error(f"⚠️ Airbnb API İçi Hata: {data['errors']}")

            yorum_listesi = airbnb_yorum_bul(data)

            if not yorum_listesi:
                logger.warning(f"⚠️ API'den yorum gelmedi. Gelen ham veri: {str(data)[:500]}")
                break

            for yrm in yorum_listesi:
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    break

                ham_metin = yorum_metnini_bul(yrm)
                if not ham_metin: continue

                temiz_metin = preprocessor.clean_text(ham_metin, "airbnb")

                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            time.sleep(1.5)
        except Exception:
            break

    if tum_yorumlar:
        veri_seti = {"platform": "airbnb", "baslik": urun_adi, "link": oda_linki, "gorsel_url": gorsel_url,
                     "yorumlar": tum_yorumlar}

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)

        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ Bu üründe çekilecek yorum bulunamadı: {urun_adi}")
        return None


def yemeksepeti_veri_cek(restoran_linki, max_sayfa) -> str:
    match = re.search(r'/restaurant/([a-zA-Z0-9]+)', restoran_linki)
    if not match: return None
    vendor_id = match.group(1)

    isim_match = re.search(r'/restaurant/[^/]+/([^/?]+)', restoran_linki)
    if isim_match:
        ham_isim = isim_match.group(1).replace('-', ' ').title()
        urun_adi = ham_isim.replace(f" {vendor_id.title()}", "").strip()
    else:
        urun_adi = "Yemeksepeti Restoranı"

    # Dosya yolunu orijinal formatına geri çektik
    dosya_yolu = f"cekilen_veriler/yemeksepeti/yemeksepeti_{vendor_id}.json"

    logger.info(f"🔍 Yemeksepeti Vendor ID Çözümleniyor: {vendor_id}")
    gorsel_url = "Görsel Bulunamadı"

    # ==========================================
    # SİHİR 1: CURL-CFFI İLE GÖRSEL ÇEKME (Playwright İptal)
    # ==========================================
    logger.info("🔍 Cloudflare atlatılarak restoran görseli aranıyor...")
    try:
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "tr-TR,tr;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Origin": "https://www.yemeksepeti.com",
            "Referer": restoran_linki
        }

        # curl_cffi'nin impersonate yeteneği sayesinde Cloudflare TLS korumasını doğrudan geçiyoruz
        res = curl_requests.get(restoran_linki, headers=headers, impersonate="chrome124", timeout=15, verify=False)

        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")

            # 1. PLAN: Sitenin Meta (Sosyal Medya) Görselini Çal (En Hızlı ve Garantili Yol)
            og_image = soup.find("meta", property="og:image")

            if og_image and og_image.get("content") and 'deliveryhero' in og_image.get("content"):
                gorsel_url = og_image.get("content")
            else:
                # 2. PLAN: Meta bulunamazsa, HTML içindeki img etiketlerini CDN kalıbına göre tara
                img_tag = soup.find("img", src=lambda x: x and ('deliveryhero' in x.lower() or 'logo' in x.lower() or 'vendor' in x.lower()))
                if img_tag:
                    gorsel_url = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("content")

            if gorsel_url and gorsel_url != "Görsel Bulunamadı":
                if gorsel_url.startswith("//"):
                    gorsel_url = "https:" + gorsel_url
                gorsel_url = gorsel_url.replace('\\u002F', '/')
                logger.info(f" ✅ Görsel Cloudflare aşılarak başarıyla bulundu: {gorsel_url}")
            else:
                logger.warning("   ⚠️ Güvenlik duvarı aşıldı ancak HTML içinde uygun görsel kaynağı tespit edilemedi.")
        else:
            logger.warning(f"   ⚠️ Sayfaya erişilemedi (Status Code: {res.status_code})")

    except Exception as img_err:
        logger.warning(f"   [Uyarı] Görsel aranırken sorun oluştu: {img_err}")

    # ==========================================
    # SİHİR 2: YORUMLARI API'DEN ÇEKME
    # ==========================================
    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set()
    MAX_YORUM_SINIRI = 200
    next_page_key = ""
    headers = {"Accept": "application/json", "Origin": "https://www.yemeksepeti.com", "Referer": restoran_linki}

    for sayfa in range(max_sayfa):
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        api_url = f"https://reviews-api-tr.fd-api.com/reviews/vendor/{vendor_id}?global_entity_id=YS_TR&limit=50&has_dish=true"
        if next_page_key: api_url += f"&nextPageKey={urllib.parse.quote(next_page_key)}"

        try:
            res = curl_requests.get(api_url, headers=headers, impersonate="chrome124", timeout=15, verify=False)
            if res.status_code != 200: break

            data = res.json()
            yorum_listesi = data.get("data", [])

            if not yorum_listesi: yorum_listesi = yemeksepeti_yorum_bul(data)
            if not yorum_listesi: break

            for yrm in yorum_listesi:
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI: break

                ham_metin = yorum_metnini_bul(yrm)
                temiz_metin = preprocessor.clean_text(ham_metin, "yemeksepeti")

                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            yeni_next_page_key = data.get("pageKey")
            if not yeni_next_page_key or yeni_next_page_key == next_page_key: break
            next_page_key = yeni_next_page_key
            time.sleep(0.5)
        except Exception:
            break

    # ==========================================
    # SİHİR 3: KAYDET
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
    if not match: return None
    vendor_id = match.group(1)

    dosya_yolu = f"cekilen_veriler/tygo/tygo_{vendor_id}.json"

    logger.info(f"🔍 Trendyol Go Vendor ID Çözümleniyor: {vendor_id}")
    gorsel_url = "Görsel Bulunamadı"
    headers_main = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}

    try:
        html_res = curl_requests.get(restoran_linki, headers=headers_main, impersonate="chrome124", timeout=10, verify=False)
        isim_match = re.search(r'<title>([^<]+)</title>', html_res.text, re.IGNORECASE)
        urun_adi = isim_match.group(1).split('|')[0].replace('Sipariş', '').strip() if isim_match else "Trendyol Go Restoranı"

        cdn_match = re.search(r'(https://cdn\.tgoapps\.com/[^"\']+\.(?:jpeg|jpg|png|webp))', html_res.text, re.IGNORECASE)
        if cdn_match:
            gorsel_url = cdn_match.group(1)
            logger.info(f"🖼️ Trendyol Go Görseli CDN'den Bulundu: {gorsel_url}")
    except Exception:
        urun_adi = "Trendyol Go Restoranı"

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set()
    MAX_YORUM_SINIRI = 200
    headers = {"Accept": "application/json", "Origin": "https://www.trendyol.com", "Referer": restoran_linki}

    for sayfa in range(1, max_sayfa + 1):
        if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
            logger.info(f" 🎯 Hedeflenen {MAX_YORUM_SINIRI} kaliteli yoruma ulaşıldı.")
            break

        api_url = f"https://api.tgoapis.com/web-restaurant-apirestaurant-santral/restaurants/{vendor_id}/comments?page={sayfa}&pageSize=20&latitude=41.07087&longitude=28.996586&tagVersion=2"
        try:
            res = curl_requests.get(api_url, headers=headers, impersonate="chrome124", timeout=10, verify=False)
            if res.status_code != 200: break

            data = res.json()
            yorum_listesi = trendyol_go_yorum_bul(data)
            if not yorum_listesi: break

            for yrm in yorum_listesi:
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI: break

                ham_metin = yorum_metnini_bul(yrm)
                temiz_metin = preprocessor.clean_text(ham_metin, "trendyol_go")

                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            time.sleep(0.5)
        except Exception:
            break

    if tum_yorumlar:
        veri_seti = {"platform": "trendyol-go", "baslik": urun_adi, "link": restoran_linki, "gorsel_url": gorsel_url,"yorumlar": tum_yorumlar}
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
    # 1. URL Çözümleme
    match = re.search(r'/place/([^/]+)/', mekan_linki)
    if match:
        urun_adi = urllib.parse.unquote(match.group(1)).replace('+', ' ').title()
        urun_id = urun_adi[:30].replace(' ', '_')
    else:
        urun_adi = "Google Maps Mekanı"
        urun_id = str(int(time.time()))

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Hedef klasörün mutlak yolunu oluştur
    hedef_klasor = os.path.join(BASE_DIR, "cekilen_veriler", "maps")
    os.makedirs(hedef_klasor, exist_ok=True)

    # Dosyanın mutlak yolunu oluştur
    dosya_yolu = os.path.join(hedef_klasor, f"maps_{urun_id}.json")
    # ---------------------------------

    logger.info(f"🔍 Google Maps ID Çözümleniyor: {urun_id}")

    gorsel_url = "Görsel Bulunamadı"
    mekan_kategorisi = "Diğer"
    ham_kategori = "Belirlenemedi"

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set()
    MAX_YORUM_SINIRI = 200

    try:
        from playwright.sync_api import sync_playwright
        profil_klasoru = "/app/browser_profiles/maps"
        os.makedirs(profil_klasoru, exist_ok=True)

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profil_klasoru,
                headless=False,  # Hata ayıklama bitene kadar False kalsın
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                ignore_default_args=["--enable-automation"],
                args=["--disable-blink-features=AutomationControlled"]
            )
            import json
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cerez_dosyasi = os.path.join(BASE_DIR, "cookies_maps.json")

            if os.path.exists(cerez_dosyasi):
                try:
                    with open(cerez_dosyasi, 'r', encoding='utf-8') as f:
                        cookies = json.load(f)

                        temiz_cookies = []
                        for cookie in cookies:
                            # 1. Sadece en temel ve zorunlu bilgileri alıyoruz
                            temiz_cookie = {
                                "name": cookie.get("name", ""),
                                "value": cookie.get("value", ""),
                                "domain": cookie.get("domain", ""),
                                "path": cookie.get("path", "/")
                            }

                            # 2. Playwright'ın kabul ettiği opsiyonel alanları güvenli bir şekilde ekliyoruz
                            if "expirationDate" in cookie:
                                temiz_cookie["expires"] = cookie["expirationDate"]
                            if "secure" in cookie:
                                temiz_cookie["secure"] = cookie["secure"]
                            if "httpOnly" in cookie:
                                temiz_cookie["httpOnly"] = cookie["httpOnly"]

                            # 3. SİHİR BURADA: sameSite hatalarını Playwright'ın diline çeviriyoruz
                            if "sameSite" in cookie:
                                val = cookie["sameSite"].lower()
                                if val == "no_restriction":
                                    temiz_cookie["sameSite"] = "None"
                                elif val == "lax":
                                    temiz_cookie["sameSite"] = "Lax"
                                elif val == "strict":
                                    temiz_cookie["sameSite"] = "Strict"
                                # Eğer "unspecified" ise hiç eklemiyoruz, Playwright kendisi karar versin.

                            temiz_cookies.append(temiz_cookie)

                        context.add_cookies(temiz_cookies)
                        logger.info("🍪 Çerezler formatlanarak başarıyla enjekte edildi!")
                except Exception as e:
                    logger.warning(f"⚠️ Çerez enjeksiyonu başarısız: {e}")
            # ==========================================

            page = context.pages[0] if context.pages else context.new_page()
            page.goto(mekan_linki, timeout=60000)

            # --- SİHİR 0: Çerezleri Hızlıca Geç ---
            try:
                page.click('button:has-text("Tümünü kabul et"), button:has-text("Accept all")', timeout=3000)
            except:
                pass

            # --- KATEGORİ ÇEKME VE TEMİZLEME (Maps'e Özel) ---
            try:
                # Doğrudan kategori aksiyonuna sahip elementi hedef alıyoruz
                ham_kategori = page.locator('[jsaction*="pane.rating.category"]').first.inner_text(timeout=3000)

                # Google UI metinlerini temizle (İstisna Kontrolü)
                if "fotoğrafları göster" in ham_kategori.lower() or "tümünü gör" in ham_kategori.lower():
                    ham_kategori = ""

                logger.info(f"📌 Maps'ten ham kategori çekildi: '{ham_kategori}'")
            except:
                ham_kategori = ""

            # --- DİNAMİK OTEL TESPİTİ (Sadece Metne Değil, Arayüze de Bakıyoruz) ---
            mekan_kategorisi = None

            # 1. AŞAMA: DOM (Sayfa) Analizi ile Kesin Otel Tespiti
            # İsmi ne olursa olsun, sayfada otellere özgü rezervasyon/fiyat araçları var mı?
            is_hotel_dom = page.evaluate('''() => {
                const text = document.body.innerText.toLowerCase();
                // Sayfada otellere özgü widget veya kelimeler aranıyor
                return text.includes("müsaitlik durumunu") || 
                       text.includes("gecelik") || 
                       text.includes("oda ayırt") ||
                       document.querySelector('button[aria-label*="Giriş tarihi"]') !== null;
            }''')

            if is_hotel_dom:
                mekan_kategorisi = "otel"
                logger.info("🏨 Sayfa yapısı incelendi: Mekanın 'otel' olduğu kesinleşti (DOM Analizi).")

            # 2. AŞAMA: İsim ve Regex Kontrolü (Senin yazdığın stratejik öncelikler)
            if not mekan_kategorisi:
                ham_kategori_temiz = str(ham_kategori).lower().replace('i̇', 'i').replace('ı', 'i')
                urun_adi_temiz = str(urun_adi).lower().replace('i̇', 'i').replace('ı', 'i')

                otel_sinyalleri = ["hotel", "otel", "resort", "pansiyon", "apart", "hostel", "konaklama", "villa", "bungalov"]
                otel_kalip = r".*\d+\s*yildizli\s*otel.*|.*otel.*|.*hotel.*|.*resort.*"

                if any(kelime in urun_adi_temiz for kelime in otel_sinyalleri) or \
                        re.match(otel_kalip, ham_kategori_temiz) or \
                        re.match(otel_kalip, urun_adi_temiz):
                    mekan_kategorisi = "otel"
                    logger.info("🏨 Metin/Regex analizi ile mekanın 'otel' olduğu tespit edildi.")


            # 4. AŞAMA: Hiçbiri tutmadıysa Sözlükten (Genel Fonksiyon) Kategori Çek
            if not mekan_kategorisi:
                mekan_kategorisi = kategoriyi_eslestir(ham_kategori, urun_adi)

            logger.info(f"📌 Kategori eşleştirildi: '{mekan_kategorisi}'")


            # --- SİHİR 0.5: GÖRSEL ÇEKME ---
            try:
                time.sleep(2)  # Resimlerin yüklenmesi için ufak bir bekleme
                gorsel_url = page.evaluate('''() => {
                    // Google Maps'teki ana mekan resmini bul
                    const img = document.querySelector('button img[src*="googleusercontent.com/p/"]') || 
                                document.querySelector('div.m6QErb img[src*="googleusercontent.com"]');
                    if (img && img.src) {
                        return img.src;
                    }
                    return "Görsel Bulunamadı";
                }''')

                if gorsel_url != "Görsel Bulunamadı":
                    # Thumbnail boyutunu büyüt
                    gorsel_url = re.sub(r'=w\d+-h\d+.*', '=w800-h800-k-no', gorsel_url)
                    logger.info(f"🖼️ Mekan Görseli Çekildi: {gorsel_url}")

                    # 🌟 İŞTE YENİ SATIR: Resmi buluta yüklüyoruz!
                    gorsel_url = upload_to_cloudinary(gorsel_url)
                    logger.info(f"☁️ Cloudinary Kalıcı URL: {gorsel_url}")
            except Exception as e:
                logger.warning(f"⚠️ Görsel çekilemedi: {e}")

            # --- SİHİR 1: YORUMLAR SEKMESİNE TIKLA (Daha Kararlı) ---
            try:
                # "Yorumlar" veya "Reviews" kelimesini içeren butonu her türlü bul
                # Google bazen <div> bazen <button> kullanıyor.
                reviews_btn = page.locator(
                    '//button[contains(@aria-label, "Yorumlar")] | //button[contains(@aria-label, "Reviews")] | //div[text()="Yorumlar"]')

                if reviews_btn.count() > 0:
                    reviews_btn.first.click(timeout=5000)
                    logger.info("   👉 Yorumlar sekmesine tıklandı.")
                    time.sleep(3)
                else:
                    # Eğer buton bulunamazsa, direkt URL'den dolayı orada olabiliriz
                    logger.warning("   ⚠️ Yorumlar sekmesi butonu bulunamadı, mevcut görünümle devam ediliyor.")
            except Exception:
                pass

            # --- SİHİR 2: NOKTA ATIŞI KAYDIRMA (Akıllı En Uzun Panel Tespiti) ---
            try:
                logger.info("🖱️ Kaydırılabilir ana panel tespit ediliyor...")

                # Sayfadaki tüm yapısal divleri gezip 'scrollHeight' (içerik uzunluğu) en büyük olanı buluyoruz
                scroll_selector = page.evaluate('''() => {
                    const candidates = Array.from(document.querySelectorAll('div.m6QErb, div[role="main"]'));
                    let targetPanel = null;
                    let maxScrollHeight = 0;
                    
                    for (let el of candidates) {
                        const style = getComputedStyle(el);
                        // Elementin kaydırılabilir olup olmadığını veya içeriğinin taşıp taşmadığını kontrol et
                        if (style.overflowY === 'auto' || style.overflowY === 'scroll' || el.scrollHeight > el.clientHeight) {
                            // En fazla içeriğe sahip (en uzun) paneli hedef olarak belirle
                            if (el.scrollHeight > maxScrollHeight) {
                                maxScrollHeight = el.scrollHeight;
                                targetPanel = el;
                            }
                        }
                    }
                    
                    if (targetPanel) {
                        targetPanel.id = "main_scroll_panel";
                        return "#main_scroll_panel";
                    }
                    return null;
                }''')

                if scroll_selector:
                    for i in range(max_kaydirma):
                        page.evaluate(f'''(sel) => {{
                            const el = document.querySelector(sel);
                            if(el) {{
                                // 4000 yerine 1500 piksel ve smooth scrolling ile daha doğal bir hareket
                                el.scrollBy({{top: 1500, behavior: 'smooth'}});
                            }}
                        }}''', scroll_selector)
                        time.sleep(2.5) # Bekleme süresini yarım saniye artırıyoruz
                        logger.info(f"   ⬇️ Panel kaydırıldı ({i + 1}/{max_kaydirma})")
                else:
                    logger.error("❌ Kaydırılabilir panel bulunamadı!")
            except Exception as e:
                logger.warning(f"⚠️ Kaydırma sırasında sorun: {e}")

            # --- SİHİR 3: VERİ TOPLAMA (ÇOKLU SEÇİCİ & YEDEK PLAN) ---
            logger.info("   ⏳ Yorumların sayfaya yüklenmesi bekleniyor...")
            time.sleep(3)  # Scroll bittikten sonra DOM'un kendine gelmesi için net bir bekleme

            ham_yorumlar = page.evaluate(r'''() => {
                let items = [];
                // 1. Taktik: Bilinen en yaygın class'lar
                let blocks = document.querySelectorAll('.jftiEf, .G57Fne, div[data-review-id]');
                
                // Eğer standart class'lar yoksa, 2. Taktik: Role=article veya uzun metin içeren kutular
                if (blocks.length === 0) {
                    // Google bazen yorumları article olarak işaretler
                    blocks = document.querySelectorAll('div[role="article"]');
                }

                blocks.forEach(block => {
                    // İsim bulma (En üstteki kalın yazı genelde isimdir)
                    let nameEl = block.querySelector('.d4r55, .WNxzHc, button[class*="d4r55"]') 
                                 || block.querySelector('div[class*="fontTitleSmall"]'); 
                    let name = nameEl ? nameEl.innerText.trim() : "Bilinmiyor";
                    
                    // Metin bulma (Daha uzun ve geniş text arıyoruz)
                    let textEl = block.querySelector('.wiI7pd, .MyEned') 
                                 || block.querySelector('span[class*="wiI7pd"]');
                                 
                    // Eğer text elementi yoksa, div içindeki en uzun metni almayı dene (Son Çare)
                    let text = "";
                    if (textEl) {
                        text = textEl.innerText.trim();
                    } else {
                        // Kutu içindeki metinleri topla
                        let spans = Array.from(block.querySelectorAll('span'));
                        let longestSpan = spans.sort((a,b) => b.innerText.length - a.innerText.length)[0];
                        if (longestSpan && longestSpan.innerText.length > 20) {
                            text = longestSpan.innerText.trim();
                        }
                    }

                    let date = block.querySelector('.rsqaWe')?.innerText.trim() || "Bilinmiyor";
                    
                    // Puanı aria-label'dan veya yıldız simgelerinden yakala
                    let finalPuan = "0";
                    
                    // 1. Deneme: Orijinal aria-label yaklaşımı (Genişletilmiş)
                    let ratingEl = block.querySelector('[aria-label*="yıldız"], [aria-label*="star"], span[role="img"]');
                    if (ratingEl) {
                        let ratingStr = ratingEl.getAttribute('aria-label') || "";
                        let match = ratingStr.match(/([0-5](?:[.,][0-9])?)/);
                        if (match) {
                            finalPuan = match[1].replace(',', '.');
                        }
                    }

                    // 2. Deneme: Eğer 1. deneme başarısızsa (hala "0" ise), CSS sınıfından bul (En yaygın yöntem)
                    if (finalPuan === "0" || finalPuan === "0.0") {
                        // Google genelde puanı "kvMYJc" veya benzeri bir span içinde yıldız ikonuyla verir.
                        // Yanındaki görünmez span içinde bazen "5,0" yazar.
                        let stars = block.querySelectorAll('.kvMYJc, img[src*="star"]');
                        if (stars.length > 0) {
                            // Yıldız sayısına göre puan ver
                            finalPuan = stars.length > 5 ? "5.0" : stars.length.toString() + ".0"; 
                        } else {
                           // Son çare: Metin olarak yıldız oranını arama (Örn: "5/5")
                           let allText = block.innerText;
                           let matchText = allText.match(/([1-5])(?:[.,][0-9])?\s*(?:\/|yıldız|star)/i);
                           if(matchText){
                               finalPuan = matchText[1];
                           }
                        }
                    }

                    if(text.length > 5) {
                        items.push({
                            isim: name,
                            tarih: date,
                            puan: finalPuan,
                            orijinal_metin: text
                        });
                    }
                });
                return items;
            }''')

            logger.info(f"   ✅ Sayfadan {len(ham_yorumlar)} adet ham yorum çekildi.")

            # Python Tarafında Temizlik ve Kayıt
            for yrm in ham_yorumlar:
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI: break

                temiz_metin = preprocessor.clean_text(yrm["orijinal_metin"], "maps")
                if kaliteli_yorum_mu(temiz_metin, gorulen_yorumlar):
                    gorulen_yorumlar.add(temiz_metin)
                    yrm["temiz_metin"] = temiz_metin
                    tum_yorumlar.append(yrm)

            context.close()
    except Exception as e:
        logger.error(f"❌ Scraper Hatası: {e}")

    # Dosya Kayıt İşlemleri...
    if tum_yorumlar:
        veri_seti = {
            "platform": "maps",
            "baslik": urun_adi,
            "link": mekan_linki,
            "ham_kategori": ham_kategori,
            "kategori": mekan_kategorisi,
            "gorsel_url": gorsel_url,
            "yorumlar": tum_yorumlar
        }

        # Hedef klasör (Yukarıda tanımladığımız hedef_klasor mutlak yolunu kullanıyoruz)
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            import json
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)

        logger.info(f"🎉 Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
        return dosya_yolu
    else:
        logger.warning(f"⚠️ {urun_adi} için DOM'dan yorum çekilemedi!")
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
            dosya_yolu = etstur_veri_cek(url, max_sayfa=40)
            return "Etstur verileri başarıyla çekildi.", dosya_yolu

        elif platform == "airbnb":
            dosya_yolu = airbnb_veri_cek(url, max_sayfa=max_sayfa)
            return "Airbnb verileri başarıyla çekildi.", dosya_yolu

        elif platform == "maps":
            dosya_yolu = google_maps_veri_cek(url, max_kaydirma=max_kaydirma)
            if dosya_yolu:  # Dosya yolu varsa başarı döndür
                return "Google Maps verileri başarıyla çekildi.", dosya_yolu
            else:  # Dosya yolu None ise hata döndür
                return "Google Maps üzerinde yorum bulunamadı veya çekilemedi.", None

        else:
            return f"❌ Bilinmeyen veya desteklenmeyen platform: '{platform}'", None

    except Exception as e:
        return f"❌ Kazıma işlemi sırasında kritik bir hata oluştu: {str(e)}", None
