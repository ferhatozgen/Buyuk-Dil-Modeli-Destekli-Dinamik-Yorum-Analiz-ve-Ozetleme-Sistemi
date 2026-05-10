import random
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

logger = setup_logger()


def kategori_verilerini_yukle(dosya_yolu="maps_ham_kategoriler.json"):
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["ana_kategori_haritasi"], data["varsayilan_kategori"]
    except Exception as e:
        print(f"⚠️ Kategori haritası yüklenemedi: {e}")
        return {}, "Diğer"


# Sadece 1 kere çalışır ve hafızada tutar
KATEGORI_HARITASI, VARSAYILAN_KATEGORI = kategori_verilerini_yukle()


def kategoriyi_eslestir(ham_kategori, urun_adi):
    # 1. Hazırlık ve Temizlik (Orijinal karakter temizleme mantığın)
    ham_kategori_temiz = str(ham_kategori).lower().replace('i̇', 'i').replace('ı', 'i').replace('I', 'ı')
    urun_adi_temiz = str(urun_adi).lower().replace('i̇', 'i').replace('ı', 'i').replace('I', 'ı')

    # 2. STRATEJİK ÖNCELİK: Ürün Adında bariz bir kategori var mı?
    # Eğer ürün adında "Hotel" geçiyorsa, Google ne derse desin bu bir OTEL'dir.
    otel_sinyalleri = ["hotel", "otel", "resort", "pansiyon", "apart", "hostel", "konaklama"]
    if any(kelime in urun_adi_temiz for kelime in otel_sinyalleri):
        return "otel"
    otel_kalip = r".*\d+\s*yildizli\s*otel.*|.*otel.*|.*hotel.*|.*resort.*"

    # Hem kategoride hem de ürün adında bu kalıpları arayalım
    if re.match(otel_kalip, ham_kategori_temiz) or re.match(otel_kalip, urun_adi_temiz):
        return "otel"

    # Eğer ürün adında "Restaurant" geçiyorsa ve yukarıdaki otel kontrolüne takılmadıysa yemektir.
    yemek_sinyalleri = ["restoran", "restaurant", "cafe", "kafe", "lokanta", "kebap", "burger"]
    if any(kelime in urun_adi_temiz for kelime in yemek_sinyalleri):
        return "yemek"

    # 3. İSTİSNA KONTROLÜ: Google UI metinlerini (Fotoğrafları göster vb.) devre dışı bırak
    # Eğer ham_kategori sadece bir buton metniyse, eşleştirmede hata yapmaması için temizliyoruz.
    if "fotoğrafları göster" in ham_kategori_temiz or "tümünü gör" in ham_kategori_temiz:
        ham_kategori_temiz = "" # Sadece ürün adına odaklanılması için kategoriyi boşaltıyoruz

    # 4. GENEL ARAMA (Orijinal Mantığın): Kategori Haritası üzerinden döngü
    # Not: Eğer ham_kategori yukarıda temizlendiyse sadece ürün adına bakacak.
    aranacak_metin = f"{ham_kategori_temiz} {urun_adi_temiz}"

    for ana_kategori, kelimeler in KATEGORI_HARITASI.items():
        for kelime in kelimeler:
            # Kelimenin tam eşleşmesi veya içinde geçmesi (Orijinal mantığın)
            if kelime in aranacak_metin:
                # Küçük bir güvenlik: "fotoğraf" kelimesi hala gelirse ama "göster" ile gelmişse atla
                if kelime == "fotoğraf" and "göster" in ham_kategori_temiz:
                    continue
                return ana_kategori

    return VARSAYILAN_KATEGORI


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
        return False  # Dil anlaşılamayacak kadar bozuksa direkt ele

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
            except Exception:
                pass
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
        match = re.search(r'<meta\s+(?:property|name)=["\']og:image["\']\s+content=["\']([^"\']+)["\']', res.text,
                          re.IGNORECASE)
        return match.group(1) if match else "Görsel Bulunamadı"
    except:
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
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict) and "comment" in \
            json_verisi[0]:
        return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = trendyol_yorum_bul(deger)
            if sonuc: return sonuc
    return []


