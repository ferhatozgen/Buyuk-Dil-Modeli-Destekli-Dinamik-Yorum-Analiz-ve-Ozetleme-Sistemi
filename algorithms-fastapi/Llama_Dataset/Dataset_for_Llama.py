import os
import json
import time
import asyncio
from collections import Counter
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- KENDİ MODÜLLERİNİZ ---
from functions.db_manager import DatabaseManager
from functions.utils import vllm_ile_toplu_isleme
from config import URUN_GRUP_SEMALARI
from functions.logger import setup_logger

# --- KONFİGÜRASYON VE SABİTLER ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.0-flash"

HEDEF_URUN_KATEGORI_BASINA = 50
MAX_YORUM_SAYISI = 50
JSONL_DOSYA_YOLU = "train.jsonl"
CHECKPOINT_DOSYASI = "islenen_urunler.json"

logger = setup_logger("Dataset_Generator")

# --- İŞLENECEK KATEGORİLER LİSTESİ ---
# İşlemi biten kategorileri bu listeden silebilir veya başına '#' koyarak atlayabilirsin.
# Buraya yazdığın isimler config.py içindeki URUN_GRUP_SEMALARI anahtarlarıyla aynı olmalı.
ISLENECEK_KATEGORILER = [
    "anne_bebek_oyuncak",
    "cicek",
    "egitim_eglence",
    "elektronik_teknoloji",
    "ev_yasam_mobilya",
    "gezilecek_yer",
    "giyim_ayakkabi",
    "gunluk_ev",
    "hediyelik_esya",
    "kirtasiye_kitap_hobi",
    "kozmetik_kisisel_bakim",
    "kurumsal",
    "oyun",
    "pet_shop",
    "saglik",
    "spor_outdoor",
    "supermarket_gida",
    "yemek",
    "yenilebilir_cicek"
]


# --- CHECKPOINT YÖNETİMİ ---
def checkpoint_yukle():
    if os.path.exists(CHECKPOINT_DOSYASI):
        with open(CHECKPOINT_DOSYASI, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def checkpoint_kaydet(islenen_idler):
    with open(CHECKPOINT_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(list(islenen_idler), f)


# --- ORANSAL ÖRNEKLEME (STRATIFIED SAMPLING) ---
def oransal_yorum_secimi(db, urun_id, max_sayi):
    """
    Yorumları puanlarına göre oranlayarak seçer.
    Geriye metinle birlikte puan bilgisini de içeren bir sözlük listesi döner.
    """
    sorgu = "SELECT clean_text, predicted_score FROM reviews WHERE product_id = %s AND clean_text IS NOT NULL;"
    tum_yorumlar = db.fetch_query(sorgu, (urun_id,))

    if not tum_yorumlar:
        return []

    puan_gruplari = {1: [], 2: [], 3: [], 4: [], 5: [], 0: []}
    for metin, puan in tum_yorumlar:
        puan_val = int(puan) if puan is not None else 0
        if puan_val in puan_gruplari:
            puan_gruplari[puan_val].append(metin)
        else:
            puan_gruplari[0].append(metin)

    for p in puan_gruplari:
        puan_gruplari[p].sort(key=len, reverse=True)

    toplam_yorum = len(tum_yorumlar)
    secilen_yorumlar = []

    for p, yorumlar in puan_gruplari.items():
        if not yorumlar:
            continue
        oran = len(yorumlar) / toplam_yorum
        secilecek_adet = int(round(oran * max_sayi))

        # Sadece metni değil, ait olduğu puanı da paketleyerek ekliyoruz
        for metin in yorumlar[:secilecek_adet]:
            secilen_yorumlar.append({"metin": metin, "puan": p})

    if len(secilen_yorumlar) > max_sayi:
        secilen_yorumlar = secilen_yorumlar[:max_sayi]

    return secilen_yorumlar


# --- GEMINI YÖNETİCİSİ (YÜKSEK SADAKATLİ PROMPT) ---
def gemini_ile_ozet_uret(gorev_tipi: str, kategori_adi: str, metin_icerigi: str, dagilim_raporu: str) -> str:
    base_talimat = (
        f"Sen profesyonel bir veri etiketleme uzmanısın.\n"
        f"Ürünün Gerçek Puan İstatistikleri: {dagilim_raporu}\n\n"
        f"KURAL 1: 'Merhaba', 'Özetle', 'Yorumlara göre' gibi giriş kelimelerini KESİNLİKLE KULLANMA. Doğrudan bilgiye geç.\n"
        f"KURAL 2: Yorumların başındaki [Puan: X/5] etiketlerini ve yukarıdaki gerçek puan dağılım oranlarını kesinlikle dikkate al. "
        f"Sırf bir yorum daha uzun veya detaylı yazılmış diye onun fikrini genele yayma. Çoğunluğun istatistiksel ağırlığına sadık kal.\n"
        f"KURAL 3: Girdi metninde açıkça bahsedilmeyen hiçbir nesneyi, kelimeyi, giysi veya eşofman gibi alakasız terimleri halüsinasyon olarak çıktıya ekleme. "
        f"Yalnızca içerikte sunulan somut verilere sadık kal.\n"
    )

    if gorev_tipi == "Kategori Özeti":
        prompt = (f"{base_talimat}\n"
                  f"Görev: Aşağıda verilen müşteri yorumlarını analiz ederek SADECE '{kategori_adi}' bağlamında iki veya üç cümlelik profesyonel, net ve tarafsız bir özet çıkar.\n\n"
                  f"Yorumlar:\n{metin_icerigi}\n\n"
                  f"Özet Çıktısı:")
    else:
        prompt = (f"{base_talimat}\n"
                  f"Görev: Aşağıda verilen ürün yorumlarının tamamını analiz et ve ürünün genel artı/eksilerini vurgulayan 3-4 cümlelik tarafsız bir genel yönetici özeti çıkar.\n\n"
                  f"Yorumlar:\n{metin_icerigi}\n\n"
                  f"Özet Çıktısı:")

    max_deneme = 5

    for deneme in range(max_deneme):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                )
            )
            return response.text.strip().replace("\n", " ")

        except Exception as e:
            hata_mesaji = str(e)

            # 429 (Kota) veya 503 (Yoğunluk) hatalarını yakala
            if "429" in hata_mesaji or "RESOURCE_EXHAUSTED" in hata_mesaji or "503" in hata_mesaji or "UNAVAILABLE" in hata_mesaji:
                bekleme = 65  # Google'ın 50 saniyelik cezasına karşı 65 saniye güvenli bekleme
                logger.warning(
                    f"Google API Kotası/Yoğunluğu (Deneme {deneme + 1}/{max_deneme}). {bekleme} saniye bekleniyor...")
                time.sleep(bekleme)
            else:
                # Farklı bir kritik hata varsa logla ve bitir
                logger.error(f"Gemini API Kritik Hatası: {e}")
                return None

    logger.error(f"Gemini API {max_deneme} deneme sonrasında yanıt vermedi. Bu özet atlanıyor.")
    return None


