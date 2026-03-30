from datetime import datetime
from uuid import uuid4
import hashlib
import os
import json

def process_airbnb_data(raw_json: dict) -> tuple[dict, list[dict]]:
    bizim_urun_id = str(uuid4())
    orj_link = raw_json.get("link")
    if orj_link:
        link_hash = hashlib.sha256(orj_link.encode("utf-8")).hexdigest()
    else:
        link_hash = None

    ham_yorumlar = raw_json.get("yorumlar", [])

    gecerli_puanlar = [y.get("rating") for y in ham_yorumlar if y.get("rating") is not None]
    hesaplanan_orj_puan = sum(gecerli_puanlar) / len(gecerli_puanlar) if gecerli_puanlar else None

    urun_paket = {
        "id": bizim_urun_id,
        "platform":raw_json.get("platform","airbnb"),
        "urun_adi":raw_json.get("baslik"),
        "urun_url_orj":orj_link,
        "urun_url_hash": link_hash, # Gerçek url de hashlib kullanacağız #
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": round(hesaplanan_orj_puan, 1) if hesaplanan_orj_puan else None,
        "kategori":None,
        "hesaplanan_puan":None,
        "guncel_ozet":None,
        "ozet_embedding":None,
        "click_count":0,
        "created_at":datetime.now(),
        "updated_at":datetime.now(),
        "like_rate":None
    }

    yorumlar_paket = []

    for raw_review in ham_yorumlar:

        metadata = {
            "verilen_puan":raw_review.get("rating"),
            "misafir_ulkesi": raw_review.get("localizedReviewerLocation"),
            "konaklama_tipi": raw_review.get("reviewHighlight"),
        }

        tekil_yorum = {
            "id": str(uuid4()),
            "urun_id": bizim_urun_id,
            "yorum_metni":raw_review.get("temiz_metin"),
            "metadata":metadata,
            "dinamik_kategori_parcalari":None,
            "created_at":datetime.now(),
            "embedding":None,
        }
        yorumlar_paket.append(tekil_yorum)

    return urun_paket,yorumlar_paket

def process_ciceksepeti_data(raw_json:dict) -> tuple[dict, list[dict]]:
    bizim_urun_id = str(uuid4())
    orj_link = raw_json.get("link")
    if orj_link:
        link_hash = hashlib.sha256(orj_link.encode("utf-8")).hexdigest()
    else:
        link_hash = None

    ham_yorumlar = raw_json.get("yorumlar", [])

    gecerli_puanlar = [int(y.get("rating")[0])
                       for y in ham_yorumlar
                       if y.get("rating") and y.get("rating")[0].isdigit()
                       ]
    hesaplanan_orj_puan = sum(gecerli_puanlar) / len(gecerli_puanlar) if gecerli_puanlar else None

    urun_paket = {
        "id": bizim_urun_id,
        "platform": raw_json.get("platform", "ciceksepeti"),
        "urun_adi": raw_json.get("baslik"),
        "urun_url_orj": orj_link,
        "urun_url_hash":link_hash,
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": round(hesaplanan_orj_puan, 1) if hesaplanan_orj_puan else None,
        "kategori": None,
        "hesaplanan_orj_puan": None,
        "guncel_ozet": None,
        "ozet_embedding": None,
        "click_count": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "like_rate": None
    }

    yorumlar_paket = []

    for raw_review in ham_yorumlar:
        tekil_yorum = {
            "id": str(uuid4()),
            "urun_id": bizim_urun_id,
            "yorum_metni":raw_review.get("temiz_metin"),
            "metadata":None,
            "created_at":datetime.now(),
            "dinamik_kategori_parcalari":None,
            "embedding":None,
        }
        yorumlar_paket.append(tekil_yorum)

    return urun_paket,yorumlar_paket

