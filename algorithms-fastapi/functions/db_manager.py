import psycopg2
from psycopg2.extras import execute_values, Json
from psycopg2 import pool
import logging
from dotenv import load_dotenv
from contextlib import contextmanager
import os

load_dotenv()

class DatabaseManager:
    # Sınıf seviyesinde havuz değişkeni (Uygulama boyunca tek 1 tane olacak)
    _db_pool = None

    def __init__(self):
        self.config = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "sslmode": "require"
        }

        # Eğer havuz daha önce oluşturulmamışsa OLUŞTUR
        if DatabaseManager._db_pool is None:
            try:
                DatabaseManager._db_pool = pool.ThreadedConnectionPool(1, 20, **self.config)
                print(" Veritabanı bağlantı havuzu 1 kez oluşturuldu ve hafızaya alındı.")
            except Exception as e:
                print(f" Veritabanı bağlantı havuzu oluşturulurken hata: {e}")
                raise

    @contextmanager
    def get_connection(self):
        # Bağlantıyı sınıf seviyesindeki (_db_pool) havuzdan çek
        conn = DatabaseManager._db_pool.getconn()
        try:
            yield conn
        finally:
            # Bağlantıyı kapatma, havuza geri bırak!
            DatabaseManager._db_pool.putconn(conn)

    @classmethod
    def close_pool(cls):
        # Sınıf metoduna çevirdik, sadece sunucu kapanırken çağrılacak
        if cls._db_pool:
            cls._db_pool.closeall()
            print(" Veritabanı bağlantı havuzu tamamen kapatıldı.")

    def fetch_data(self, query):
        import pandas as pd
        with self.get_connection() as conn:
            return pd.read_sql(query, conn)

    #  BURADAN İTİBAREN TÜM METOTLAR İÇERİ ALINDI
    def save_product_and_reviews(self, urun_paketi, yorum_paketleri):
        try:
            with self.get_connection() as conn:
                try:
                    with conn.cursor() as cur:
                        # 1. Products Tablosuna Kayıt ve GERÇEK ID'yi Alma
                        product_query = """
                            INSERT INTO products (
                                id, platform, platform_id, product_name, image_url, category,
                                original_url, url_hash, avg_orj_score, avg_model_score, celiski_score, status, last_updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (url_hash) DO UPDATE SET         
                                avg_orj_score = EXCLUDED.avg_orj_score,
                                avg_model_score = EXCLUDED.avg_model_score,
                                category = EXCLUDED.category,
                                celiski_score = EXCLUDED.celiski_score,
                                last_updated_at = CURRENT_TIMESTAMP,
                                status = 'active'
                            RETURNING id; 
                        """

                        cur.execute(product_query, (
                            urun_paketi['id'], urun_paketi['platform'], urun_paketi['platform_id'],
                            urun_paketi['product_name'], urun_paketi['image_url'], urun_paketi['category'],
                            urun_paketi['original_url'], urun_paketi['url_hash'],
                            urun_paketi['avg_orj_score'], urun_paketi['avg_model_score'], urun_paketi["celiski_score"], urun_paketi['status'],
                            urun_paketi['last_updated_at']
                        ))

                        db_actual_id = cur.fetchone()[0]

                        # 2. Eski Yorumları Temizleme
                        cur.execute("DELETE FROM reviews WHERE product_id = %s", (db_actual_id,))

                        # 3. Reviews Tablosuna Toplu Kayıt
                        review_query = """
                                INSERT INTO reviews (
                                    product_id, original_rating, rating_int, predicted_score, raw_text, clean_text, metadata, reviewed_at, is_summarized
                                ) VALUES %s
                            """
                        seen_reviews = set()
                        review_values = []

                        for y in yorum_paketleri:
                            ham_metin = y['raw_text'].strip() if y['raw_text'] else ""
                            puan = y['original_rating']

                            review_key = (ham_metin, puan)

                            if review_key not in seen_reviews and ham_metin != "":
                                seen_reviews.add(review_key)
                                review_values.append((
                                    db_actual_id,
                                    puan,
                                    y["rating_int"],
                                    y['predicted_score'],
                                    y['raw_text'],
                                    y['clean_text'],
                                    Json(y['metadata']),
                                    y['reviewed_at'],
                                    y['is_summarized']
                                ))

                        # Sadece tekil olan temiz listeyi tek kalemde veritabanına fırlatıyoruz
                        if review_values:
                            execute_values(cur, review_query, review_values)

                        conn.commit()
                        print(f"--- [DB BAŞARILI] --- {urun_paketi['product_name']} kaydedildi.")
                        return db_actual_id
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

    def fetch_query(self, query, params=None):
        """Veritabanından veri çekmek (SELECT) için kullanılır."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    return cur.fetchall()  # vtden dönen satırları [("..", "...")]  list of tupples olarak getirir.
        except Exception as e:
            print(f"Veri çekme hatası: {e}")
            return []

    def execute_query(self, query, params=None):
        """Veritabanında güncelleme (UPDATE, DELETE, INSERT) yapmak için kullanılır."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    conn.commit()
        except Exception as e:
            print(f"Sorgu çalıştırma hatası: {e}")
            raise e

    def get_unscored_data_by_produc_id(self, product_id):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = "Select id, clean_text FROM reviews WHERE product_id = %s"
                    cur.execute(query, (product_id,))
                    rows = cur.fetchall()

                    yorum_paketleri = []
                    for row in rows:
                        yorum_paketleri.append({
                            "db_review_id": row[0],
                            "clean_text": row[1]
                        })

                    return yorum_paketleri
        except Exception as e:
            print(f"Ham yorumlar çekilirken hata: {e}")
            return []

    def update_scores(self, product_id, avg_model_score, yorum_paketleri):
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if avg_model_score is not None:
                        cur.execute(
                            "UPDATE products SET avg_model_score = %s WHERE id = %s",
                            (avg_model_score, product_id)
                        )

                    update_query = "UPDATE reviews SET predicted_score = %s WHERE id = %s"
                    review_data = [(y.get('predicted_score'), y.get('db_review_id')) for y in yorum_paketleri if y.get('predicted_score') is not None]

                    from psycopg2.extras import execute_batch
                    execute_batch(cur, update_query, review_data)

                    conn.commit()
        except Exception as e:
            raise Exception(f"Puanlar güncellenirken hata: {e}")

    def save_summary_and_get_id(self, product_id, summary_type, category_name, summary_text, average_score):
        """
        Özeti product_summaries tablosuna kaydeder ve oluşturulan yeni UUID'yi döndürür.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        INSERT INTO product_summaries (product_id, summary_type, category_name, summary_text, average_score) 
                        VALUES (%s, %s, %s, %s, %s) RETURNING id;
                    """
                    cur.execute(query, (product_id, summary_type, category_name, summary_text, average_score))
                    summary_id = cur.fetchone()[0]
                    conn.commit()

                    return summary_id
        except Exception as e:
            print(f"[ERROR] Özet veritabanına kaydedilirken hata oluştu: {e}")
            return None

    def save_summary_source_reviews(self, iliskiler):
        """
        Hangi özetin hangi yorumlardan oluştuğunu eşleşme tablosuna (summary_source_reviews) toplu olarak yazar.
        iliskiler formatı: [(summary_id, review_id), (summary_id, review_id), ...]
        """
        if not iliskiler:
            return

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = "INSERT INTO summary_source_reviews (summary_id, review_id) VALUES %s"
                    execute_values(cur, query, iliskiler)
                    conn.commit()
        except Exception as e:
            print(f"[ERROR] Özet-Yorum ilişkileri kaydedilirken hata oluştu: {e}")

    def save_review_aspects(self, final_aspects):
        """
        Qwen modelinden dönen ve puanlanan parçaları (aspects) toplu olarak veritabanına yazar.
        final_aspects formatı: [{"review_id": ..., "category_name": ..., "snippet_text": ..., "snippet_score": ...}]
        """
        if not final_aspects:
            return

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        INSERT INTO review_aspects (review_id, category_name, snippet_text, snippet_score)
                        VALUES %s
                    """
                    # Sözlük listesini, execute_values'un okuyabileceği tuple listesine çeviriyoruz
                    values = [
                        (item["review_id"], item["category_name"], item["snippet_text"], item["snippet_score"])
                        for item in final_aspects
                    ]

                    execute_values(cur, query, values)
                    conn.commit()
        except Exception as e:
            print(f"[ERROR] Review aspects kaydedilirken hata oluştu: {e}")