def hb_yorum_bul(json_verisi):
    if isinstance(json_verisi, list) and len(json_verisi) > 0 and isinstance(json_verisi[0], dict):
        if "review" in json_verisi[0] or "star" in json_verisi[0] or "customerName" in json_verisi[
            0]: return json_verisi
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
        except:
            pass


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
        if "text" in json_verisi[0] or "comment" in json_verisi[0] or "reviewText" in json_verisi[0] or "customer" in \
                json_verisi[0]:
            return json_verisi
    elif isinstance(json_verisi, dict):
        for _, deger in json_verisi.items():
            sonuc = etstur_yorum_bul(deger)
            if sonuc: return sonuc
    return []


def airbnb_yorum_bul(json_verisi):
    try:
        reviews_data = json_verisi.get("data", {}).get("presentation", {}).get("stayProductDetailPage", {}).get(
            "reviews", {}).get("reviews", [])
        if reviews_data: return reviews_data
    except Exception:
        pass
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

    # --- GÜNCELLENEN KISIM: Kategori Çekme (Trendyol - Akıllı Temizleme) ---
    kategori_agaci = []
    try:
        html_res = curl_requests.get(urun_linki, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(html_res.text, 'html.parser')

        kategori_etiketleri = soup.find_all('li', class_='product-detail-breadcrumbs-item')
        kategoriler = []

        # Ekstra temizlik için marka ve ürün ismini html içinden bulmayı deneriz, bulamazsak da en son elemanı (ürün adı) sileriz.
        urun_adi_html_icinde = ""
        try:
            # Trendyolda genellikle <h1> etiketi ürün adıdır.
            urun_baslik = soup.find('h1')
            if urun_baslik:
                # span'ler içinde marka ve ürün adı olabilir. Sadece metinleri alalım.
                urun_adi_html_icinde = urun_baslik.text.strip().lower()
        except:
            pass

        for li in kategori_etiketleri:
            isim = li.text.strip()
            # 1. 'Trendyol' u atlıyoruz.
            if isim and isim != "Trendyol":
                # 2. Eğer bu breadcrumb öğesi, ürünün isminin (ya da uzun marka+ürün birleşiminin) kendisiyse atla.
                # E-ticaret siteleri breadcrumbın en sonuna genelde ürünün kendisini koyar.
                if urun_adi_html_icinde and isim.lower() in urun_adi_html_icinde and len(isim) > 20:
                    continue

                # 3. Listeye ekle (daha önce eklenmediyse)
                if isim not in kategoriler:
                    kategoriler.append(isim)

        # Ekstra Filtre: E-ticaret siteleri breadcrumb'ın en sonuna genelde ürünün adını koyar.
        # Liste boş değilse ve son elemanın uzunluğu çok fazlaysa (kategori isimleri genelde kısadır, örn. "Sneaker", ürün isimleri uzundur),
        # büyük ihtimalle ürün ismini almıştır. Onu listeden çıkaralım.
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
                if len(tum_yorumlar) >= MAX_YORUM_SINIRI:
                    break

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
        # JSON SETİNE 'kategori' EKLENDİ
        veri_seti = {
            "platform": "trendyol",
            "baslik": urun_adi,
            "kategori": kategori_agaci,  # YENİ ALAN
            "link": urun_linki,
            "gorsel_url": gorsel_url,
            "yorumlar": tum_yorumlar
        }

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
    gorsel_url = "Görsel Bulunamadı"  # Başlangıçta boş

    # --- SADECE BU KISIM GÜNCELLENDİ: Kategori Çekme (Hepsiburada - Gelişmiş Hibrit Çözüm) ---
    kategori_agaci = []  # Boş liste ile başlatıyoruz
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
                    kategoriler = [el.get('name') for el in breadcrumbs_list if
                                   el.get('name') and el.get('name') != "Anasayfa"]
                    if 0 < len(kategoriler) <= 10:
                        kategori_agaci = kategoriler  # LİSTE OLARAK ATANDI

                if not kategori_agaci:  # Liste boşsa diğerine bak
                    bcs_list = json_icinde_ara(data, 'breadcrumbs')
                    if bcs_list and isinstance(bcs_list, list):
                        kategoriler = [b.get('name') for b in bcs_list if isinstance(b, dict) and b.get('name')]
                        if kategoriler and 0 < len(kategoriler) <= 10:
                            kategori_agaci = kategoriler  # LİSTE OLARAK ATANDI

                if not kategori_agaci:
                    category_str = json_icinde_ara(data, 'category')
                    if isinstance(category_str, str) and " > " in category_str:
                        # EĞER METİNSE PARÇALAYIP LİSTEYE ÇEVİRİYORUZ
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
                                    kategori_agaci = kategoriler  # LİSTE OLARAK ATANDI
                                    break

                            elif isinstance(obj, dict) and obj.get('@type') == 'Product' and obj.get('category'):
                                cat_str = obj.get('category')
                                if " > " in cat_str:
                                    kategori_agaci = cat_str.split(" > ")  # METNİ LİSTEYE ÇEVİR
                                    break

                        if kategori_agaci:  # Liste artık boş değilse çık
                            break
                    except Exception:
                        continue

        logger.info(f"📁 Kategori Bulundu: {kategori_agaci}")

    except Exception as e:
        logger.warning(f"⚠️ Hepsiburada Kategori çekilemedi: {e}")
    # -----------------------------------------------------

    # --- ALT KISIM TAMAMEN SENİN ORİJİNAL KODUNDUR, HİÇBİR ŞEY DEĞİŞMEDİ ---
    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set()  # Tekrar kontrolü için hafıza
    MAX_YORUM_SINIRI = 200  # Limitimiz
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
            "kategori": kategori_agaci,  # YENİ ALAN
            "link": urun_linki,
            "gorsel_url": gorsel_url,
            "yorumlar": tum_yorumlar
        }

        hedef_klasor = "cekilen_veriler/hepsiburada"
        os.makedirs(hedef_klasor, exist_ok=True)

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(veri_seti, f, ensure_ascii=False, indent=4)
        logger.info(f"Kaydedildi: {dosya_yolu} ({len(tum_yorumlar)} yorum)")
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

    # Dosya yolu yapılandırması
    hedef_klasor = "cekilen_veriler/ciceksepeti"
    os.makedirs(hedef_klasor, exist_ok=True)
    dosya_yolu = os.path.join(hedef_klasor, f"ciceksepeti_{urun_kodu}.json")

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
    if not match: return
    app_id = match.group(1)
    isim_match = re.search(r'/app/\d+/([^/?]+)', oyun_linki)
    urun_adi = isim_match.group(1).replace('_', ' ').title() if isim_match else "Steam Oyunu"

    dosya_yolu = f"cekilen_veriler/steam/steam_{app_id}.json"

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

    session = curl_requests.Session(impersonate="chrome124")
    try:
        html_res = session.get(otel_linki, timeout=15, verify=False)
        if html_res.status_code != 200: return

        hotel_id_match = re.search(r'data-hotel-id=["\']([^"\']+)["\']', html_res.text) or re.search(
            r'"hotelId"\s*:\s*["\']([^"\']+)["\']', html_res.text)
        hotel_code_match = re.search(r'data-vendor-code=["\']([^"\']+)["\']', html_res.text) or re.search(
            r'"vndCode"\s*:\s*["\']([^"\']+)["\']', html_res.text)
        if not hotel_code_match or not hotel_id_match: return
        hotel_code = hotel_code_match.group(1)
        hotel_id = hotel_id_match.group(1)
    except Exception:
        return

    isim_match = re.search(r'etstur\.com/([^/?]+)', otel_linki)
    urun_adi = isim_match.group(1).replace('-', ' ').title() if isim_match else "Etstur Oteli"

    dosya_yolu = f"cekilen_veriler/etstur/etstur_{hotel_code}.json"

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
    if not match: return None
    oda_id = match.group(1)

    dosya_yolu = f"cekilen_veriler/airbnb/airbnb_{oda_id}.json"

    logger.info(f" 🔍 Airbnb ID Çözümleniyor: {oda_id}")
    gorsel_url = "Görsel Bulunamadı"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
               "Accept-Language": "tr-TR,tr;q=0.9"}
    try:
        from curl_cffi import requests as curl_requests

        # --- YENİ EKLENEN KISIM: ZAMAN AŞIMI VE TEKRAR DENEME MEKANİZMASI ---
        max_deneme = 3
        html_res = None
        for deneme in range(max_deneme):
            try:
                # Timeout süresini 15'ten 30'a çıkardık
                html_res = curl_requests.get(oda_linki, headers=headers, impersonate="chrome124", timeout=30,
                                             verify=False)
                break  # Başarılı olursa döngüyü kır ve devam et
            except Exception as e:
                if deneme < max_deneme - 1:
                    logger.warning(
                        f"⚠️ Airbnb sayfası yanıt vermedi (Zaman Aşımı). Tekrar deneniyor ({deneme + 1}/{max_deneme})...")
                    time.sleep(3)  # 3 saniye bekle ve tekrar dene
                else:
                    raise e  # 3 denemede de başarısız olursa asıl hatayı fırlat

        temiz_html = html_res.text.replace('\\u002F', '/')
        # -------------------------------------------------------------------

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

        # API KEY'i dinamik bulma
        api_key_match = re.search(r'"api_config"\s*:\s*{[^}]*"key"\s*:\s*"([^"]+)"', temiz_html)
        if not api_key_match:
            api_key_match = re.search(r'("key"|"apiKey")\s*:\s*"([^"]+)"', temiz_html)

        if api_key_match:
            api_key = api_key_match.group(2) if len(api_key_match.groups()) > 1 else api_key_match.group(1)
        else:
            logger.error(f"❌ Airbnb API Key Bulunamadı: {oda_id}")
            return None

        # sha256Hash Değerini Dinamik Bulma (Yedekli)
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

        limit = 24  # Airbnb'nin teşhis dosyasında gördüğümüz sınırı
        offset = sayfa * limit

        # --- YENİ EKLENEN KISIM: 'first' PARAMETRESİ ---
        variables = {
            "id": base64_id,
            "pdpReviewsRequest": {
                "fieldSelector": "for_p3_translation_only",
                "forPreview": False,
                "limit": limit,
                "first": limit,  # Eksik olan ve API'yi bozan kritik değer
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
            from curl_cffi import requests as curl_requests
            response = curl_requests.get(full_url, headers=api_headers, impersonate="chrome124", timeout=15,
                                         verify=False)

            if response.status_code != 200:
                logger.error(f"❌ Airbnb API Hatası (Kod: {response.status_code})")
                break

            data = response.json()
            # --- TEŞHİS İÇİN EKLENDİ (GERÇEK HATAYI GÖRECEĞİZ) ---
            if "errors" in data:
                logger.error(f"⚠️ Airbnb API İçi Hata: {data['errors']}")

            yorum_listesi = airbnb_yorum_bul(data)

            if not yorum_listesi:
                # Airbnb bize yorum listesi yerine ne gönderdi, ekranda görelim!
                logger.warning(f"⚠️ API'den yorum gelmedi. Gelen ham veri: {str(data)[:500]}")
                break
            # ---------------------------------------------------
            yorum_listesi = airbnb_yorum_bul(data)

            # Eğer sayfa boş gelirse API verileri bitirmiş demektir
            if not yorum_listesi:
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
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
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

                kapat_btn = page.locator(
                    'button:has-text("Kabul Et"), button:has-text("Anladım"), button:has-text("Kapat")')
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
    gorulen_yorumlar = set()  # Tekrar kontrolü
    MAX_YORUM_SINIRI = 200  # Hedef limit
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
            res = curl_requests.get(api_url, headers=headers, impersonate="chrome124", timeout=15, verify=False)
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
        except Exception:
            break

    # ==========================================
    # SİHİR 3: BİRLEŞTİR VE KAYDET
    # ==========================================
    if tum_yorumlar:
        veri_seti = {"platform": "yemeksepeti", "baslik": urun_adi, "link": restoran_linki, "gorsel_url": gorsel_url,
                     "yorumlar": tum_yorumlar}

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
    headers_main = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}

    try:
        html_res = curl_requests.get(restoran_linki, headers=headers_main, impersonate="chrome124", timeout=10,
                                     verify=False)
        isim_match = re.search(r'<title>([^<]+)</title>', html_res.text, re.IGNORECASE)
        if isim_match:
            urun_adi = isim_match.group(1).split('|')[0].replace('Sipariş', '').strip()
        else:
            urun_adi = "Trendyol Go Restoranı"

        cdn_match = re.search(r'(https://cdn\.tgoapps\.com/[^"\']+\.(?:jpeg|jpg|png|webp))', html_res.text,
                              re.IGNORECASE)
        if cdn_match:
            gorsel_url = cdn_match.group(1)
            logger.info(f"🖼️ Trendyol Go Görseli CDN'den Bulundu: {gorsel_url}")
    except Exception:
        urun_adi = "Trendyol Go Restoranı"

    preprocessor = ReviewPreprocessor()
    tum_yorumlar = []
    gorulen_yorumlar = set()  # Tekrar kontrolü
    MAX_YORUM_SINIRI = 200  # Hedef limit
    headers = {"Accept": "application/json", "Origin": "https://www.trendyol.com", "Referer": restoran_linki}

    for sayfa in range(1, max_sayfa + 1):
        # DIŞ KONTROL
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
        except Exception:
            break

    if tum_yorumlar:
        veri_seti = {"platform": "trendyol-go", "baslik": urun_adi, "link": restoran_linki, "gorsel_url": gorsel_url,
                     "yorumlar": tum_yorumlar}

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
        profil_klasoru = os.path.join(os.getcwd(), "saved_maps_profile")
        os.makedirs(profil_klasoru, exist_ok=True)

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=profil_klasoru,
                headless=False,  # Hata ayıklama bitene kadar False kalsın
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                ignore_default_args=["--enable-automation"],
                args=["--disable-blink-features=AutomationControlled"]
            )

            page = context.pages[0] if context.pages else context.new_page()
            page.goto(mekan_linki, timeout=60000)

            # --- SİHİR 0: Çerezleri Hızlıca Geç ---
            try:
                page.click('button:has-text("Tümünü kabul et"), button:has-text("Accept all")', timeout=3000)
            except:
                pass

            # --- KATEGORİ ÇEKME (Yeni ve Sağlam Yöntem) ---
            try:
                # Doğrudan kategori aksiyonuna sahip elementi hedef alıyoruz
                ham_kategori = page.locator('[jsaction*="pane.rating.category"]').first.inner_text(timeout=3000)
                logger.info(f"📌 Maps'ten ham kategori çekildi: '{ham_kategori}'")
            except:
                # Yedek: Eğer yukarıdaki bulunamazsa butonu değil, yanındaki text'i al
                ham_kategori = "Belirlenemedi"

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

            # --- SİHİR 2: NOKTA ATIŞI KAYDIRMA (Yeni Mantık) ---
            try:
                # Class ismi yerine, scroll özelliği olan div'i JS ile dinamik buluyoruz
                logger.info("🖱️ Kaydırılabilir panel tespit ediliyor...")

                # Bu JS kodu, sayfadaki en büyük kaydırılabilir alanı (scrollable area) bulur
                scroll_selector = page.evaluate('''() => {
                    const div = Array.from(document.querySelectorAll('div[role="main"] div, div.m6QErb'))
                                      .find(el => getComputedStyle(el).overflowY === 'auto' || getComputedStyle(el).overflowY === 'scroll');
                    if (div) {
                        div.id = "scroll_target_div"; // Kolay yakalamak için ID atıyoruz
                        return "#scroll_target_div";
                    }
                    return null;
                }''')

                if scroll_selector:
                    for i in range(max_kaydirma):
                        page.evaluate(f'''(sel) => {{
                            const el = document.querySelector(sel);
                            if(el) {{
                                el.scrollBy(0, 4000);
                            }}
                        }}''', scroll_selector)
                        time.sleep(2)
                        # Sayfayı "aktif" tutmak için mouse tekerleği simülasyonu
                        page.mouse.wheel(0, 1000)
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
def linkten_veri_cek(url, platform, max_sayfa=15, max_kaydirma=25):
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
