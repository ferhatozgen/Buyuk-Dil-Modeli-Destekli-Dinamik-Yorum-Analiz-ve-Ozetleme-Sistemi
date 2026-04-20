import psycopg2
from psycopg2.extras import execute_values, Json
import logging
from dotenv import load_dotenv
import os

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.config = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"), # <--- BURASI os.getenv OLMALI!
            "port": os.getenv("DB_PORT"),
            "sslmode": "require" # Neon gibi bulut servisler için bu ŞART
        }

    def save_product_and_reviews(self, urun_paketi, yorum_paketleri):
        conn = None
        try:
            conn = psycopg2.connect(**self.config)
            cur = conn.cursor()

            # 1. Products Tablosuna Kayıt ve GERÇEK ID'yi Alma
            # RETURNING id ekledik, çünkü ürün zaten varsa DB'deki gerçek UUID'yi almamız lazım.
            product_query = """
                INSERT INTO products (
                    id, platform, platform_id, product_name, image_url, 
                    original_url, url_hash, avg_orj_score, status, last_updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url_hash) DO UPDATE SET         
                    avg_orj_score = EXCLUDED.avg_orj_score,
                    last_updated_at = CURRENT_TIMESTAMP,
                    status = 'active'
                RETURNING id; 
            """

            cur.execute(product_query, (
                urun_paketi['id'], urun_paketi['platform'], urun_paketi['platform_id'],
                urun_paketi['product_name'], urun_paketi['image_url'],
                urun_paketi['original_url'], urun_paketi['url_hash'],
                urun_paketi['avg_orj_score'], urun_paketi['status'],
                urun_paketi['last_updated_at']
            ))

            # DB'deki gerçek ID'yi yakalıyoruz (UUID uyuşmazlığını çözer)
            db_actual_id = cur.fetchone()[0]

            # 2. Eski Yorumları Temizleme (Opsiyonel ama Tavsiye Edilir)
            # Aynı ürünü tekrar çekiyorsak mükerrer yorum olmaması için eskileri siliyoruz.
            # (İleride yorum bazlı 'id' üzerinden kontrol de yapabilirsin)
            cur.execute("DELETE FROM reviews WHERE product_id = %s", (db_actual_id,))

            # 3. Reviews Tablosuna Toplu Kayıt
            review_query = """
                INSERT INTO reviews (
                    product_id, original_rating, raw_text, clean_text, metadata
                ) VALUES %s
            """

            review_values = [
                (
                    db_actual_id,  # Transformer'dan gelen değil, DB'den aldığımız ID'yi kullanıyoruz!
                    y['original_rating'],
                    y['raw_text'],
                    y['clean_text'],
                    Json(y['metadata'])
                ) for y in yorum_paketleri
            ]

            execute_values(cur, review_query, review_values)

            conn.commit()
            print(f"--- [DB BAŞARILI] --- {urun_paketi['product_name']} kaydedildi.")

        except Exception as e:
            if conn: conn.rollback()
            raise Exception(f"Veritabanı kayıt hatası: {e}")  # Hatayı yukarı (main'e) fırlatıyoruz
        finally:
            if conn: cur.close(); conn.close()