def process_etstur_data(raw_json: dict) -> tuple[dict, list[dict]]:
    bizim_urun_id = str(uuid4())
    orj_link = raw_json.get("link")
    if orj_link:
        link_hash = hashlib.sha256(orj_link.encode("utf-8")).hexdigest()
    else:
        link_hash = None

    ham_yorumlar = raw_json.get("yorumlar", [])

    gecerli_puanlar = [
        round((float(y.get("score")) / 20) * 2) / 2
        for y in ham_yorumlar
        if isinstance(y.get("score"), (int, float))
    ]


    if gecerli_puanlar:
        ham_ortalama = sum(gecerli_puanlar) / len(gecerli_puanlar)
        hesaplanan_orj_puan = round(ham_ortalama * 2) / 2
    else:
        hesaplanan_orj_puan = None

    urun_paket = {
        "id": bizim_urun_id,
        "platform": raw_json.get("platform", "etstur"),
        "urun_adi": raw_json.get("baslik"),
        "urun_url_orj": orj_link,
        "urun_url_hash":link_hash,
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": round(hesaplanan_orj_puan, 1) if hesaplanan_orj_puan else None,
        "kategori": None,
        "hesaplanan_orj_puan": None,
        "guncel_ozet": None,
        "ozet_embedding": None,
        "click_count": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "like_rate": None
    }

    yorumlar_paket = []

    for raw_review in ham_yorumlar:

        orijinal_score = raw_review.get("score")
        normalizce_ana_puan = float(orijinal_score) / 20 if isinstance(orijinal_score, (int,float)) else None

        alt_puanlar_listesi = raw_review.get("ratingTypes") or []
        alt_kategori_puanlari = {
            item.get("name"): (float(item.get("score")) / 2 if isinstance(item.get("score"), (int, float)) else None)
            for item in alt_puanlar_listesi
        }

        metadata = {
            "verilen_puan":normalizce_ana_puan,
            "is_recommened":raw_review.get("recommendation"),
            "guest_type":raw_review.get("guestType"),
            "oda_tipi":raw_review.get("roomName"),
            "alt_kategori_puanlari":alt_kategori_puanlari
        }

        tekil_yorum = {
            "id": str(uuid4()),
            "urun_id": bizim_urun_id,
            "yorum_metni": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "created_at": datetime.now(),
            "dinamik_kategori_parcalari": None,
            "embedding": None,
        }
        yorumlar_paket.append(tekil_yorum)

    return urun_paket, yorumlar_paket

def process_hepsiburada_data(raw_json: dict) -> tuple[dict, list[dict]]:
    bizim_urun_id = str(uuid4())
    orijinal_link = raw_json.get("link")
    link_hash = hashlib.sha256(orijinal_link.encode('utf-8')).hexdigest() if orijinal_link else None

    ham_yorumlar = raw_json.get("yorumlar", [])

    gecerli_puanlar = [
        y.get("star")
        for y in ham_yorumlar
        if isinstance(y.get("star"), (int, float))
    ]

    hesaplanan_orj_puan = sum(gecerli_puanlar) / len(gecerli_puanlar) if gecerli_puanlar else None

    urun_paket = {
        "id": bizim_urun_id,
        "platform": raw_json.get("platform", "hepsiburada"),
        "urun_adi": raw_json.get("baslik"),
        "urun_url_orj": orijinal_link,
        "urun_url_hash": link_hash,
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": hesaplanan_orj_puan,
        "kategori": None,
        "hesaplanan_puan": None,
        "guncel_ozet": None,
        "ozet_embedding": None,
        "click_count": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "like_rate": None
    }

    yorumlar_paket = []

    for raw_review in ham_yorumlar:
        order_info = raw_review.get("order") or {}
        reaction_info = raw_review.get("reactions") or {}
        media_list = raw_review.get("media") or []

        metadata = {
            "satici_adi":order_info.get("merchantName"),
            "dogrulanmis_satin_alim":raw_review.get("isPurchaseVerified"),
            "beden_kalibi":raw_review.get("mould"),
            "faydali_bulma_sayisi":reaction_info.get("clap", 0),
        }

        tekil_yorum = {
            "id": str(uuid4()),
            "urun_id": bizim_urun_id,
            "yorum_metni": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "dinamik_kategori_parcalari": None,
            "created_at": datetime.now(),
            "embedding": None,
        }
        yorumlar_paket.append(tekil_yorum)

    return urun_paket, yorumlar_paket

