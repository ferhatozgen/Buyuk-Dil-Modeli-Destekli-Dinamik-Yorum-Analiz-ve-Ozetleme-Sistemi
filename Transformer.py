from datetime import datetime
from uuid import uuid4

def parse_turkish_date(date_str:str) -> datetime:
    if not date_str:
        return None

    aylar = {
        "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6,
        "Temmuz": 7, "Ağustos": 8, "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12
    }

    try:
        gun, ay_isim, yil = date_str.strip().split()
        ay = aylar.get(ay_isim,1)
        return datetime(int(yil),ay,gun)
    except ValueError:
        return None




def process_airbnb_date(raw_json: dict) -> tuple[dict, list[dict]]:
    bizim_urun_id = str(uuid4())
    airbnb_orijinal_id = raw_json.get("urun_id")

    ham_yorumlar = raw_json.get("yorumlar", [])

    gecerli_puanlar = [y.get("rating") for y in ham_yorumlar if y.get("rating") is not None]
    hesaplanan_puan = sum(gecerli_puanlar) / len(gecerli_puanlar) if gecerli_puanlar else None

    urun_paket = {
        "id": bizim_urun_id,
        "platform":raw_json.get("platform","airbnb"),
        "urun_adi":f"Airbnb Evi - {airbnb_orijinal_id}", ### gerçek adı gelcek ###
        "urun_url_orj":f"https://www.airbnb.com.tr/rooms/{airbnb_orijinal_id}", ### gercek url gelcek ###
        "urun_url_hash": f"hash_of_{airbnb_orijinal_id}", # Gerçek url de hashlib kullanacağız #
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": round(hesaplanan_puan,1) if hesaplanan_puan else None,
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
    ciceksepeti_orijinal_id = raw_json.get("urun_id")

    ham_yorumlar = raw_json.get("yorumlar", [])

    gecerli_puanlar = [int(y.get("rating")[0])
                       for y in ham_yorumlar
                       if y.get("rating") and y.get("rating")[0].isdigit()
                       ]
    hesaplanan_puan = sum(gecerli_puanlar) / len(gecerli_puanlar) if gecerli_puanlar else None

    urun_paket = {
        "id": bizim_urun_id,
        "platform": raw_json.get("platform", "ciceksepeti"),
        "urun_adi": f"Airbnb Evi - {ciceksepeti_orijinal_id}",  ### gerçek adı gelcek ###
        "urun_url_orj": f"https://www.airbnb.com.tr/rooms/{ciceksepeti_orijinal_id}",  ### gercek url gelcek ###
        "urun_url_hash": f"hash_of_{ciceksepeti_orijinal_id}",  # Gerçek url de hashlib kullanacağız #
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": round(hesaplanan_puan, 1) if hesaplanan_puan else None,
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
    etstur_orijinal_id = raw_json.get("urun_id")

    ham_yorumlar = raw_json.get("yorumlar", [])

    gecerli_puanlar = [
        round((float(y.get("score")) / 20) * 2) / 2
        for y in ham_yorumlar
        if isinstance(y.get("score"), (int, float))
    ]


    if gecerli_puanlar:
        ham_ortalama = sum(gecerli_puanlar) / len(gecerli_puanlar)
        hesaplanan_puan = round(ham_ortalama * 2) / 2  # 0.5'in katlarına yuvarlar
    else:
        hesaplanan_puan = None

    urun_paket = {
        "id": bizim_urun_id,
        "platform": raw_json.get("platform", "etstur"),
        "urun_adi": f"Airbnb Evi - {etstur_orijinal_id}",  ### gerçek adı gelcek ###
        "urun_url_orj": f"https://www.airbnb.com.tr/rooms/{etstur_orijinal_id}",  ### gercek url gelcek ###
        "urun_url_hash": f"hash_of_{etstur_orijinal_id}",  # Gerçek url de hashlib kullanacağız #
        "image_url": raw_json.get("gorsel_url"),
        "orj_puan": round(hesaplanan_puan, 1) if hesaplanan_puan else None,
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
