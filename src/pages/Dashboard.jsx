import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import './Dashboard.css';

function Dashboard() {
    const [url, setUrl] = useState('');
    const [selected, setSelected] = useState(null);
    const [loading, setLoading] = useState(false);
    const [userRating, setUserRating] = useState(0);
    const [hasRated, setHasRated] = useState(false);
    const navigate = useNavigate();

    const platforms = ["Trendyol", "Amazon", "Steam", "Hepsiburada", "Airbnb", "Google Maps", "Yemeksepeti"];

    const trends = [
        {
            id: 1,
            name: "Sony WH-1000XM5",
            plat: "Amazon",
            avgScore: 4.8,
            sum: "Sektör lideri ANC ve ses netliği ile premium bir deneyim sunuyor.",
            img: "https://picsum.photos/seed/sony_final/800/500",
            categories: [
                { title: "Ses Kalitesi", comment: "Baslar derin, tizler net. Odyofiller için tatmin edici." },
                { title: "ANC Gücü", comment: "Dış dünyayı tamamen kapatıyor, odaklanma için ideal." },
                { title: "Konfor", comment: "Yumuşak deri pedler uzun kullanımda bile rahatsız etmiyor." },
                { title: "Mikrofon", comment: "Gürültülü ortamlarda bile ses iletimi pürüzsüz." }
            ]
        },
        {
            id: 2,
            name: "iPhone 15 Pro",
            plat: "Trendyol",
            avgScore: 4.6,
            sum: "Titanyum kasa ve yeni A17 çipi ile performansın zirvesinde.",
            img: "https://picsum.photos/seed/iphone_final/800/500",
            categories: [
                { title: "Kamera", comment: "Gece çekimleri ve sinematik mod rakipsiz." },
                { title: "Ekran", comment: "ProMotion teknolojisi ile her şey akıcı." },
                { title: "Batarya", comment: "Yoğun kullanımda bir günü rahatça çıkarıyor." },
                { title: "Tasarım", comment: "Titanyum çerçeve hem hafif hem de çok şık." }
            ]
        },
        {
            id: 3,
            name: "Elden Ring: Shadow",
            plat: "Steam",
            avgScore: 4.9,
            sum: "Açık dünya tasarımında yeni bir standart, sanat eseri niteliğinde.",
            img: "https://picsum.photos/seed/elden_final/800/500",
            categories: [
                { title: "Oynanış", comment: "Boss savaşları ve mekanikler kusursuz işliyor." },
                { title: "Atmosfer", comment: "Dünyanın gizemi oyuncuyu içine hapsediyor." },
                { title: "Sanat", comment: "Görsel tasarım her sahnede büyüleyici." },
                { title: "Zorluk", comment: "Zorlayıcı ama ödüllendirici bir deneyim." }
            ]
        }
    ];

    const handleAnalyze = () => {
        if (!url) return;
        setLoading(true);
        setSelected(null);
        setHasRated(false);
        setUserRating(0);
        setTimeout(() => {
            setLoading(false);
            setSelected(trends[0]);
        }, 1800);
    };

    const handleRating = (rate) => {
        if (hasRated) return;
        setUserRating(rate);
        setHasRated(true);
    };

    const selectTrend = (item) => {
        setSelected(item);
        setHasRated(false);
        setUserRating(0);
    };

    return (
        <div className="modern-root">
            {/* ARKA PLANDAKİ BEYAZ ÇİZGİLER VE IŞIKLAR */}
            <div className="bg-grid"></div>
            <div className="bg-glow glow-1"></div>
            <div className="bg-glow glow-2"></div>

            <header className="modern-nav">
                {/* --- HOME SAYFASINDAKİ LOGONUN BİREBİR AYNISI --- */}
                <Link to="/" className="logo-wrap" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', zIndex: 100 }}>
                    <div className="premium-logo-container">
                        <div className="logo-halo"></div>
                        <div className="logo-structure">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z" stroke="url(#paint0_linear_dash)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                <path d="M8 9H16" stroke="white" strokeWidth="2" strokeLinecap="round" />
                                <path d="M8 13H13" stroke="white" strokeWidth="2" strokeLinecap="round" />
                                <circle cx="17.5" cy="12.5" r="2" fill="#ec4899" className="pulse-dot" />
                                <defs>
                                    <linearGradient id="paint0_linear_dash" x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
                                        <stop stopColor="#60a5fa" />
                                        <stop offset="1" stopColor="#a21d74" />
                                    </linearGradient>
                                </defs>
                            </svg>
                        </div>
                    </div>

                    <div className="project-title-group" style={{ marginLeft: '12px' }}>
                        <div className="brand-primary" style={{ fontSize: '26px', fontWeight: '900', color: '#cbd5e1' }}>
                            Vivid<span className="brand-accent" style={{
                                background: 'linear-gradient(90deg, #60a5fa, #a21d74)',
                                WebkitBackgroundClip: 'text',
                                WebkitTextFillColor: 'transparent',
                                textShadow: '0 0 10px rgba(96, 165, 250, 0.5)'
                            }}>AI</span>
                        </div>
                        <div className="brand-slogan" style={{ fontSize: '10px', color: '#9ca3af', letterSpacing: '1px', textTransform: 'uppercase', marginTop: '2px' }}>
                            Yapay Zeka Analiz Motoru
                        </div>
                    </div>
                </Link>

                <div className="nav-right">
                    <div className="user-pill">
                        <img src="https://ui-avatars.com/api/?name=Nisanur&background=a855f7&color=fff" alt="Nisanur" />
                        <span>Nisanur Cebecioğlu</span>
                    </div>
                    <button className="logout-btn-v11" onClick={() => navigate('/')}>
                        Çıkış Yap
                    </button>
                </div>
            </header>

            <main className="main-grid" style={{ position: 'relative', zIndex: 10 }}>
                <aside className="panel-glass side-panel">
                    <div className="panel-tag">TREND ANALİZLER</div>
                    <div className="trend-list-scroll">
                        {trends.map((t, index) => (
                            <div
                                key={t.id}
                                className="trend-card-v10 animated-card"
                                style={{ animationDelay: `${index * 0.1}s` }}
                                onClick={() => selectTrend(t)}
                            >
                                <div className="tc-img"><img src={t.img} alt="" /></div>
                                <div className="tc-info">
                                    <h4>{t.name}</h4>
                                    <small>{t.plat}</small>
                                </div>
                                <div className="tc-score">★{t.avgScore}</div>
                            </div>
                        ))}
                    </div>
                </aside>

                <section className="panel-glass report-view">
                    {selected ? (
                        <div className="report-container fade-in">
                            <div className="report-header">
                                <h2>
                                    {selected.name}
                                    <span className="plat-badge">{selected.plat} Ürünü</span>
                                </h2>
                                <div className="rating-area">
                                    {hasRated ? (
                                        <div className="thanks-msg">
                                            ✓ Puanınız Başarıyla Kaydedildi
                                        </div>
                                    ) : (
                                        <div className="user-rate-box">
                                            <span>Değerlendir:</span>
                                            <div className="stars">
                                                {[1, 2, 3, 4, 5].map((s) => (
                                                    <span
                                                        key={s}
                                                        className={userRating >= s ? "star active" : "star"}
                                                        onClick={() => handleRating(s)}
                                                    >★</span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="report-visual">
                                <img src={selected.img} alt={selected.name} />
                            </div>

                            <div className="report-summary">
                                <label>✦ ANALİZ ÖZETİ</label>
                                <p>{selected.sum}</p>
                            </div>

                            <div className="category-analysis">
                                {selected.categories.map((cat, i) => (
                                    <div key={i} className="cat-card">
                                        <h5>{cat.title}</h5>
                                        <p>{cat.comment}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="empty-state">
                            <div className="pulse-icon">✦</div>
                            <h3>{loading ? "Analiz Başlatıldı" : "Ürün Bekleniyor"}</h3>
                            <p>{loading ? "Yapay zeka verileri işliyor..." : "Trendlerden birini seçin veya link yapıştırın."}</p>
                        </div>
                    )}
                </section>
            </main>

            <footer className="footer-zone" style={{ position: 'relative', zIndex: 10 }}>
                <div className="marquee-container">
                    <div className="marquee-content">
                        {[...platforms, ...platforms].map((p, i) => <span key={i}>{p}</span>)}
                    </div>
                </div>
                <div className="input-wrapper">
                    <input
                        placeholder="Analiz için ürün linkini buraya bırakın..."
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                    />
                    <button className="btn-primary" onClick={handleAnalyze}>
                        {loading ? <div className="spinner"></div> : "Analiz Et"}
                    </button>
                </div>
            </footer>
        </div>
    );
}

export default Dashboard;