def process_maps_data(raw_json: dict) -> tuple[dict, list[dict]]:
    bizim_urun_id = str(uuid4())

    orijinal_link = raw_json.get("link")
    link_hash = hashlib.sha256(orijinal_link.encode('utf-8')).hexdigest() if orijinal_link else None

    ham_yorumlar = raw_json.get("yorumlar", [])

    gecerli_puanlar = [int(y.get("puan", "")[0])
                       for y in ham_yorumlar
                       if y.get("puan") and y.get("puan")[0].isdigit()
                       ]

    hesaplanan_orj_puan = (sum(gecerli_puanlar) / len(gecerli_puanlar)) if gecerli_puanlar else None

    urun_paket = {
        "id": bizim_urun_id,
        "platform": raw_json.get("platform", "maps"),
        "urun_adi": raw_json.get("baslik"),
        "urun_url_orj": orijinal_link,
        "urun_url_hash": link_hash,
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": hesaplanan_orj_puan,
        "kategori": None,
        "hesaplanan_puan": None,
        "guncel_ozet": None,
        "ozet_embedding": None,
        "click_count": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "like_rate": None
    }

    yorumlar_paket = []

    for raw_review in ham_yorumlar:

        tekil_yorum = {
            "id": str(uuid4()),
            "urun_id": bizim_urun_id,
            "yorum_metni": raw_review.get("temiz_metin"),
            "metadata": None,
            "dinamik_kategori_parcalari": None,
            "created_at": datetime.now(),
            "embedding": None,
        }
        yorumlar_paket.append(tekil_yorum)

    return urun_paket, yorumlar_paket

def process_steam_data(raw_json: dict) -> tuple[dict, list[dict]]:
    bizim_urun_id = str(uuid4())

    orijinal_link = raw_json.get("link")
    link_hash = hashlib.sha256(orijinal_link.encode('utf-8')).hexdigest() if orijinal_link else None

    ham_yorumlar = raw_json.get("yorumlar", [])

    if ham_yorumlar:
        olumlu_sayisi = sum(1 for y in ham_yorumlar if y.get("voted_up") is True)
        oran = olumlu_sayisi / len(ham_yorumlar)
        hesaplanan_orj_puan = round((oran * 5) * 2) / 2
    else:
        hesaplanan_orj_puan = None

    urun_paket = {
        "id": bizim_urun_id,
        "platform": raw_json.get("platform", "steam"),
        "urun_adi": raw_json.get("baslik"),
        "urun_url_orj": orijinal_link,
        "urun_url_hash": link_hash,
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": hesaplanan_orj_puan,
        "kategori": None,
        "hesaplanan_puan": None,
        "guncel_ozet": None,
        "ozet_embedding": None,
        "click_count": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "like_rate": None
    }

    yorumlar_paket = []

    for raw_review in ham_yorumlar:
        author_info = raw_review.get("author") or {}

        metadata = {
            "oynanma_suresi_dakika": author_info.get("playtime_forever"),
        }
        tekil_yorum = {
            "id": str(uuid4()),
            "urun_id": bizim_urun_id,
            "yorum_metni": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "dinamik_kategori_parcalari": None,
            "created_at": datetime.now(),
            "embedding": None,
        }
        yorumlar_paket.append(tekil_yorum)

    return urun_paket, yorumlar_paket

def process_trendyol_data(raw_json:dict) -> tuple[dict, list[dict]]:
    bizim_urun_id = str(uuid4())

    orijinal_link = raw_json.get("link")
    link_hash = hashlib.sha256(orijinal_link.encode('utf-8')).hexdigest() if orijinal_link else None

    ham_yorumlar = raw_json.get("yorumlar", [])

    gecerli_puanlar = [
        y.get("rate")
        for y in ham_yorumlar
        if isinstance(y.get("rate"), (int, float))
    ]

    hesaplanan_orj_puan = sum(gecerli_puanlar) / len(gecerli_puanlar)

    urun_paket = {
        "id": bizim_urun_id,
        "platform": raw_json.get("platform", "trendyol"),
        "urun_adi": raw_json.get("baslik"),
        "urun_url_orj": orijinal_link,
        "urun_url_hash": link_hash,
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": hesaplanan_orj_puan,
        "kategori": None,
        "hesaplanan_puan": None,
        "guncel_ozet": None,
        "ozet_embedding": None,
        "click_count": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "like_rate": None
    }

    yorumlar_paket = []

    for raw_review in ham_yorumlar:
        satici_bilgisi = raw_review.get("seller") or {}
        medya_dosyasi = raw_review.get("mediaFiles") or []

        metadata = {
            "satici_adi": raw_review.get("name"),
            "dogrulanmis_alim_mi": raw_review.get("trusted"),
            "faydali_bulan_sayisi": raw_review.get("likesCount"),
        }

        tekil_yorum = {
            "id": str(uuid4()),
            "urun_id": bizim_urun_id,
            "yorum_metni": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "dinamik_kategori_parcalari": None,
            "created_at": datetime.now(),
            "embedding": None,
        }
        yorumlar_paket.append(tekil_yorum)

    return urun_paket, yorumlar_paket

