from collections import Counter
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import pipeline, AutoTokenizer
from functions.scraper import linkten_veri_cek
from functions.Transformer import donustur_ve_kaydet
from functions.db_manager import DatabaseManager
from functions.utils import url_cleaning, url_hashing, url_cozumle, yorumlara_puan_ver, vllm_ile_toplu_isleme, oransal_yorum_secimi, llama_ile_toplu_ozet
import requests
from fastapi.middleware.cors import CORSMiddleware

class ChatRequest(BaseModel):
    productId: str
    user_message: str
class ExtractRequest(BaseModel):
    url: str

class ProductIdRequest(BaseModel):
    productId: str

ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[INFO] ONNX BerTurk modeli yükleniyor...")
    MODEL_ID = "Halitbkts/berturk-review-score-predicter-model-onnx"
    try:
        model = ORTModelForSequenceClassification.from_pretrained(MODEL_ID)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        ml_models["classifier"] = pipeline("text-classification", model=model, tokenizer=tokenizer)
        print("INFO - [STARTUP] Model başarıyla yüklendi ve FastAPI sunucusu hazır!")
    except Exception as e:
        print(f"[ERROR] Model yüklenirken bir hata oluştu: {e}")

    yield

    print("[INFO] FastAPI sunucusu kapanıyor. Temizlik işlemleri yapılıyor...")
    ml_models.clear()

    try:
        DatabaseManager.close_pool()
    except Exception as e:
        print(f"[ERROR] Havuz kapatılırken bir sorun oluştu: {e}")


app = FastAPI(title="LLM Destekli Yorum Analiz API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme aşamasında tüm kökenlere izin veriyoruz
    allow_credentials=True,
    allow_methods=["*"],  # POST, GET, OPTIONS vb. tüm isteklere izin ver
    allow_headers=["*"],
)


