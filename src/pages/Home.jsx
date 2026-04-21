import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import botImage from '../assets/ai-review-bot.png';

function Home() {

    const [activeAnalysis, setActiveAnalysis] = useState(null);

    const trends = [
        {
            id: 1,
            name: "iPhone 15 Pro",
            platform: "Trendyol",
            score: "4.8",
            summary: "12.450 yorum analizi: Titanyum kasa beğenildi, batarya performansı sorgulanıyor.",
            aiDetail: "Kullanıcıların %85'i titanyum malzemenin hafifliğini 'devrimsel' olarak nitelendiriyor. Ancak %12'lik bir kesim yoğun kullanımda ısınma bildirmiş. Genel kanı: Premium bir deneyim sunuyor.",
            tags: ["Elektronik", "Hızlı Teslimat"]
        },
        {
            id: 2,
            name: "Elden Ring: Shadow of the Erdtree",
            platform: "Steam",
            score: "4.9",
            summary: "Binlerce oyuncu yorumu: Zorluk seviyesi yüksek ancak atmosfer büyüleyici.",
            aiDetail: "Sanatsal tasarım ve boss mekanikleri tam puan aldı. Zorluk seviyesi 'Soulslike' türünün zirvesi olarak görülüyor. Teknik tarafta kare hızı (FPS) stabilitesi en çok övülen detay.",
            tags: ["Aksiyon", "RPG"]
        },
        {
            id: 3,
            name: "Antalya Kaş Apart",
            platform: "Airbnb",
            score: "4.2",
            summary: "Konum ve manzara tam puan aldı. Temizlik konusunda birkaç geri bildirim mevcut.",
            aiDetail: "Lokasyon verimliliği 10/10. Son 3 ayda temizlik şikayetlerinde %40 azalma gözlemlendi. Ev sahibinin iletişim hızı kullanıcı memnuniyetini doğrudan artıran ana faktör.",
            tags: ["Konaklama", "Süper Ev Sahibi"]
        }
    ];

    const platforms = [
        "Trendyol", "Hepsiburada", "Airbnb", "Steam",
        "Google Maps", "Etstur", "Çiçeksepeti", "TrendyolGo"
    ];

    const toggleAnalysis = (id) => {
        setActiveAnalysis(activeAnalysis === id ? null : id);
    };

    return (
        <div className="landing-page">

            <div className="bg-glow glow-1"></div>
            <div className="bg-glow glow-2"></div>
            <div className="bg-grid"></div>


            <header className="navbar">
                <Link to="/" className="logo-wrap">
                    <div className="premium-logo-container">

                        <div className="logo-halo"></div>

                        <div className="logo-structure">

                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z" stroke="url(#paint0_linear)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                <path d="M8 9H16" stroke="white" strokeWidth="2" strokeLinecap="round" />
                                <path d="M8 13H13" stroke="white" strokeWidth="2" strokeLinecap="round" />
                                <circle cx="17.5" cy="12.5" r="2" fill="#ec4899" className="pulse-dot" />
                                <defs>
                                    <linearGradient id="paint0_linear" x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
                                        <stop stopColor="#a855f7" />
                                        <stop offset="1" stopColor="#ec4899" />
                                    </linearGradient>
                                </defs>
                            </svg>
                        </div>
                    </div>

                    <div className="project-title-group">
                        <div className="brand-primary">
                            Vivid<span className="brand-accent">AI</span>
                        </div>
                        <div className="brand-slogan">Yapay Zeka Analiz Motoru</div>
                    </div>
                </Link>

                <nav className="menu">
                    <a href="#trends">Trendler</a>
                    <a href="#features">Özellikler</a>
                    <a href="#faq">S.S.S</a>
                </nav>
            </header>

            <main>

                <section className="hero-section hero-split">
                    <div className="hero-content-left">
                        <h1 className="hero-title text-left">
                            Binlerce yorumu saniyeler içinde <br />
                            <span className="gradient-text">
                                anlamlı verilere dönüştür.
                            </span>
                        </h1>
                        <p className="hero-text text-left">
                            Tüm platformlardaki kullanıcı yorumlarını analiz ederek
                            gerçek içgörülere ulaşın. LLM desteğiyle veriyi sadece okumayın, hissedin.
                        </p>
                        <div className="hero-actions justify-left">
                            <Link to="/login" className="primary-btn">
                                Hemen Analize Başla
                            </Link>
                        </div>

                        <div className="login-stats stats-inline">
                            <div className="login-stat">
                                <strong>1M+</strong>
                                <span>Yorum</span>
                            </div>
                            <div className="login-stat">
                                <strong>50K+</strong>
                                <span>Kullanıcı</span>
                            </div>
                            <div className="login-stat">
                                <strong>98%</strong>
                                <span>Doğruluk</span>
                            </div>
                        </div>
                    </div>

                    <div className="hero-visual-right">
                        <div className="hero-blob-glow"></div>
                        <img
                            src={botImage}
                            alt="YorumNet AI"
                            className="hero-robot-img animate-float"
                        />
                    </div>
                </section>


                <div className="trust-bar-container">
                    <div className="trust-bar-overlay left"></div>
                    <div className="trust-bar-overlay right"></div>

                    <div className="trust-marquee">
                        <div className="marquee-content">

                            {platforms.map((p, i) => (
                                <div className="platform-item" key={`p1-${i}`}>
                                    <span className="platform-dot"></span>
                                    {p}
                                </div>
                            ))}

                            {platforms.map((p, i) => (
                                <div className="platform-item" key={`p2-${i}`}>
                                    <span className="platform-dot"></span>
                                    {p}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>


                <section id="trends" className="product-section" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div className="section-head">
                        <div className="section-tag">Popüler Analizler</div>
                        <h2>Platform Bazlı Özetler</h2>
                    </div>
                    <div className="product-grid" style={{ justifyContent: 'center', width: '100%' }}>
                        {trends.map(product => (
                            <div className="product-card" key={product.id} style={{ margin: '0 auto' }}>
                                <div className="product-visual">
                                    <div className="product-chip">{product.platform}</div>
                                    <div className="visual-mock">
                                        <div className="mock-line short"></div>
                                        <div className="mock-line"></div>
                                        <div style={{ marginTop: 10, fontSize: '12px' }}>SKOR: {product.score}</div>
                                    </div>
                                </div>
                                <div className="product-content">
                                    <h3>{product.name}</h3>
                                    <p>{product.summary}</p>


                                    {activeAnalysis === product.id && (
                                        <div className="ai-insight-panel">
                                            <div className="insight-header">
                                                <span className="sparkle">✨</span> AI DERİN ANALİZ
                                            </div>
                                            <p>{product.aiDetail}</p>
                                        </div>
                                    )}

                                    <div className="mini-tags">
                                        {product.tags.map(tag => <span key={tag}>#{tag}</span>)}
                                    </div>

                                    <button
                                        className="secondary-btn-small"
                                        onClick={() => toggleAnalysis(product.id)}
                                    >
                                        {activeAnalysis === product.id ? "Kapat" : "Detaylı Analiz →"}
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>


                <section id="features" className="feature-section" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div className="section-head">
                        <div className="section-tag">Nasıl Çalışır?</div>
                        <h2>3 Adımda Sonuca Ulaş</h2>
                        <p style={{ marginTop: '10px', color: 'var(--muted)' }}>
                            VividAİ, karmaşık verileri saniyeler içinde sizin için analiz eder.
                        </p>
                    </div>

                    <div className="feature-grid" style={{ justifyContent: 'center', width: '100%' }}>
                        <div className="feature-card">
                            <div className="feature-icon purple">01</div>
                            <h3>Linki Yapıştır</h3>
                            <p>Trendyol, Amazon veya Steam ürün linkini kopyalayıp sisteme ekleyin.</p>
                        </div>

                        <div className="feature-card">
                            <div className="feature-icon pink">02</div>
                            <h3>AI İşlesin</h3>
                            <p>LLM modellerimiz yorumları süzgeçten geçirip en önemli noktaları belirlesin.</p>
                        </div>

                        <div className="feature-card">
                            <div className="feature-icon blue">03</div>
                            <h3>Özeti Gör</h3>
                            <p>Karmaşa yerine; net skorlar ve raporlarını saniyeler içinde alın.</p>
                        </div>
                    </div>
                </section>


                <section id="faq" className="feature-section" style={{ paddingBottom: '100px' }}>
                    <div className="section-head">
                        <div className="section-tag">Destek</div>
                        <h2>Sıkça Sorulan Sorular</h2>
                    </div>
                    <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                        {[
                            { q: "Hangi platformları destekliyor?", a: "Trendyol, Amazon, Steam, Airbnb ve Google Maps dahil 10+ platformu destekliyoruz." },
                            { q: "Yorumları nasıl analiz ediyorsunuz?", a: "En güncel Büyük Dil Modellerini (LLM) kullanarak metinlerdeki anlam ve duygu tonunu ayrıştırıyoruz." },
                            { q: "Veriler gerçek zamanlı mı?", a: "Evet, siz linki yapıştırdığınız an platformdaki en güncel yorumlar taranır." }
                        ].map((item, index) => (
                            <div key={index} className="feature-card" style={{ padding: '20px', textAlign: 'left' }}>
                                <h4 style={{ color: 'var(--purple)', marginBottom: '10px' }}>{item.q}</h4>
                                <p style={{ fontSize: '14px' }}>{item.a}</p>
                            </div>
                        ))}
                    </div>
                </section>


                <section className="cta-section-modern">
                    <div className="cta-container">

                        <div className="cta-ring ring-1"></div>
                        <div className="cta-ring ring-2"></div>

                        <div className="cta-glass-card">
                            <div className="section-tag">Hemen Başla</div>
                            <h2 className="cta-heading">
                                Yorumları analiz etmeye <br />
                                <span className="gradient-text">hazır mısın?</span>
                            </h2>
                            <p className="cta-subtext">
                                Binlerce kullanıcı deneyimini saniyeler içinde analiz edin.
                                Karmaşayı netliğe dönüştürmek için sadece bir adım kaldı.
                            </p>

                            <div className="cta-button-wrapper">
                                <Link to="/login" className="primary-btn-premium">
                                    <span className="btn-text">Analize Şimdi Başla</span>
                                    <span className="btn-glow"></span>
                                </Link>
                            </div>

                            <div className="cta-features-mini">
                                <span>✦ Ücretsiz Kullanım</span>
                                <span>✦ 10+ Platform Desteği</span>
                                <span>✦ LLM Analiz Gücü</span>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <footer style={{ textAlign: 'center', padding: '60px 0', opacity: 0.4 }}>
                © 2026 VividAİ - Smart Review Engine
            </footer>
        </div>
    );
}

export default Home;