def process_tygo_data(raw_json:dict) -> tuple[dict, list[dict]]:
    bizim_urun_id = str(uuid4())

    orijinal_link = raw_json.get("link")
    link_hash = hashlib.sha256(orijinal_link.encode('utf-8')).hexdigest() if orijinal_link else None

    ham_yorumlar = raw_json.get("yorumlar", [])

    tum_yorum_puanlari = []

    for y in ham_yorumlar:
        score_dict = y.get("score") or {}
        puanlar = [v for k, v in score_dict.items() if isinstance(v, (int, float))]
        if puanlar:
            yorum_ort = sum(puanlar) / len(puanlar)
            tum_yorum_puanlari.append(yorum_ort)

    hesaplanan_orj_puan = sum(tum_yorum_puanlari) / len(tum_yorum_puanlari)if tum_yorum_puanlari else None

    urun_paket = {
        "id": bizim_urun_id,
        "platform": raw_json.get("platform", "trendyol-go"),
        "urun_adi": raw_json.get("baslik"),
        "urun_url_orj": orijinal_link,
        "urun_url_hash": link_hash,
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": hesaplanan_orj_puan,
        "kategori": None,
        "hesaplanan_puan": None,
        "guncel_ozet": None,
        "ozet_embedding": None,
        "click_count": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "like_rate": None
    }

    yorumlar_paket = []

    for raw_review in ham_yorumlar:
        order_items = raw_review.get("orderItems") or []

        alinan_urunler = [item.get("name") for item in order_items if item.get("name")]

        metadata = {
            "siparis_edilen_urunler": alinan_urunler,
            "teslimat_tipi": raw_review.get("deliveryType")
        }

        tekil_yorum = {
            "id": str(uuid4()),
            "urun_id": bizim_urun_id,
            "yorum_metni": raw_review.get("temiz_metin"),
            "metadata": metadata,
            "dinamik_kategori_parcalari": None,
            "created_at": datetime.now(),
            "embedding": None,
        }
        yorumlar_paket.append(tekil_yorum)

    return urun_paket, yorumlar_paket


