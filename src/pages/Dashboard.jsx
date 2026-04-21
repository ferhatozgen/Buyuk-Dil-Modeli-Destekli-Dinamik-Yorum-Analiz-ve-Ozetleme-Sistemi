import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import './Dashboard.css';

function Dashboard() {
    const [url, setUrl] = useState('');
    const [selected, setSelected] = useState(null);
    const [loading, setLoading] = useState(false);
    const [userRating, setUserRating] = useState(0);
    const [hoverRating, setHoverRating] = useState(0);
    const [hasRated, setHasRated] = useState(false);
    const [sidebarTab, setSidebarTab] = useState('trends');
    const [favorites, setFavorites] = useState([]);

    const navigate = useNavigate();

    const trends = [
        {
            id: 1,
            name: "Sony WH-1000XM5",
            plat: "Amazon",
            avgScore: 4.8,
            sum: "Yapay zeka analizimize göre Sony WH-1000XM5, gürültü engelleme performansında rakiplerinin %15 önünde. Özellikle vokal netliği ve hafif yapısı kullanıcı yorumlarında en çok övülen noktalar.",
            img: "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?auto=format&fit=crop&w=800&q=80",
            productUrl: "https://www.amazon.com.tr",
            categories: [
                { title: "Akustik Analiz", comment: "Sanal sahne genişliği mükemmel, enstrüman ayrımı çok net." },
                { title: "Kullanıcı Konforu", comment: "Uzun süreli kullanımlarda terletme yapmadığı onaylandı." }
            ]
        },
        {
            id: 2,
            name: "iPhone 15 Pro Max",
            plat: "Trendyol",
            avgScore: 4.6,
            sum: "Titanyum kasa ve yeni A17 Pro çipi ile performansın zirvesinde. Kamera yetenekleri profesyonel seviyede.",
            img: "https://preview.redd.it/silver-just-looks-so-timeless-v0-jmgzk86qslmc1.jpeg?width=1080&crop=smart&auto=webp&s=d5e7b937141623c09b643b19cd83ae059987a5bf",
            productUrl: "https://www.trendyol.com",
            categories: [
                { title: "Kamera", comment: "Gece çekimleri ve sinematik mod rakipsiz." },
                { title: "Ekran", comment: "ProMotion teknolojisi ile her şey akıcı." }
            ]
        }
    ];

    const history = [
        {
            id: 101,
            name: "Logitech MX Master 3S",
            plat: "Hepsiburada",
            avgScore: 4.9,
            img: "https://images.unsplash.com/photo-1625773130728-190367307222?auto=format&fit=crop&w=800&q=80",
            productUrl: "#",
            sum: "Ofis kullanımı için en iyi mouse ergonomisi ve tıklama sessizliği ile öne çıkıyor.",
            categories: [{ title: "Ergonomi", comment: "Bilek desteği mükemmel seviyede." }]
        }
    ];

    const platforms = ["Trendyol", "Hepsiburada", "Airbnb", "Steam",
        "Google Maps", "Etstur", "Çiçeksepeti", "TrendyolGo"];

    const handleAnalyze = () => {
        if (!url) return;
        setLoading(true);
        setSelected(null);
        setHasRated(false);
        setUserRating(0);
        setTimeout(() => {
            setLoading(false);
            setSelected(trends[0]);
        }, 2000);
    };

    const toggleFavorite = (e, item) => {
        e.stopPropagation();
        if (favorites.find(fav => fav.id === item.id)) {
            setFavorites(favorites.filter(fav => fav.id !== item.id));
        } else {
            setFavorites([...favorites, item]);
        }
    };


    const getTabData = () => {
        if (sidebarTab === 'trends') return trends;
        if (sidebarTab === 'favorites') return favorites;
        return history;
    };

    return (
        <div className="modern-root">
            <header className="modern-nav">
                <Link className="logo-wrap" style={{ textDecoration: 'none' }}>
                    <div className="premium-logo-container">
                        <div className="logo-halo"></div>
                        <div className="logo-structure">
                            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z" stroke="url(#paint0_linear)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                <path d="M8 9H16" stroke="white" strokeWidth="2" strokeLinecap="round" />
                                <path d="M8 13H13" stroke="white" strokeWidth="2" strokeLinecap="round" />
                                <circle cx="17.5" cy="12.5" r="2" fill="#ec4899" />
                                <defs>
                                    <linearGradient id="paint0_linear" x1="3" y1="3" x2="21" y2="21" gradientUnits="userSpaceOnUse">
                                        <stop stopColor="#a855f7" />
                                        <stop offset="1" stopColor="#6366f1" />
                                    </linearGradient>
                                </defs>
                            </svg>
                        </div>
                    </div>
                    <span className="brand-primary">Vivid<span className="brand-accent">AI</span></span>
                </Link>

                <div className="nav-right">
                    <div className="user-info-group">
                        <div className="user-pill">
                            <img src="https://ui-avatars.com/api/?name=N&background=c084fc&color=fff" alt="User" />
                            <span className="user-name">Nisanur Cebecioğlu</span>
                        </div>
                        <button className="logout-btn-v11" onClick={() => navigate('/')}>Çıkış Yap</button>
                    </div>
                </div>
            </header>

            <main className="main-grid">
                <aside className="panel-glass">
                    <div className="sidebar-tabs">
                        <button className={sidebarTab === 'trends' ? 'tab-btn active' : 'tab-btn'} onClick={() => setSidebarTab('trends')}>TRENDLER</button>
                        <button className={sidebarTab === 'history' ? 'tab-btn active' : 'tab-btn'} onClick={() => setSidebarTab('history')}>GEÇMİŞ</button>
                        <button className={sidebarTab === 'favorites' ? 'tab-btn active' : 'tab-btn'} onClick={() => setSidebarTab('favorites')}>FAVORİLER</button>
                    </div>
                    <div className="trend-list-scroll">
                        {getTabData().length > 0 ? getTabData().map(item => (
                            <div key={item.id} className="trend-card-v10" onClick={() => setSelected(item)}>
                                <div className="tc-img"><img src={item.img} alt={item.name} /></div>
                                <div className="tc-info">
                                    <h4>{item.name}</h4>
                                    <small>{item.plat}</small>
                                </div>
                                <div className="tc-score">{sidebarTab === 'favorites' ? '❤' : `★${item.avgScore}`}</div>
                            </div>
                        )) : <div className="no-data">Henüz veri yok.</div>}
                    </div>
                </aside>

                <section className="panel-glass report-view">
                    {selected ? (
                        <div className="report-container">
                            <div className="report-header-minimal">
                                <h2>{selected.name}</h2>
                                <span className="plat-tag">{selected.plat}</span>
                            </div>
                            <div className="visual-stage">
                                <img src={selected.img} alt={selected.name} className="stage-img" />
                                <div className="visual-overlay">
                                    <div className="overlay-actions">
                                        <button
                                            className={`action-pill fav-pill ${favorites.some(f => f.id === selected.id) ? 'active' : ''}`}
                                            onClick={(e) => toggleFavorite(e, selected)}
                                        >
                                            {favorites.some(f => f.id === selected.id) ? '❤ Favorilerde' : '♡ Favorilere Ekle'}
                                        </button>
                                        <a href={selected.productUrl} target="_blank" rel="noreferrer" className="action-pill visit-pill">Ürüne Git ↗</a>
                                    </div>
                                </div>
                            </div>
                            <div className="report-summary-box">
                                <label>✦ YAPAY ZEKA ANALİZ ÖZETİ</label>
                                <p>{selected.sum}</p>
                            </div>
                            <div className="category-analysis">
                                {selected.categories?.map((cat, i) => (
                                    <div key={i} className="cat-card">
                                        <h5>{cat.title}</h5>
                                        <p>{cat.comment}</p>
                                    </div>
                                ))}
                            </div>
                            <div className="feedback-section">

                                {!hasRated ? (
                                    <>
                                        <p>Bu analizi nasıl buldunuz?</p>
                                        <div className="stars-v2">
                                            {[1, 2, 3, 4, 5].map((s) => (
                                                <span
                                                    key={s}
                                                    className={(hoverRating || userRating) >= s ? "star active" : "star"}
                                                    onMouseEnter={() => setHoverRating(s)}
                                                    onMouseLeave={() => setHoverRating(0)}
                                                    onClick={() => {
                                                        setUserRating(s);
                                                        setHasRated(true);
                                                    }}
                                                >
                                                    ★
                                                </span>
                                            ))}
                                        </div>
                                    </>
                                ) : (

                                    <div className="thanks-msg-container">
                                        <div className="check-icon">✓</div>
                                        <div className="thanks-text">Geri bildiriminiz kaydedildi!</div>
                                        <small className="rated-score">Verdiğiniz Puan: {userRating}/5</small>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="empty-state">
                            <div className="pulse-icon">✦</div>
                            <h3>Veri Analiz Motoru Hazır</h3>
                            <p>Trendlerden bir ürün seçin veya analiz etmek istediğiniz ürün linkini yapıştırın.</p>
                        </div>
                    )}
                </section>
            </main>

            <div className="platform-marquee">
                <div className="marquee-content">
                    {[...platforms, ...platforms].map((p, i) => (
                        <span key={i} className="marquee-item">
                            <span className="dot">•</span> {p}
                        </span>
                    ))}
                </div>
            </div>

            <footer className="footer-zone">
                <div className="input-wrapper">
                    <input
                        placeholder="Amazon, Trendyol veya Hepsiburada linkini buraya bırakın..."
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                    />
                    <button className="btn-primary" onClick={handleAnalyze}>
                        {loading ? "Analiz Ediliyor..." : "Analizi Başlat"}
                    </button>
                </div>
            </footer>
        </div>
    );
}

export default Dashboard;