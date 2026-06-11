import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';

function Register() {
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: ''
    });
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');

        // 1. E-POSTA FORMAT KONTROLÜ (Regex ile)
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(formData.email)) {
            setError('Lütfen geçerli bir e-posta adresi girin (örn: isim@sirket.com).');
            return; // Hata varsa işlemi durdur ve backend'e gitme
        }

        // 2. ŞİFRE GÜVENLİK KONTROLLERİ
        if (formData.password.length < 6) {
            setError('Şifreniz en az 6 karakter uzunluğunda olmalıdır.');
            return;
        }
        if (!/[A-Z]/.test(formData.password)) {
            setError('Şifreniz en az bir büyük harf içermelidir.');
            return;
        }
        if (!/[0-9]/.test(formData.password)) {
            setError('Şifreniz en az bir rakam içermelidir.');
            return;
        }
        // İstersen özel karakter zorunluluğu da ekleyebilirsin:
        // if (!/[!@#$%^&*]/.test(formData.password)) {
        //     setError('Şifreniz en az bir özel karakter (!@#$%) içermelidir.');
        //     return;
        // }

        setIsLoading(true);

        try {
            await api.post('/Auth/register', formData);
            navigate('/login', { state: { message: "Kayıt başarıyla tamamlandı! Şimdi giriş yapabilirsiniz." } });
        } catch (err) {
            console.error("Kayıt hatası:", err);
            setError(err.response?.data?.message || 'Kayıt başarısız. Lütfen bilgileri kontrol edin.');
        } finally {
            setIsLoading(false);
        }
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
                            <p>VividAI deneyimine başlamak için kayıt ol.</p>
                        </header>

                        <form onSubmit={handleRegister} className="auth-form">
                            <div className="input-field">
                                <label>Kullanıcı Adı</label>
                                <input
                                    type="text"
                                    placeholder="Kullanıcı adınız"
                                    required
                                    value={formData.username}
                                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                />
                            </div>

                            <div className="input-field">
                                <label>E-posta Adresi</label>
                                <input
                                    type="text" // 'email' yerine 'text' yaptık ki tarayıcı varsayılanı yerine bizim hatamız görünsün
                                    placeholder="isim@sirket.com"
                                    required
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                />
                            </div>

                            <div className="input-field">
                                <label>Şifre</label>
                                <input
                                    type="password"
                                    placeholder="••••••••"
                                    required
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                />
                            </div>

                            {/* HATA MESAJI BURADA GÖSTERİLİYOR */}
                            {error && (
                                <div style={{
                                    backgroundColor: '#fee2e2',
                                    color: '#ef4444',
                                    padding: '10px',
                                    borderRadius: '6px',
                                    fontSize: '13px',
                                    marginBottom: '15px',
                                    border: '1px solid #f87171'
                                }}>
                                    {error}
                                </div>
                            )}

                            <button type="submit" className="auth-submit-btn" disabled={isLoading}>
                                {isLoading ? 'Kaydediliyor...' : 'Kaydol'}
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