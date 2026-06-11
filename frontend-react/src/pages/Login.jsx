import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import api from '../api';

function Login() {
    const navigate = useNavigate();
    const location = useLocation();

    // REGISTER'DAN GELEN MESAJI YAKALIYORUZ
    const message = location.state?.message;

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            const response = await api.post('/Auth/login', {
                email: email,
                password: password
            });

            // GİRİŞ BAŞARILIYSA TOKEN VE İSMİ KAYDEDİYORUZ
            localStorage.setItem('token', response.data.accessToken);
            localStorage.setItem('username', response.data.username);

            navigate('/dashboard');
        } catch (err) {
            console.error("Giriş hatası:", err);
            setError('Giriş başarısız. Lütfen bilgilerinizi kontrol edin.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="modern-auth-wrapper">
            <div className="ambient-light light-purple"></div>
            <div className="ambient-light light-blue"></div>
            <div className="bg-mesh"></div>

            <div className="auth-container">
                <div className="auth-visual-side">
                    <div className="visual-content">
                        <div className="abstract-shape"></div>
                    </div>
                </div>

                <div className="auth-form-side">
                    <div className="form-content">
                        <header>
                            <Link to="/" className="back-button">
                                <span>←</span> Ana Sayfaya Dön
                            </Link>
                            <h2>Hoş Geldiniz</h2>
                            <p>Sisteme erişmek için bilgilerinizi girin.</p>
                        </header>

                        {/* BAŞARI MESAJINI BURADA GÖSTERİYORUZ */}
                        {message && (
                            <div style={{ backgroundColor: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa', padding: '12px', borderRadius: '8px', marginBottom: '16px', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                                {message}
                            </div>
                        )}

                        <form onSubmit={handleLogin} className="auth-form">
                            <div className="input-field">
                                <label>E-posta Adresi</label>
                                <input
                                    type="email"
                                    placeholder="isim@sirket.com"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>

                            <div className="input-field">
                                <label>Şifre</label>
                                <input
                                    type="password"
                                    placeholder="••••••••"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>

                            {error && <p className="error-message" style={{ color: '#ef4444', fontSize: '14px', marginBottom: '10px' }}>{error}</p>}

                            <button type="submit" className="auth-submit-btn" disabled={isLoading}>
                                {isLoading ? 'Giriş Yapılıyor...' : 'Giriş Yap'}
                            </button>
                        </form>

                        <footer>
                            <span>Hesabınız yok mu?</span>
                            <Link to="/register" className="signup-link">Hemen Kaydolun</Link>
                        </footer>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Login;