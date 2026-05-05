from functions.db_manager import DatabaseManager
from functions.utils import ciceksepeti_kategori_hibrit
from functions.logger import setup_logger

logger = setup_logger()

def migrate_ciceksepeti_categories():
    db = DatabaseManager()

    try:
        # 1. Tüm Çiçeksepeti ürünlerini çek
        logger.info(" Çiçeksepeti ürünleri veritabanından çekiliyor...")
        # Sadece ciceksepeti platformuna ait id ve isimleri alıyoruz
        products = db.fetch_query("SELECT id, product_name FROM products WHERE platform = 'ciceksepeti'")

        if not products:
            logger.warning(" Güncellenecek ürün bulunamadı.")
            return

        logger.info(f"📂 Toplam {len(products)} ürün bulundu. Güncelleme başlıyor...")

        updated_count = 0
        for p_id, p_name in products:
            # 2. Hibrit fonksiyonu çalıştır ve yeni kategoriyi belirle
            yeni_kategori = ciceksepeti_kategori_hibrit(p_name)

            # 3. Veritabanını güncelle
            db.execute_query(
                "UPDATE products SET category = %s WHERE id = %s",
                (yeni_kategori, p_id)
            )

            updated_count += 1
            if updated_count % 50 == 0:
                logger.info(f"✅ {updated_count}/{len(products)} ürün güncellendi...")

        logger.info(f"🎉 İşlem tamamlandı! {updated_count} ürünün kategorisi hibrit modelle düzeltildi.")

    except Exception as e:
        logger.error(f" Güncelleme sırasında hata oluştu: {e}")
    finally:
        db.close_pool()  # Bağlantıları kapatmayı unutma


if __name__ == "__main__":
    migrate_ciceksepeti_categories()