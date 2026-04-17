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
            "host": "localhost",
            "port": "5432"
        }

    def save_product_and_reviews(self, urun_paketi, yorum_paketleri):
        """
        (products ve reviews tablolarını doldurur.)
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.config)
            cur = conn.cursor()

            # 1. Products Tablosuna Kayıt (Veya Güncelleme)
            # dbde 'url_hash' UNIQUE olduğu için ON CONFLICT kullanıyoruz bu sayede eğer aynı link giriliyorsa hata demek yerine o ürünün puanını güncelliyor.
            product_query = """
                INSERT INTO products (
                    id, platform, platform_id, product_name, image_url, 
                    original_url, url_hash, avg_orj_score, status, last_updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url_hash) DO UPDATE SET         
                    avg_orj_score = EXCLUDED.avg_orj_score,
                    last_updated_at = CURRENT_TIMESTAMP,
                    status = 'active';
            """

            cur.execute(product_query, (
                urun_paketi['id'],
                urun_paketi['platform'],
                urun_paketi['platform_id'],
                urun_paketi['product_name'],
                urun_paketi['image_url'],
                urun_paketi['original_url'],
                urun_paketi['url_hash'],
                urun_paketi['avg_orj_score'],
                urun_paketi['status'],
                urun_paketi['last_updated_at']
            ))



            # 2. Reviews Tablosuna Toplu Kayıt
            # Senin şemanda reviews.id SERIAL olduğu için onu göndermiyoruz, DB kendisi oluşturacak.
            review_query = """
                INSERT INTO reviews (
                    product_id, original_rating, raw_text, clean_text, metadata
                ) VALUES %s
            """

            # Veriyi executemany yerine daha hızlı olan execute_values formatına getiriyoruz
            review_values = [
                (
                    y['product_id'],
                    y['original_rating'],
                    y['raw_text'],
                    y['clean_text'],
                    Json(y['metadata'])  # Python dict -> PostgreSQL JSONB
                ) for y in yorum_paketleri
            ]

            execute_values(cur, review_query, review_values)

            conn.commit()
            print(f"--- [DB BAŞARILI] --- {urun_paketi['product_name']} kaydedildi.")

        except Exception as e:
            if conn: conn.rollback()   #eğer yorum kaydederken hata çıkarsa yarım yamalak kalmasın diye tüm işlemleri geri alır(ATOMİCİTY)
            print(f"!!! [DB HATASI] !!! : {e}")
        finally:
            if conn: cur.close(); conn.close()