def process_yemeksepeti_data(raw_json: dict) -> tuple[dict, list[dict]]:
    bizim_urun_id = str(uuid4())
    orijinal_link = raw_json.get("link")

    link_hash = hashlib.sha256(orijinal_link.encode('utf-8')).hexdigest()

    ham_yorumlar = raw_json.get("yorumlar", [])

    tum_yorum_puanlari = []
    for y in ham_yorumlar:
        ratings = y.get("ratings", [])
        overall_score = next((r.get("score") for r in ratings if
                              r.get("topic") == "overall" and isinstance(r.get("score"), (int, float))), None)

        if overall_score is not None:
            tum_yorum_puanlari.append(overall_score)

    hesaplanan_orj_puan = sum(tum_yorum_puanlari) / len(tum_yorum_puanlari)if tum_yorum_puanlari else None

    urun_paket = {
        "id": bizim_urun_id,
        "platform": raw_json.get("platform", "yemeksepeti"),
        "urun_adi": raw_json.get("baslik"),
        "urun_url_orj": orijinal_link,
        "urun_url_hash": link_hash,
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": hesaplanan_orj_puan,
        "kategori": None,
        "hesaplanan_puan": None,
        "guncel_ozet": None,
        "ozet_embedding": None,
        "click_count": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "like_rate": None
    }

    yorumlar_paket = []

    for raw_review in ham_yorumlar:
        ratings = raw_review.get("ratings", [])

        # Puanları topic'lere (konulara) göre ayrıştırıyoruz
        overall_score = next((r.get("score") for r in ratings if r.get("topic") == "overall"), None)
        food_score = next((r.get("score") for r in ratings if r.get("topic") == "restaurant_food"), None)
        rider_score = next((r.get("score") for r in ratings if r.get("topic") == "rider"), None)

        # Sipariş edilen ürünleri (isimleri) listeleme ve TOPLAM SEPET TUTARINI hesaplama
        product_variations = raw_review.get("productVariations", [])
        alinan_urunler = []
        tahmini_sepet_tutari = 0

        for item in product_variations:
            urun_adi = item.get("defaultTitle")
            fiyat = item.get("unitPrice", 0)

            if urun_adi:
                alinan_urunler.append(urun_adi)
            if isinstance(fiyat, (int, float)):
                tahmini_sepet_tutari += fiyat

        metadata = {
            "verilen_puan": overall_score,
            "lezzet_puani": food_score,
            "kurye_puani": rider_score,  # Kurye performansı NLP için çok değerlidir
            "siparis_edilen_urunler": alinan_urunler,  # ["Coni Çıtır...", "Tavuk Kanat..."]
            "tahmini_sepet_tutari": tahmini_sepet_tutari,  # Analitik altını: Örn 1370 TL
            "faydali_bulan_sayisi": raw_review.get("likeCount", 0),
            "anonim_mi": raw_review.get("isAnonymous")  # True/False
        }

        tekil_yorum = {
            "id": str(uuid4()),
            "urun_id": bizim_urun_id,
            "yorum_metni": raw_review.get("temiz_metin") or raw_review.get("text"),
            "metadata": metadata,
            "dinamik_kategori_parcalari": None,
            "embedding": None,
            "created_at": datetime.now()
        }
        yorumlar_paket.append(tekil_yorum)

    return urun_paket, yorumlar_paket


def donustur_ve_kaydet(ham_json_yolu: str) -> str:
    try:
        with open(ham_json_yolu, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except Exception as e:
        return f"json okuma hatası ({ham_json_yolu}): {e}"

    platform = raw_data.get("platform")
    if not platform:
        return f"Platform bilgisi bulunamadı: {ham_json_yolu}"

    hedef_klasor = os.path.join("Transformed_datas",platform)
    os.makedirs(hedef_klasor, exist_ok=True)

    if platform == "trendyol":
        urun_paket, yorumlar_paket = process_trendyol_data(raw_data)
    elif platform == "hepsiburada":
        urun_paket, yorumlar_paket = process_hepsiburada_data(raw_data)
    elif platform == "ciceksepeti":
        urun_paket, yorumlar_paket = process_ciceksepeti_data(raw_data)
    elif platform == "steam":
        urun_paket, yorumlar_paket = process_steam_data(raw_data)
    elif platform == "yemeksepeti":
        urun_paket, yorumlar_paket = process_yemeksepeti_data(raw_data)
    elif platform == "trendyol-go":
        urun_paket, yorumlar_paket = process_tygo_data(raw_data)
    elif platform == "etstur":
        urun_paket, yorumlar_paket = process_etstur_data(raw_data)
    elif platform == "airbnb":
        urun_paket, yorumlar_paket = process_airbnb_data(raw_data)
    elif platform == "maps":
        urun_paket, yorumlar_paket = process_maps_data(raw_data)
    else:
        return f"⚠️ Dönüştürücü Hatası: Bilinmeyen platform '{platform}'"


    temiz_veri = {
        "urun_paketi":urun_paket,
        "yorum_paketi":yorumlar_paket
    }

    dosya_adi = os.path.basename(ham_json_yolu)
    yeni_dosya_yolu = os.path.join(hedef_klasor, f"clean_{dosya_adi}")

    with open(yeni_dosya_yolu, "w", encoding='utf-8') as f:
        json.dump(temiz_veri, f, ensure_ascii=False, indent=4, default=str)

    return f"Temiz veri klasöre kaydedildi: {yeni_dosya_yolu}"







