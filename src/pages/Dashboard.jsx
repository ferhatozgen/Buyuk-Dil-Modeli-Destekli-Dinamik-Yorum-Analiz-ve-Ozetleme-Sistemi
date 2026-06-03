import React, { useState, useCallback, useMemo } from 'react';
import {
    Search, Zap, Link2, ClipboardPaste, BarChart,
    LayoutGrid, Cpu, Shirt, UtensilsCrossed, Hotel,
    Sparkles, Dumbbell, BookOpen, Flower2, Baby,
    Car, Music, LogOut, TrendingUp, Clock, Heart,
    ChevronRight, Compass, FileText, ChartNoAxesColumnIncreasing,
    ChevronDown, Star
} from 'lucide-react';
import './Dashboard.css';
import ProductCard, { getPlatformColor } from './ProductCard';
import ProductPage from './ProductPage';
import { dbGet, dbSet, STORAGE_KEYS } from './storage';

/* ── AMAZON ÇIKARILMIŞ GÜNCEL VERİ SETİ ── */
const MOCK_PRODUCTS = [
    { id: 1, name: 'Keten Karışımlı Gömlek', category: 'Moda', plat: 'Trendyol', avgScore: 4.6, img: 'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400', productUrl: 'https://trendyol.com', sum: 'Kumaşın nefes alabilir yapısı yaz ayları için ideal bulunmuş. Tam kalıp olduğu belirtiliyor.' },
    { id: 2, name: 'Acılı Tavuk Dürüm Menü', category: 'Yemek & Gıda', plat: 'Yemeksepeti', avgScore: 4.4, img: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400', productUrl: 'https://yemeksepeti.com', sum: 'Sıcak ve hızlı teslimat öne çıkıyor. Sosların lezzeti kullanıcılar tarafından beğenilmiş.' },
    { id: 3, name: 'Taze Sıkma Portakal Suyu 1L', category: 'Yemek & Gıda', plat: 'Trendyol Go', avgScore: 4.8, img: 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=400', productUrl: 'https://trendyol.com', sum: 'Ürünlerin soğuk zincir bozulmadan hızlı ulaştığı raporlanmış. Meyve tazeliği vurgulanıyor.' },
    { id: 4, name: 'Moda Sahili Parkı', category: 'Gezilecek Yerler', plat: 'Google Maps', avgScore: 4.8, img: 'https://images.unsplash.com/photo-1572889601641-60a89d380e22?w=400', productUrl: 'https://maps.google.com', sum: 'Yürüyüş ve bisiklet yolları çok seviliyor. Hafta sonları kalabalık olabileceği belirtilmiş.' },
    { id: 5, name: 'Boğaz Manzaralı Teraslı Loft', category: 'Otel & Konaklama', plat: 'Airbnb', avgScore: 4.9, img: 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=400', productUrl: 'https://airbnb.com', sum: 'Evin temizliği ve ev sahibinin iletişimi kusursuz bulunmuş. Manzara beklentilerin üzerinde.' },
    { id: 6, name: 'Apple iPhone 15 Pro (256 GB)', category: 'Elektronik & Teknoloji', plat: 'Hepsiburada', avgScore: 4.7, img: 'https://images.unsplash.com/photo-1695048065166-51e891395b05?w=400', productUrl: 'https://hepsiburada.com', sum: 'Kamera performansı ve hafif titanyum kasa övülmüş. Batarya ömrü kullanıcıları tatmin ediyor.' },
    { id: 7, name: 'Cyberpunk 2077', category: 'Oyun & Eğlence', plat: 'Steam', avgScore: 4.2, img: 'https://images.unsplash.com/photo-1605901309584-818e25960b8f?w=400', productUrl: 'https://store.steampowered.com', sum: 'Güncellemelerle hikaye ve oynanışın çok iyileştiği, detaylı açık dünyanın etkileyici olduğu söyleniyor.' },
    { id: 8, name: 'Crystal Tat Beach Golf Resort', category: 'Otel & Konaklama', plat: 'Etstur', avgScore: 4.5, img: 'https://images.unsplash.com/photo-1582719508461-905c673771fd?w=400', productUrl: 'https://etstur.com', sum: 'Çocuklu aileler için havuz ve animasyon imkanları harika. Açık büfe yemek çeşitliliği çok zengin.' },
    { id: 9, name: 'Kırmızı Gül Buketi', category: 'Çiçek & Yenilebilir Çiçek', plat: 'Çiçeksepeti', avgScore: 4.4, img: 'https://images.unsplash.com/photo-1582791695759-4d22165c3619?w=400', productUrl: 'https://ciceksepeti.com', sum: 'Çiçeklerin çok taze ve canlı teslim edildiği belirtilmiş. Teslimat saatine titizlikle uyulmuş.' },
    { id: 10, name: 'Dyson V15 Kablosuz Süpürge', category: 'Elektronik & Teknoloji', plat: 'Hepsiburada', avgScore: 4.8, img: 'https://images.unsplash.com/photo-1558317374-067fb5f30001?w=400', productUrl: 'https://hepsiburada.com', sum: 'Lazer başlığın tozu gösterme performansı övülmüş. Batarya süresi performansa göre yeterli.' },
    { id: 11, name: 'Nike Air Force 1 Sneaker', category: 'Moda', plat: 'Hepsiburada', avgScore: 4.6, img: 'https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=400', productUrl: 'https://hepsiburada.com', sum: 'Gündelik kullanım için çok rahat ve şık bulunmuş. Temizliğinin kolay olduğu belirtiliyor.' },
    { id: 12, name: 'Estée Lauder Gece Serumu', category: 'Kozmetik & Kişisel Bakım', plat: 'Trendyol', avgScore: 4.7, img: 'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400', productUrl: 'https://trendyol.com', sum: 'Düzenli kullanımda cilde aydınlık kattığı raporlanmış. Kalitesi sebebiyle çok tercih ediliyor.' },
    { id: 13, name: 'Gece Yarısı Kütüphanesi', category: 'Diğer', plat: 'Trendyol', avgScore: 4.9, img: 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400', productUrl: 'https://trendyol.com', sum: 'Sürükleyici hikayesi ve derin karakter analizleri okuyucuları çok etkilemiş. Başucu kitabı niteliğinde.' },
    { id: 14, name: 'Nusret Steakhouse Etiler', category: 'Yemek & Gıda', plat: 'Google Maps', avgScore: 4.2, img: 'https://images.unsplash.com/photo-1544025162-d76694265947?w=400', productUrl: 'https://maps.google.com', sum: 'Et kalitesi ve sunumlar kusursuz bulunurken, popülerliği sebebiyle rezervasyon gerektiriyor.' }
];

const CATEGORIES = [
    { label: 'Hepsi', icon: LayoutGrid },
    { label: 'Yemek & Gıda', icon: UtensilsCrossed },
    { label: 'Elektronik & Teknoloji', icon: Cpu },
    { label: 'Moda', icon: Shirt },
    { label: 'Otel & Konaklama', icon: Hotel },
    { label: 'Oyun & Eğlence', icon: Music },
    { label: 'Çiçek & Yenilebilir Çiçek', icon: Flower2 },
    { label: 'Gezilecek Yerler', icon: Compass },
    { label: 'Kozmetik & Kişisel Bakım', icon: Sparkles },
    { label: 'Diğer', icon: LayoutGrid },
];

export default function Dashboard() {
    const [tab, setTab] = useState('kesfet');
    const [category, setCategory] = useState('Hepsi');
    const [searchQ, setSearchQ] = useState('');
    const [selected, setSelected] = useState(null);
    const [favorites, setFavorites] = useState(() => dbGet(STORAGE_KEYS.favorites) ?? []);
    const [ratings, setRatings] = useState(() => dbGet(STORAGE_KEYS.ratings) ?? {});
    const [history, setHistory] = useState(() => dbGet(STORAGE_KEYS.history) ?? []);
    const [searchCounts, setSearchCounts] = useState(() => dbGet(STORAGE_KEYS.searches) ?? {});
    const [clickCounts, setClickCounts] = useState(() => dbGet('clickCounts') ?? {});

    const [profileMenuOpen, setProfileMenuOpen] = useState(false);
    const [profileView, setProfileView] = useState(null);

    const toggleFav = useCallback((item) => {
        setFavorites((prev) => {
            const exists = prev.some((f) => f.id === item.id);
            const next = exists ? prev.filter((f) => f.id !== item.id) : [...prev, item];
            dbSet(STORAGE_KEYS.favorites, next);
            return next;
        });
    }, []);

    const handleRate = useCallback((productId, score) => {
        setRatings((prev) => {
            const next = { ...prev, [productId]: score };
            dbSet(STORAGE_KEYS.ratings, next);
            return next;
        });
    }, []);

    const recordSearch = useCallback((term) => {
        setHistory((prev) => {
            const next = [term, ...prev.filter((h) => h !== term)].slice(0, 20);
            dbSet(STORAGE_KEYS.history, next);
            return next;
        });
        setSearchCounts((prev) => {
            const next = { ...prev, [term]: (prev[term] || 0) + 1 };
            dbSet(STORAGE_KEYS.searches, next);
            return next;
        });
    }, []);

    const handleSearch = () => {
        const query = searchQ.trim();
        if (!query) return;

        recordSearch(query);

        const found = MOCK_PRODUCTS.find(p =>
            p.productUrl.toLowerCase().includes(query.toLowerCase()) ||
            p.name.toLowerCase().includes(query.toLowerCase())
        );

        if (found) {
            openProduct(found);
        } else {
            const isLink = query.startsWith('http') || query.includes('www.');
            const newAnalysis = {
                id: Date.now(),
                name: isLink ? 'Yeni URL Analizi Sonucu' : `"${query}" Analiz Raporu`,
                category: 'Diğer',
                plat: isLink ? 'Trendyol' : 'Sistem Geneli',
                avgScore: (Math.random() * (4.9 - 3.8) + 3.8).toFixed(1),
                img: 'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=400',
                productUrl: query,
                sum: 'VividAI girilen bağlantıyı başarıyla taradı. Kullanıcı duygu durum analizine göre olumlu bildirimler ezici çoğunlukta. Fiyat-performans dengesi stabil görünüyor.'
            };
            openProduct(newAnalysis);
        }
        setSearchQ('');
    };

    const openProduct = (item) => {
        recordSearch(item.name);
        setClickCounts((prev) => {
            const next = { ...prev, [item.id]: (prev[item.id] || 0) + 1 };
            dbSet('clickCounts', next);
            return next;
        });
        setSelected(item);
    };

    const handleLogout = () => { window.location.href = '/'; };

    const filteredProducts = useMemo(() =>
        MOCK_PRODUCTS.filter((p) => {
            if (category === 'Hepsi') return true;
            return p.category === category;
        }),
        [category]
    );

    const topRatedProducts = useMemo(() => {
        return [...MOCK_PRODUCTS].sort((a, b) => b.avgScore - a.avgScore);
    }, []);

    const trendProducts = useMemo(() => {
        return MOCK_PRODUCTS.map(p => ({
            ...p,
            clickCount: clickCounts[p.id] || 0
        })).sort((a, b) => b.clickCount - a.clickCount);
    }, [clickCounts]);

    if (selected) {
        return (
            <ProductPage
                product={selected}
                isFav={favorites.some((f) => f.id === selected.id)}
                onFav={toggleFav}
                onClose={() => setSelected(null)}
                userRating={ratings[selected.id]}
                onRate={handleRate}
                allProducts={MOCK_PRODUCTS}
                openProduct={openProduct}
                favorites={favorites}
                ratings={ratings}
            />
        );
    }

    return (
        <div className="vivid-main-page">
            <div className="bg-animation-layer">
                <div className="mesh-glow-light mesh-1"></div>
                <div className="mesh-glow-light mesh-2"></div>
                <div className="light-grid-overlay"></div>
            </div>

            <header className="vivid-top-nav">
                <div className="nav-glow-capsule">

                    <div className="logo-wrap" onClick={() => window.location.reload()}>
                        <div className="premium-logo-container">
                            <div className="logo-halo"></div>
                            <div className="logo-structure">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
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
                    </div>

                    <div className="vivid-user-profile-wrapper">
                        <div className="vivid-user-profile" onClick={() => setProfileMenuOpen(!profileMenuOpen)}>
                            <div className="user-avatar-circle">N</div>
                            <span className="user-name-display">Nisanur Cebecioğlu</span>
                            <ChevronDown size={14} className={`profile-chevron ${profileMenuOpen ? 'open' : ''}`} />
                        </div>

                        {profileMenuOpen && (
                            <div className="profile-dropdown-menu">
                                <div className="dropdown-header">Kişisel Menü</div>
                                <button className="dropdown-item" onClick={() => { setProfileView('favoriler'); setProfileMenuOpen(false); }}>
                                    <Heart size={14} /> Favorilerim
                                </button>
                                <button className="dropdown-item" onClick={() => { setProfileView('gecmis'); setProfileMenuOpen(false); }}>
                                    <Clock size={14} /> Analiz Geçmişi
                                </button>
                                <div className="dropdown-divider"></div>
                                <button className="dropdown-item exit-item" onClick={handleLogout}>
                                    <LogOut size={14} /> Çıkış Yap
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </header>

            <section className="vivid-hero-section">
                <div className="hero-top">
                    <div className="hero-text">
                        <h1>Analiz Portalına<br /><span>Hoş Geldin</span></h1>
                        <p>Ürün linkini yapıştır, AI ile anında detaylı analiz et.</p>
                    </div>
                    <div className="hero-stats">
                        <div className="stat-box">
                            <div className="s-num">12.4K</div>
                            <div className="s-label">Analiz Edildi</div>
                        </div>
                        <div className="stat-box">
                            <div className="s-num">4.8</div>
                            <div className="s-label">Ort. Puan</div>
                        </div>
                        <div className="stat-box">
                            <div className="s-num">98%</div>
                            <div className="s-label">Doğruluk Oranı</div>
                        </div>
                    </div>
                </div>

                <div className="search-glow-wrap">
                    <div className="search-inner-box">
                        <Search size={20} color="#94a3b8" className="search-icon" />
                        <input
                            className="search-input-field"
                            placeholder="Ürün linki yapıştır veya isim ile ara..."
                            value={searchQ}
                            onChange={(e) => setSearchQ(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleSearch(); }}
                        />
                        <button className="search-action-btn" onClick={handleSearch}>
                            <Zap size={16} /> Analiz Et
                        </button>
                    </div>
                </div>

                <div className="flow-steps-row">
                    <div className="flow-step-unit">
                        <div className="flow-icon-box"><Link2 size={18} /></div>
                        <div className="flow-text">
                            <div className="flow-title">Link'i Kopyala</div>
                            <div className="flow-desc">Ürün sayfasından URL al</div>
                        </div>
                    </div>
                    <ChevronRight size={16} color="#cbd5e1" />
                    <div className="flow-step-unit">
                        <div className="flow-icon-box"><ClipboardPaste size={18} /></div>
                        <div className="flow-text">
                            <div className="flow-title">Yapıştır</div>
                            <div className="flow-desc">Arama kutusuna ekle</div>
                        </div>
                    </div>
                    <ChevronRight size={16} color="#cbd5e1" />
                    <div className="flow-step-unit">
                        <div className="flow-icon-box"><ChartNoAxesColumnIncreasing size={18} /></div>
                        <div className="flow-text">
                            <div className="flow-title">Sonuçları Gör</div>
                            <div className="flow-desc">AI analiz raporunu incele</div>
                        </div>
                    </div>
                </div>
            </section>

            <div className="cat-section">
                <div className="cat-scroll-container">
                    <div className="cat-row">
                        {CATEGORIES.map((c) => {
                            const CurrentIcon = c.icon;
                            return (
                                <button
                                    key={c.label}
                                    className={`cat-pill ${category === c.label ? 'active' : ''}`}
                                    onClick={() => setCategory(c.label)}
                                >
                                    {CurrentIcon && <CurrentIcon size={14} />}
                                    {c.label}
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>

            <div className="tab-bar-container">
                <div className="tab-bar">
                    <button className={`tab-btn ${tab === 'kesfet' ? 'active' : ''}`} onClick={() => setTab('kesfet')}>
                        <Compass size={16} /> Keşfet
                    </button>
                    <button className={`tab-btn ${tab === 'begenilenler' ? 'active' : ''}`} onClick={() => setTab('begenilenler')}>
                        <Star size={16} /> En Çok Beğenilenler
                    </button>
                    <button className={`tab-btn ${tab === 'trendler' ? 'active' : ''}`} onClick={() => setTab('trendler')}>
                        <TrendingUp size={16} /> Trend Sıralaması
                    </button>
                </div>
            </div>

            {tab === 'kesfet' && (
                <div className="vivid-section">
                    {filteredProducts.length === 0 ? (
                        <div className="empty-state">
                            <Search size={32} color="#cbd5e1" />
                            <br />Bu kategoride ürün bulunamadı.
                        </div>
                    ) : (
                        <div className="card-grid">
                            {filteredProducts.map((item) => (
                                <ProductCard
                                    key={item.id}
                                    item={item}
                                    isFav={favorites.some((f) => f.id === item.id)}
                                    onFav={toggleFav}
                                    onClick={() => openProduct(item)}
                                    userRating={ratings[item.id]}
                                />
                            ))}
                        </div>
                    )}
                </div>
            )}

            {tab === 'begenilenler' && (
                <div className="vivid-section">
                    <div className="card-grid">
                        {topRatedProducts.map((item) => (
                            <ProductCard
                                key={item.id}
                                item={item}
                                isFav={favorites.some((f) => f.id === item.id)}
                                onFav={toggleFav}
                                onClick={() => openProduct(item)}
                                userRating={ratings[item.id]}
                            />
                        ))}
                    </div>
                </div>
            )}

            {tab === 'trendler' && (
                <div className="vivid-section">
                    {trendProducts.filter(p => p.clickCount > 0).length === 0 ? (
                        <div className="empty-state">
                            <BarChart size={32} color="#cbd5e1" />
                            <br />Henüz hiçbir ürüne tıklanmadı.
                        </div>
                    ) : (
                        trendProducts.filter(p => p.clickCount > 0).map((product, i, arr) => {
                            const platColor = getPlatformColor(product.plat);

                            return (
                                <div key={product.id} className="trend-row" onClick={() => openProduct(product)}>
                                    <span className="t-rank" style={{ color: platColor }}>#{i + 1}</span>

                                    <div className="t-img-box">
                                        <img src={product.img} alt={product.name} />
                                    </div>

                                    <div className="trend-row-info">
                                        <span className="t-name">{product.name}</span>
                                        <span className="t-sub">{product.category} · <strong style={{ color: platColor }}>{product.plat}</strong></span>
                                    </div>

                                    <span className="t-badge" style={{ backgroundColor: `${platColor}15`, color: platColor, border: `1px solid ${platColor}30` }}>
                                        {product.clickCount} tıklanma
                                    </span>

                                    <div className="trend-bar-wrap">
                                        <div
                                            className="trend-bar"
                                            style={{
                                                backgroundColor: platColor,
                                                width: Math.min(100, (product.clickCount / (arr[0].clickCount || 1)) * 100) + '%'
                                            }}
                                        />
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            )}

            {profileView && (
                <div className="profile-modal-overlay" onClick={() => setProfileView(null)}>
                    <div className="profile-modal-card" onClick={(e) => e.stopPropagation()}>
                        <div className="profile-modal-header">
                            <div className="profile-modal-tabs">
                                <button className={`p-tab-btn ${profileView === 'favoriler' ? 'active' : ''}`} onClick={() => setProfileView('favoriler')}>
                                    <Heart size={14} /> Favorilerim
                                </button>
                                <button className={`p-tab-btn ${profileView === 'gecmis' ? 'active' : ''}`} onClick={() => setProfileView('gecmis')}>
                                    <Clock size={14} /> Analiz Geçmişim
                                </button>
                            </div>
                            <button className="profile-modal-close" onClick={() => setProfileView(null)}>✕</button>
                        </div>

                        <div className="profile-modal-body">
                            {profileView === 'favoriler' && (
                                <div className="modal-inner-section">
                                    {favorites.length === 0 ? (
                                        <div className="empty-state"><Heart size={32} /><br />Henüz favorilere ürün eklemediniz.</div>
                                    ) : (
                                        <div className="modal-card-grid">
                                            {favorites.map((item) => (
                                                <ProductCard key={item.id} item={item} isFav={true} onFav={toggleFav} onClick={() => { openProduct(item); setProfileView(null); }} userRating={ratings[item.id]} />
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {profileView === 'gecmis' && (
                                <div className="modal-inner-section">
                                    {history.length === 0 ? (
                                        <div className="empty-state"><Clock size={32} /><br />Arama geçmişiniz temiz.</div>
                                    ) : (
                                        <div className="modal-card-grid">
                                            {history.map((h) => {
                                                const matchedProduct = MOCK_PRODUCTS.find((p) => p.name === h);
                                                if (!matchedProduct) return null;
                                                return (
                                                    <ProductCard key={matchedProduct.id} item={matchedProduct} isFav={favorites.some((f) => f.id === matchedProduct.id)} onFav={toggleFav} onClick={() => { setSelected(matchedProduct); setProfileView(null); }} userRating={ratings[matchedProduct.id]} />
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
            <div style={{ height: 60 }} />
        </div>
    );
}