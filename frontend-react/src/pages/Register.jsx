import React, { useState } from 'react';
import { Link } from 'react-router-dom';

function Register() {
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: ''
    });
    const [error, setError] = useState('');

    // Input'a tıklandığında veya harf yazılmaya çalışıldığında tetiklenecek fonksiyon
    const handleInteraction = () => {
        setError('⚠️ Kayıt işlemleri şu an için kapalıdır. Sistem sadece yetkili kullanıcılara açıktır.');
    };

    // Form gönderilmeye (butona basılmaya) çalışıldığında tetiklenecek fonksiyon
    const handleRegister = (e) => {
        e.preventDefault(); // Sayfanın yenilenmesini engeller
        handleInteraction(); // Hata mesajını gösterir
    };

    return (
        <div className="modern-auth-wrapper">
            <div className="auth-academic-banner">
                BU BİR AKADEMİK ÇALIŞMADIR - SADECE YETKİLİ KULLANICILAR İÇİN ERİŞİME AÇIKTIR
            </div>
            <div className="ambient-light light-purple"></div>
            <div className="ambient-light light-blue"></div>

            <div className="auth-container" style={{ height: 'auto', minHeight: '550px' }}>
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
                    <div className="form-content" style={{ paddingBottom: '20px' }}>
                        <header style={{ marginBottom: '20px' }}>
                            <Link to="/" className="back-button">
                                <span>←</span> Ana Sayfaya Dön
                            </Link>
                            <h2>Hesap Oluştur</h2>
                            <p>YorumAnaliz deneyimine başlamak için kayıt ol.</p>
                        </header>

                        <form onSubmit={handleRegister} className="auth-form">
                            <div className="input-field" style={{ marginBottom: '14px' }}>
                                <label>Kullanıcı Adı</label>
                                <input
                                    type="text"
                                    placeholder="Kullanıcı adınız"
                                    value={formData.username}
                                    onFocus={handleInteraction}
                                    onChange={(e) => {
                                        setFormData({ ...formData, username: e.target.value });
                                        handleInteraction();
                                    }}
                                />
                            </div>

                            <div className="input-field" style={{ marginBottom: '14px' }}>
                                <label>E-posta Adresi</label>
                                <input
                                    type="text"
                                    placeholder="isim@sirket.com"
                                    value={formData.email}
                                    onFocus={handleInteraction}
                                    onChange={(e) => {
                                        setFormData({ ...formData, email: e.target.value });
                                        handleInteraction();
                                    }}
                                />
                            </div>

                            <div className="input-field" style={{ marginBottom: '14px' }}>
                                <label>Şifre</label>
                                <input
                                    type="password"
                                    placeholder="••••••••"
                                    value={formData.password}
                                    onFocus={handleInteraction}
                                    onChange={(e) => {
                                        setFormData({ ...formData, password: e.target.value });
                                        handleInteraction();
                                    }}
                                />
                            </div>

                            {/* UYARI / HATA MESAJI (Daha kompakt hale getirildi) */}
                            <div style={{ minHeight: '48px', marginBottom: '8px' }}>
                                {error && (
                                    <div style={{
                                        backgroundColor: '#fef2f2',
                                        color: '#dc2626',
                                        padding: '8px 12px',
                                        borderRadius: '8px',
                                        fontSize: '12.5px',
                                        fontWeight: '500',
                                        border: '1px solid #fca5a5',
                                        lineHeight: '1.4'
                                    }}>
                                        {error}
                                    </div>
                                )}
                            </div>

                            <button type="submit" className="auth-submit-btn" style={{ marginTop: '0' }}>
                                Kaydol
                            </button>
                        </form>

                        <footer style={{ marginTop: '20px' }}>
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