@app.post("/api/v1/extract")
def extract_and_save(request: ExtractRequest):
    try:
        db = DatabaseManager()
        temiz_url = url_cleaning(request.url)
        url_hash = url_hashing(temiz_url)
        platform, platform_id = url_cozumle(temiz_url)

        if not platform:
            raise HTTPException(status_code=400, detail="Platform tanımlanamadı.")

        mevcut_urun_id = db.fetch_query("SELECT id FROM products WHERE url_hash = %s", (url_hash,))
        if mevcut_urun_id:
            return {
                "status": "success",
                "message": "Ürün zaten veritabanında mevcut.",
                "productId": str(mevcut_urun_id[0][0])
            }

        kazima_mesaji, ham_dosya_yolu = linkten_veri_cek(temiz_url, platform)
        if not ham_dosya_yolu or not os.path.exists(ham_dosya_yolu):
            raise HTTPException(status_code=500, detail=f"Veri çekilemedi: {kazima_mesaji}")

        urun_paketi, yorum_paketleri = donustur_ve_kaydet(
            ham_dosya_yolu,
            platform=platform,
            platform_id=platform_id,
            temiz_url=temiz_url,
            url_hash=url_hash
        )

        urun_paketi['avg_model_score'] = None
        if yorum_paketleri:
            for yrm in yorum_paketleri:
                yrm['predicted_score'] = None

        product_id = db.save_product_and_reviews(urun_paketi, yorum_paketleri)

        return {
            "status": "success",
            "message": "Veriler başarıyla işlendi ve kaydedildi.",
            "productId": str(product_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kazıma hatası: {str(e)}")


# Aşama 2: Puanlama (Score)
@app.post("/api/v1/score")
async def score_reviews(request: ProductIdRequest):
    try:
        db = DatabaseManager()
        yorum_paketleri = db.get_unscored_data_by_produc_id(request.productId)

        if not yorum_paketleri:
            raise HTTPException(status_code=404, detail="Bu ürüne ait puanlanacak yorum bulunamadı.")

        classifier = ml_models.get("classifier")
        if not classifier:
            raise HTTPException(status_code=503, detail="BERTurk modeli RAM'de bulunamadı.")

        yorum_paketleri = yorumlara_puan_ver(classifier, yorum_paketleri)

        gecerli_puanlar = [y['predicted_score'] for y in yorum_paketleri if y.get('predicted_score') is not None]
        avg_model_score = None
        if gecerli_puanlar:
            avg_model_score = round(sum(gecerli_puanlar) / len(gecerli_puanlar), 2)

        db.update_scores(request.productId, avg_model_score, yorum_paketleri)

        return {
            "status": "success",
            "message": f"Yorumlar puanlandı. Ortalama: {avg_model_score}",
            "productId": request.productId
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Puanlama hatası: {str(e)}")


@app.post("/api/v1/categorize")
async def categorize_aspects(request: ProductIdRequest):
    try:
        db = DatabaseManager()
        product_id = request.productId

        urun_kategori_verisi = db.fetch_query("Select category FROM products WHERE id = %s", (product_id,))
        if not urun_kategori_verisi:
            raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

        urun_grubu = urun_kategori_verisi[0][0]
        secilen_yorumlar = oransal_yorum_secimi(db, product_id, 50)

        if not secilen_yorumlar or len(secilen_yorumlar) < 5:
            return {
                "status": "warning",
                "message": "Kategorizasyon için yeterli yorum bulunamadı (En az 5 gerekli).",
                "productId": product_id
            }

        metin_id_haritasi = {y["clean_text"]: y["id"] for y in secilen_yorumlar}
        yorum_metinleri = list(metin_id_haritasi.keys())

        toplu_yanitlar = await vllm_ile_toplu_isleme(yorum_metinleri, urun_grubu)

        snippet_paketleri = []
        for yanit in toplu_yanitlar:
            orijinal_metin = yanit.get("orijinal_yorum")
            parent_review_id = metin_id_haritasi.get(orijinal_metin)

            for kat_veri in yanit.get("kategoriler", []):
                snippet_text = kat_veri.get("parca") or kat_veri.get("metin")
                kategori_adi = kat_veri.get("kategori")

                if snippet_text and kategori_adi:
                    snippet_paketleri.append({
                        "review_id": parent_review_id,
                        "category_name": kategori_adi,
                        "clean_text": snippet_text[:500]
                    })

        if not snippet_paketleri:
            raise HTTPException(status_code=500, detail="Qwen modeli yorumları parçalayamadı.")

        classifier = ml_models.get("classifier")
        if not classifier:
            raise HTTPException(status_code=503, detail="BERTurk modeli RAM'de bulunamadı.")

        puanlanmis_paketler = yorumlara_puan_ver(classifier, snippet_paketleri)

        final_aspects = []
        for pkt in puanlanmis_paketler:
            final_aspects.append({
                "review_id": pkt["review_id"],
                "category_name": pkt["category_name"],
                "snippet_text": pkt["clean_text"],
                "snippet_score": pkt.get("predicted_score")
            })

        db.save_review_aspects(final_aspects)

        return {
            "status": "success",
            "message": f"Yorumlar başarıyla niteliklerine ayrıldı ve alt-puanları hesaplandı. Toplam {len(final_aspects)} parça kaydedildi.",
            "productId": product_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kategorizasyon hatası: {str(e)}")



# Aşama 4: Özetleme (Summarize)
@app.post("/api/v1/summarize")
async def summarize_reviews(request: ProductIdRequest):
    try:

        db = DatabaseManager()
        product_id = request.productId

        aspect_sorgusu = "SELECT review_id, category_name, snippet_text, snippet_score FROM review_aspects WHERE review_id IN (SELECT id FROM reviews WHERE product_id = %s)"
        ham_parcalar = db.fetch_query(aspect_sorgusu, (product_id,))

        if not ham_parcalar:
            raise HTTPException(status_code=404, detail="Bu ürüne ait özetlenecek nitelik bulunamadı.")

        islenen_review_idler = list(set([p[0] for p in ham_parcalar]))

        kategori_sayaclari = Counter([p[1] for p in ham_parcalar if p[1] and p[1].lower() != "genel"])
        top_3_kategori = [k[0] for k in kategori_sayaclari.most_common(3)]

        urun_sorgusu = "SELECT avg_model_score FROM products WHERE id = %s;"
        urun_verisi = db.fetch_query(urun_sorgusu, (product_id,))
        avg_model_score = float(urun_verisi[0][0]) if urun_verisi and urun_verisi[0][0] is not None else 0.0

        # Sadece puanlanmış yorumları (dağılımı bulmak ve genel özet metnini oluşturmak için) çekiyoruz
        yorumlar_sorgusu = "SELECT id, clean_text, predicted_score FROM reviews WHERE product_id = %s AND predicted_score IS NOT NULL;"
        tum_yorumlar = db.fetch_query(yorumlar_sorgusu, (product_id,))

        puanlar = [int(y[2]) for y in tum_yorumlar]
        toplam_yorum_sayisi = len(puanlar)
        sayac = Counter(puanlar)

        # Yeniden hesaplamak yerine doğrudan DB'deki avg_model_score'u kullanıyoruz
        dagilim_raporu = f"Toplam Yorum: {toplam_yorum_sayisi} | Ortalama Puan: {avg_model_score:.2f} | Dağılım: " + ", ".join(
            [f"{p} Yıldız: {sayac[p]} adet" for p in sorted(sayac.keys())]
        )

        system_prompt = (
            "Sen profesyonel bir e-ticaret veri etiketleme ve özetleme uzmanısın. "
            "Sana verilen müşteri yorumlarını, puan dağılımını ve uzunluk sapmalarını dikkate alarak tarafsız, net ve veriye sadık bir dille özetlersin."
        )

        llama_istekleri = []

        for kat_adi in top_3_kategori:
            ilgili_parcalar = [p for p in ham_parcalar if p[1] == kat_adi]
            kat_puanlari = [float(p[3]) for p in ilgili_parcalar if p[3] is not None]
            kat_ortalama = round(sum(kat_puanlari) / len(kat_puanlari), 2) if kat_puanlari else None
            kaynak_id_listesi = list(set([p[0] for p in ilgili_parcalar]))

            gorulen_parcalar = set()
            essiz_parcalar = []
            for p in ilgili_parcalar:
                temiz_metin = p[2].strip().lower()
                if temiz_metin not in gorulen_parcalar:
                    gorulen_parcalar.add(temiz_metin)
                    essiz_parcalar.append(f"[Puan: {int(p[3] if p[3] else 0)}/5] {p[2]}")

            kategori_metni = " | ".join(essiz_parcalar)

            user_content = f"Görev: Kategori Özeti\nKategori: {kat_adi}\nÜrün Dağılımı: {dagilim_raporu}\nYorumlar:\n{kategori_metni}"

            llama_istekleri.append({
                "system_prompt": system_prompt,
                "user_content": user_content,
                "meta": {"type": "CATEGORY", "category_name": kat_adi, "avg_score": kat_ortalama,
                         "source_ids": kaynak_id_listesi}
            })

        qwen_secimi_yorumlar = [y for y in tum_yorumlar if y[0] in islenen_review_idler]

        gorulen_genel_yorumlar = set()
        essiz_genel_yorumlar = []
        genel_kaynak_id_listesi = []

        for y in qwen_secimi_yorumlar:
            temiz_metin = y[1].strip().lower()
            if temiz_metin not in gorulen_genel_yorumlar:
                gorulen_genel_yorumlar.add(temiz_metin)
                essiz_genel_yorumlar.append(f"[Puan: {int(y[2])}/5] {y[1]}")
                genel_kaynak_id_listesi.append(y[0])

        tum_yorumlar_metni = " | ".join(essiz_genel_yorumlar)

        genel_user_content = f"Görev: Genel Özet\nÜrün Dağılımı: {dagilim_raporu}\nYorumlar:\n{tum_yorumlar_metni}"

        llama_istekleri.append({
            "system_prompt": system_prompt,
            "user_content": genel_user_content,
            "meta": {"type": "GENERAL", "avg_score": avg_model_score, "source_ids": genel_kaynak_id_listesi}
        })

        sonuclar = await llama_ile_toplu_ozet(llama_istekleri)

        yazilan_ozet_sayisi = 0
        genel_ozet_metni_arayuz_icin = None

        for sonuc in sonuclar:
            ozet_metni = sonuc["ozet"]
            meta = sonuc["meta"]

            if not ozet_metni:
                continue

            if meta["type"] == "GENERAL":
                genel_ozet_metni_arayuz_icin = ozet_metni

            # Tertemiz, tek satırlık Data Access Layer (DAL) çağrısı
            summary_id = db.save_summary_and_get_id(
                product_id,
                meta["type"],
                meta.get("category_name"),
                ozet_metni,
                meta["avg_score"]
            )

            if summary_id:
                yazilan_ozet_sayisi += 1

                if meta["source_ids"]:
                    iliskiler = [(summary_id, r_id) for r_id in meta["source_ids"]]
                    db.save_summary_source_reviews(iliskiler)

        return {
            "status": "success",
            "message": f"Yapay zeka özeti başarıyla oluşturuldu. Toplam {yazilan_ozet_sayisi} özet kaydedildi.",
            "productId": product_id,
            "summary": genel_ozet_metni_arayuz_icin
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Özetleme hatası: {str(e)}")

#Aşama 5: Chatbot
#chati hafızada tutan sözlük
chat_histories = {}
@app.post("/api/v1/chat")
async def chat_with_vivid_bot(request: ChatRequest):
    try:
        db = DatabaseManager()

        # 1. Adım: Veritabanından zengin bağlamı getir (Retrieval)
        context_bilgisi = get_product_rag_context(request.productId, db)

        # 2. Adım: Hafıza (Session) Yönetimi
        if request.productId not in chat_histories:
            chat_histories[request.productId] = []

        chat_histories[request.productId].append({"role": "user", "content": request.user_message})
        aktif_gecmis = chat_histories[request.productId][-6:]

        # 3. Adım: Kurallı ve Doğal Türkçe Sağlayan Sistem Promptu
        system_prompt = f"""
        Sen VividAI platformunun resmi, zeki, kurallı ve akıcı Türkçe konuşan müşteri asistanısın.
        
        [GÖREV KAPSAMI VE SOHBET]
        Kullanıcıyla doğal, kibar ve akıcı bir etkileşim kur. Kullanıcının önceki mesajlarda verdiği bilgileri (isim vb.) hatırla ve sohbet bağlamını koru. 
        
        [KATI VERİ KURALLARI]
        1. Ürün, restoran veya analizlerle ilgili bir soru sorulduğunda SADECE aşağıdaki [VİVİDAİ BİLGİ HAVUZU] alanında yer alan verilere sadık kal.
        2. Havuzda olmayan bir bilgi istenirse kafandan uydurma (halüsinasyon görme); "Bu konuda sistemimizde yeterli veri bulunmuyor" diyerek kibarca reddet.
        3. Çelişki Oranı sorulursa: Bunun kelime zıtlığı olmadığını, memnuniyet puanlarındaki varyans/kutuplaşma olduğunu profesyonelce açıkla (Örn: "Toplumun bir kısmı 5 yıldız verirken diğer kısmının 1 yıldız vererek fikir ayrılığına düşmesi").
        4. Asla devrik veya yarım cümle kurma, Türkçe dilbilgisi kurallarına kusursuz uy.
        
        [VİVİDAİ BİLGİ HAVUZU]:
        {context_bilgisi}
        """
        tam_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        for mesaj in aktif_gecmis:
            tam_prompt += f"<|im_start|>{mesaj['role']}\n{mesaj['content']}<|im_end|>\n"
        tam_prompt += "<|im_start|>assistant\n"


        ollama_url = "http://localhost:11434/api/generate"
        istek_ayarlari = {
            "model": "qwen2.5:14b",
            "prompt": tam_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "stop": ["<|im_end|>", "<|im_start|>"]
            }
        }

        response = requests.post(ollama_url, json=istek_ayarlari, timeout=90)
        bot_cevap = response.json().get("response", "").strip()

        chat_histories[request.productId].append({"role": "assistant", "content": bot_cevap})

        return {"status": "success", "response": bot_cevap}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sistemsel Chatbot Hatası: {str(e)}")



# Uygulamayı Ayağa Kaldırma
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api_runner:app", host="0.0.0.0", port=port)

