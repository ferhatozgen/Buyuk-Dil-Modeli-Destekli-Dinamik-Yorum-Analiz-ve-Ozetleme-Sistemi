import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tqdm import tqdm
from functions.db_manager import DatabaseManager
from functions.logger import setup_logger

load_dotenv()
logger = setup_logger("DatasetBuilder")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    logger.error("GEMINI_API_KEY çevre değişkeni bulunamadı. Lütfen .env dosyasını kontrol edin.")
    exit(1)

client = genai.Client(api_key=api_key)

def create_chatml_line(system_prompt, user_prompt, assistant_response):
    return json.dumps({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_response}
        ]
    }, ensure_ascii=False)

def analyse_w_gemini(system_prompt, user_prompt):
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.1,
            ))
        content = response.text.strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("\n", 1)[0].strip()

        return content
    except Exception as e:
        logger.error(f"Gemini API hatası: {e}")
        return ""

def gold_dataset_creator():
    db = DatabaseManager()
    query = """
    WITH RastgeleUrunler AS (
        SELECT id as product_id, product_name
        FROM (
            SELECT id, product_name,
                   ROW_NUMBER() OVER(PARTITION BY platform ORDER BY RANDOM()) as rnk
            FROM products
            WHERE id IN (SELECT DISTINCT product_id FROM reviews)
        ) ranked_products
        WHERE rnk <= 2 
    )
    SELECT ru.product_name, r.clean_text
    FROM RastgeleUrunler ru
    JOIN reviews r ON ru.product_id = r.product_id;
    """
    urunler_ve_yorumlari = {}

    try:
        with db.get_connection()as conn:
            with conn.cursor() as cur:
                cur.execute(query)

                for product_name, yorum in cur.fetchall():
                    if not yorum or len(yorum.strip()) < 5:
                        continue
                    if product_name not in urunler_ve_yorumlari:
                        urunler_ve_yorumlari[product_name] = []

                    if len(urunler_ve_yorumlari[product_name]) < 10:
                        urunler_ve_yorumlari[product_name].append(yorum.strip())
    except Exception as e:
        logger.error(f"Veritabanı sorgu hatası: {e}")
        return

    logger.info(f"Veritabanından {len(urunler_ve_yorumlari)} yorum çekildi. Gemini ile analiz başlıyor...")

    sys_gorev_1 = "Görev 1: Sen bir duygu analizi modelisin. Verilen yoruma 1.0 ile 5.0 arasında objektif bir puan ver. Sadece rakam dön."
    sys_gorev_2 = "Görev 2: Sana bir ürüne ait BİRDEN FAZLA müşteri yorumu verilecek. Bu yorumların genelini analiz et ve en çok bahsedilen 3 veya 4 profesyonel kategori başlığını çıkar. SADECE geçerli bir JSON array dön. (Örn: [\"Hız\", \"Lezzet\"])"
    sys_gorev_3 = "Görev 3: Sana verilen yorumu anlamsal bütünlüğe göre parçalara ayır. Her parçayı, sana önceden verilmiş Kategori Havuzuyla eşleştir. SADECE geçerli bir JSON dön: [{\"parca\": \"...\", \"kategori\": \"...\"}]"
    sys_gorev_4 = "Görev 4: Sana bir ürüne ait onlarca yorumun parçalanmış/kategorize edilmiş hali devasa bir JSON listesi olarak verilecek. Buna bakarak profesyonel, akıcı bir genel özet ve kategori bazlı özetler çıkar. SADECE JSON dön: {\"genel_ozet\": \"...\", \"kategori_ozetleri\": {\"kategori1\": \"özet\"}}"

    output_file = "gold_dataset.jsonl"
    basarili_satir = 0

    with open(output_file, 'w', encoding='utf-8') as f:
        for product_name, yorumlar_listesi in tqdm(urunler_ve_yorumlari.items(), desc="Ürünler üzerinde analiz yapılıyor"):
            if len(yorumlar_listesi) == 0:
                continue

            toplu_yorum = "\n".join([f"- {y}" for y in yorumlar_listesi])

            g2_user_prompt = f"Ürün: {product_name}\nYorumlar:\n{toplu_yorum}"
            ortak_kategoriler_json = analyse_w_gemini(sys_gorev_2, g2_user_prompt)

            if ortak_kategoriler_json:
                f.write(create_chatml_line(sys_gorev_2, g2_user_prompt, ortak_kategoriler_json) + "\n")
                basarili_satir += 1
            else:
                logger.warning(f"Ortak kategoriler alınamadı: {product_name}")
                continue

            tum_parcalar = []

            for yorum in yorumlar_listesi:
                puan = analyse_w_gemini(sys_gorev_1, yorum)
                if puan:
                    f.write(create_chatml_line(sys_gorev_1, yorum, puan) + "\n")
                    basarili_satir += 1

                g3_user_prompt = f"Kategori Havuzu: {ortak_kategoriler_json}\nİncelenecek Yorum: {yorum}"
                parcalar_json = analyse_w_gemini(sys_gorev_3, g3_user_prompt)

                if parcalar_json:
                    f.write(create_chatml_line(sys_gorev_3, g3_user_prompt, parcalar_json) + "\n")
                    basarili_satir += 1

                    try:
                        tum_parcalar.extend(json.loads(parcalar_json))
                    except json.JSONDecodeError:
                        pass
            if tum_parcalar:
                g4_user_prompt = json.dumps(tum_parcalar, ensure_ascii=False)
                ozet_json = analyse_w_gemini(sys_gorev_4, g4_user_prompt)

                if ozet_json:
                    f.write(create_chatml_line(sys_gorev_4, g4_user_prompt, ozet_json) + "\n")
                    basarili_satir += 1

    logger.info(f"Gold dataset oluşturma tamamlandı. Toplam başarılı satır: {basarili_satir}")
    db.close_pool()

if __name__ == "__main__":
    gold_dataset_creator()