# --- MODERN CHATML / MESSAGES FORMATLAYICI ---
def jsonl_satiri_olustur(gorev_tipi, kategori, dagilim_raporu, metin_icerigi, cikti_hedefi):
    """
    LLaMA modelinin fine-tune aşamasında en yüksek başarıyı veren
    'messages' (ChatML) yapısında çıktı üretir.
    """
    system_prompt = (
        "Sen profesyonel bir e-ticaret veri etiketleme ve özetleme uzmanısın. "
        "Sana verilen müşteri yorumlarını, puan dağılımını ve uzunluk sapmalarını dikkate alarak tarafsız, net ve veriye sadık bir dille özetlersin."
    )

    if gorev_tipi == "Kategori Özeti":
        user_content = f"Görev: {gorev_tipi}\nKategori: {kategori}\nÜrün Dağılımı: {dagilim_raporu}\nYorumlar:\n{metin_icerigi}"
    else:
        user_content = f"Görev: {gorev_tipi}\nÜrün Dağılımı: {dagilim_raporu}\nYorumlar:\n{metin_icerigi}"

    return json.dumps({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": cikti_hedefi}
        ]
    }, ensure_ascii=False)


# --- ANA ORKESTRASYON ---
async def veri_setini_olustur():
    db = DatabaseManager()
    islenen_idler = checkpoint_yukle()
    toplam_satir = 0

    logger.info("Veri seti oluşturma süreci başlıyor...")

    # Artık tüm şemayı değil, sadece yukarıda belirlediğimiz listeyi geziyoruz
    for urun_grubu in ISLENECEK_KATEGORILER:

        # Eğer listeye yazılan kategori ismi şemalarda yoksa uyar ve atla (hata vermesin diye güvenlik)
        if urun_grubu not in URUN_GRUP_SEMALARI:
            logger.warning(f"'{urun_grubu}' adlı kategori URUN_GRUP_SEMALARI içinde bulunamadı, atlanıyor.")
            continue

        logger.info(f"Kategori işleniyor: {urun_grubu}")

        urunler_sorgusu = "SELECT id, product_name FROM products WHERE category = %s LIMIT %s;"
        urunler = db.fetch_query(urunler_sorgusu, (urun_grubu, HEDEF_URUN_KATEGORI_BASINA))

        for urun in urunler:
            urun_id = urun[0]
            urun_adi = urun[1]

            if str(urun_id) in islenen_idler:
                continue

            secilen_yorumlar = oransal_yorum_secimi(db, urun_id, MAX_YORUM_SAYISI)

            # Belirlediğimiz güvenli taban tavan kontrolü
            if not secilen_yorumlar or len(secilen_yorumlar) < 5:
                logger.warning(f"Atlanıyor (Yetersiz Yorum): {urun_adi[:30]}")
                continue

            logger.info(f"Ürün işleniyor: {urun_adi[:30]}... ({len(secilen_yorumlar)} yorum)")

            # --- 1. HAMLE: MATEMATİKSEL DAĞILIM RAPORUNUN HAZIRLANMASI ---
            puanlar = [y["puan"] for y in secilen_yorumlar]
            toplam_secilen = len(puanlar)
            avg_puan = sum(puanlar) / toplam_secilen if toplam_secilen > 0 else 0
            sayac = Counter(puanlar)
            dagilim_raporu = f"Toplam Yorum: {toplam_secilen} | Ortalama Puan: {avg_puan:.2f} | Dağılım: " + ", ".join(
                [f"{p} Yıldız: {sayac[p]} adet" for p in sorted(sayac.keys())])

            # Orijinal yorum metinlerinin listesini çıkarıp vLLM sunucusuna gönderiyoruz
            yorum_metinleri = [y["metin"] for y in secilen_yorumlar]
            toplu_yanitlar = await vllm_ile_toplu_isleme(yorum_metinleri, urun_grubu)

            # Hızlı arama için yorum-puan haritası kuruyoruz
            yorum_puan_map = {y["metin"]: y["puan"] for y in secilen_yorumlar}

            # --- 2. HAMLE: PARÇALARI ETİKETLEME VE KARAKTER BUDAMA ---
            parcalanmis_veri = []
            for yanit in toplu_yanitlar:
                orig_metin = yanit.get("orijinal_yorum")
                puan = yorum_puan_map.get(orig_metin, 0)

                for kat_veri in yanit.get("kategoriler", []):
                    metin_val = kat_veri.get("parca") or kat_veri.get("metin")
                    kat_val = kat_veri.get("kategori")

                    if metin_val and kat_val:
                        # Uzun cümlelerin ağırlığı ezmesini engellemek için tavan budaması yapıyoruz
                        budanmis_metin = metin_val[:300] + "..." if len(metin_val) > 300 else metin_val
                        parcalanmis_veri.append({
                            "metin": budanmis_metin,
                            "kategori": kat_val,
                            "puan": puan
                        })

            if not parcalanmis_veri:
                logger.warning(f"Parçalayıcı model boş döndü veya vLLM yanıt veremedi: {urun_adi[:30]}")
                continue

            # Genel Özet Promptu için tüm yorum havuzunu skor etiketli ve karakter sınırıyla inşa ediyoruz
            genel_havuz_listesi = []
            for y in secilen_yorumlar:
                budanmis_y = y["metin"][:300] + "..." if len(y["metin"]) > 300 else y["metin"]
                genel_havuz_listesi.append(f"[Puan: {y['puan']}/5] {budanmis_y}")
            tum_yorumlar_metni = " | ".join(genel_havuz_listesi)

            kategori_sayaclari = Counter([item.get('kategori') for item in parcalanmis_veri if item.get('kategori')])
            top_3_kategori = [kat[0] for kat in kategori_sayaclari.most_common(3)]

            with open(JSONL_DOSYA_YOLU, "a", encoding="utf-8") as jsonl_dosya:

                # --- KATEGORİ ÖZETLERİNİN ÜRETİMİ ---
                for kategori_adi in top_3_kategori:
                    kategoriye_ait_cumleler = [
                        f"[Puan: {item['puan']}/5] {item['metin']}"
                        for item in parcalanmis_veri if item.get('kategori') == kategori_adi
                    ]
                    kategori_metni = " | ".join(kategoriye_ait_cumleler)

                    if len(kategori_metni.split()) < 4:
                        continue

                    # --- 3. HAMLE: İSTATİSTİĞİ GEMINI'YE FISILDAMA ---
                    kategori_ozeti = gemini_ile_ozet_uret("Kategori Özeti", kategori_adi, kategori_metni,
                                                          dagilim_raporu)

                    if kategori_ozeti:
                        jsonl_satiri = jsonl_satiri_olustur("Kategori Özeti", kategori_adi, dagilim_raporu,
                                                            kategori_metni, kategori_ozeti)
                        jsonl_dosya.write(jsonl_satiri + "\n")
                        toplam_satir += 1

                # --- GENEL ÖZETİN ÜRETİMİ ---
                genel_ozet = gemini_ile_ozet_uret("Genel Özet", "", tum_yorumlar_metni, dagilim_raporu)
                if genel_ozet:
                    jsonl_satiri = jsonl_satiri_olustur("Genel Özet", "", dagilim_raporu, tum_yorumlar_metni,
                                                        genel_ozet)
                    jsonl_dosya.write(jsonl_satiri + "\n")
                    toplam_satir += 1

            islenen_idler.add(str(urun_id))
            checkpoint_kaydet(islenen_idler)

            time.sleep(20)

    DatabaseManager.close_pool()
    logger.info(f"İŞLEM TAMAMLANDI! Toplam {toplam_satir} adet yüksek kaliteli ChatML eğitim satırı yazıldı.")


if __name__ == "__main__":
    asyncio.run(veri_setini_olustur())