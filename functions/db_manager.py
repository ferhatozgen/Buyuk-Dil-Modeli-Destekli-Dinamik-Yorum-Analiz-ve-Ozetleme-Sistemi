import psycopg2
from psycopg2.extras import execute_values, Json
from psycopg2 import pool
import logging
from dotenv import load_dotenv
from contextlib import contextmanager
import os

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.config = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "sslmode": "require"
        }

        try:
            self.db_pool = pool.ThreadedConnectionPool(1, 10, **self.config)
            print("Veritabanı bağlantı havuzu başarıyla oluşturuldu.")
        except Exception as e:
            print(f"Veritabanı bağlantı havuzu oluşturulurken hata: {e}")
            raise

    @contextmanager
    def get_connection(self):
        conn = self.db_pool.getconn()
        try:
            yield conn
        finally:
            self.db_pool.putconn(conn)

    def close_pool(self):
        if self.db_pool:
            self.db_pool.closeall()
            print("Veritabanı bağlantı havuzu kapatıldı.")

    def save_product_and_reviews(self, urun_paketi, yorum_paketleri):
        try:
            with self.get_connection() as conn:
                try:
                    with conn.cursor() as cur:
                        # 1. Products Tablosuna Kayıt ve GERÇEK ID'yi Alma
                        # RETURNING id ekledik, çünkü ürün zaten varsa DB'deki gerçek UUID'yi almamız lazım.
                        product_query = """
                        INSERT INTO products (
                            id, platform, platform_id, product_name, image_url, category,
                            original_url, url_hash, avg_orj_score, status, last_updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (url_hash) DO UPDATE SET         
                            avg_orj_score = EXCLUDED.avg_orj_score,
                            category = EXCLUDED.category, -- Kategori değişmişse günceller
                            last_updated_at = CURRENT_TIMESTAMP,
                            status = 'active'
                        RETURNING id; 
                    """

                        cur.execute(product_query, (
                            urun_paketi['id'], urun_paketi['platform'], urun_paketi['platform_id'],
                            urun_paketi['product_name'], urun_paketi['image_url'], urun_paketi['category'],
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
                                product_id, original_rating, rating_int, raw_text, clean_text, metadata
                            ) VALUES %s
                        """

                        review_values = [
                            (
                                db_actual_id,  # Transformer'dan gelen değil, DB'den aldığımız ID'yi kullanıyoruz!
                                y['original_rating'],
                                y["rating_int"],
                                y['raw_text'],
                                y['clean_text'],
                                Json(y['metadata'])
                            ) for y in yorum_paketleri
                        ]

                        execute_values(cur, review_query, review_values)

                        conn.commit()
                        print(f"--- [DB BAŞARILI] --- {urun_paketi['product_name']} kaydedildi.")
                except Exception as inner_e:
                    conn.rollback()
                    raise inner_e

        except Exception as e:
            raise Exception(f"Veritabanı kayıt hatası: {e}")

    def is_exist_in_db(self, url_hash: str) -> bool:
        query = "SELECT EXISTS (SELECT 1 FROM products WHERE url_hash = %s);"
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (url_hash,))
                    return cur.fetchone()[0]
        except Exception as e:
            print(f"Veritabanı kontrol hatası: {e}")
            return False

