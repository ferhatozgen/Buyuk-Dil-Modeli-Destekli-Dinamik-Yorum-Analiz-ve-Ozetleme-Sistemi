import React from 'react';
import { Link, useNavigate } from 'react-router-dom';

function Login() {
    const navigate = useNavigate();

    const handleLogin = (e) => {
        e.preventDefault();
        navigate('/dashboard');
    };

    return (
        <div className="modern-auth-wrapper">
            {/* Arka planda yumuşak ışık oyunları */}
            <div className="ambient-light light-purple"></div>
            <div className="ambient-light light-blue"></div>
            <div className="bg-mesh"></div>

            <div className="auth-container">
                <div className="auth-visual-side">
                    {/* Görsel tarafta sanatsal bir dokunuş */}
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

                        <form onSubmit={handleLogin} className="auth-form">
                            <div className="input-field">
                                <label>E-posta Adresi</label>
                                <input type="email" placeholder="isim@sirket.com" required />
                            </div>

                            <div className="input-field">
                                <div className="label-row">
                                    <label>Şifre</label>

                                </div>
                                <input type="password" placeholder="••••••••" required />
                            </div>

                            <button type="submit" className="auth-submit-btn">
                                Giriş Yap
                            </button>
                        </form>


                        <footer>
                            <span>Hesabınız yok mu?</span>
                            {/* Link etiketini kullanarak /register sayfasına yönlendiriyoruz */}
                            <Link to="/register" className="signup-link">Hemen Kaydolun</Link>
                        </footer>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Login;