import os
import uuid
import bcrypt
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Kendi db_manager'ını import ediyoruz
from functions.db_manager import DatabaseManager

def create_admin_user():
    print("--- 🔐 Manuel Kullanıcı (Admin) Ekleme Aracı ---")
    username = input("Kullanıcı Adı: ")
    email = input("E-Posta: ")
    plain_password = input("Şifre: ")

    # 1. Şifreyi BCrypt ile Hashle (C# standartlarına uygun olarak)
    # NOT: Eğer C# tarafında BCrypt yerine PBKDF2 veya SHA256 kullanıldıysa burası değişmelidir.
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')

    db = DatabaseManager()

    try:
        # C# tarafı ID'leri Guid (UUID) olarak tuttuğu için yeni bir UUID üretiyoruz
        user_id = str(uuid.uuid4())

        # 2. Veritabanına Kayıt
        # DİKKAT: 'users' tablo adını ve sütun adlarını kendi veritabanı şemana göre güncelle!
        sorgu = """
            INSERT INTO users (id, username, email, password_hash, created_at) 
            VALUES (%s, %s, %s, %s, %s)
        """

        # db_manager içindeki execute metodunu kullanıyoruz
        # (metodun adı execute_query veya farklıysa kendi yapınıza göre düzelt)
        db.execute_query(sorgu, (user_id, username, email, hashed_password, datetime.now()))

        print(f"\n✅ Kullanıcı başarıyla oluşturuldu!")
        print(f"ID: {user_id}")
        print(f"Email: {email}")
        print("Artık bu bilgilerle React frontend üzerinden giriş yapıp JWT alabilirsin.")

    except Exception as e:
        print(f"\n❌ Veritabanına kayıt sırasında hata oluştu: {e}")
    finally:
        # Veritabanı bağlantısını kapatmayı unutmuyoruz
        db.close_pool()

if __name__ == "__main__":
    create_admin_user()