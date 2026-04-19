import React from 'react';
import { Link, useNavigate } from 'react-router-dom';

function Register() {
    const navigate = useNavigate();

    const handleRegister = (e) => {
        e.preventDefault();
        // Kayıt işlemleri burada simüle edilebilir
        navigate('/login');
    };

    return (
        <div className="modern-auth-wrapper">
            <div className="ambient-light light-purple"></div>
            <div className="ambient-light light-blue"></div>

            <div className="auth-container">
                <div className="auth-visual-side">
                    <div className="visual-content">
                        <div className="abstract-shape" style={{ background: 'linear-gradient(45deg, #3b82f6, #60a5fa)' }}></div>
                        <h3 style={{ color: 'white', fontSize: '24px', fontWeight: '800' }}>Aramıza Katıl</h3>
                        <p style={{ color: 'rgba(255,255,255,0.6)', marginTop: '10px' }}>
                            Verinin gücünü keşfetmek için ilk adımı at.
                        </p>
                    </div>
                </div>

                <div className="auth-form-side">
                    <div className="form-content">
                        <header>
                            <Link to="/" className="back-button">
                                <span>←</span> Ana Sayfaya Dön
                            </Link>
                            <h2>Hesap Oluştur</h2>
                            <p>YorumNet deneyimine başlamak için kayıt ol.</p>
                        </header>

                        <form onSubmit={handleRegister} className="auth-form">
                            <div className="input-field">
                                <label>Ad Soyad</label>
                                <input type="text" placeholder="Nisanur Cebecioğlu" required />
                            </div>

                            <div className="input-field">
                                <label>E-posta Adresi</label>
                                <input type="email" placeholder="isim@sirket.com" required />
                            </div>

                            <div className="input-field">
                                <label>Şifre</label>
                                <input type="password" placeholder="••••••••" required />
                            </div>

                            <button type="submit" className="auth-submit-btn">
                                Kaydol
                            </button>
                        </form>

                        <footer>
                            <span>Zaten hesabınız var mı?</span>
                            <Link to="/login" className="signup-link">Giriş Yap</Link>
                        </footer>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Register;