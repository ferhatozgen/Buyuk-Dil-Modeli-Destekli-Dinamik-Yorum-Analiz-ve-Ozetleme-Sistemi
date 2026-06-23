import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useInView } from 'react-intersection-observer';

import {
    Search, Zap, Link2, BarChart, LayoutGrid, Cpu, Shirt, UtensilsCrossed, Hotel,
    Sparkles, Compass, Flower2, LogOut, TrendingUp, Clock, Heart, ChevronDown, Star,
    ClipboardPaste, ChartNoAxesColumnIncreasing, ChevronRight,
    ShoppingBag, BookOpen, Home, GraduationCap, HeartPulse, Gamepad2,
    Baby, Gift, PawPrint, Store, Cookie, Wrench, Building2, Dumbbell, Gem, Armchair, MoreHorizontal, Loader2, AlertCircle
} from 'lucide-react';
import './Dashboard.css';
import ProductCard, { getPlatformColor } from './ProductCard';
import ProductPage from './ProductPage';
import { dbGet, dbSet, STORAGE_KEYS } from './storage';
import api from '../api';

const CATEGORIES = [
    { label: 'Hepsi', icon: LayoutGrid },
    { label: 'Alışveriş', icon: ShoppingBag },
    { label: 'Kırtasiye & Kitap & Hobi', icon: BookOpen },
    { label: 'Otel', icon: Hotel },
    { label: 'Günlük Ev', icon: Home },
    { label: 'Giyim & Ayakkabı', icon: Shirt },
    { label: 'Eğitim & Eğlence', icon: GraduationCap },
    { label: 'Sağlık', icon: HeartPulse },
    { label: 'Oyun', icon: Gamepad2 },
    { label: 'Yemek', icon: UtensilsCrossed },
    { label: 'Gezilecek Yer', icon: Compass },
    { label: 'Anne & Bebek & Oyuncak', icon: Baby },
    { label: 'Kozmetik & Kişisel Bakım', icon: Sparkles },
    { label: 'Hediyelik Eşya', icon: Gift },
    { label: 'Pet Shop', icon: PawPrint },
    { label: 'Süpermarket & Gıda', icon: Store },
    { label: 'Çiçek', icon: Flower2 },
    { label: 'Yenilebilir Çiçek', icon: Cookie },
    { label: 'Hizmet', icon: Wrench },
    { label: 'Kurumsal', icon: Building2 },
    { label: 'Spor & Outdoor', icon: Dumbbell },
    { label: 'Aksesuar & Takı', icon: Gem },
    { label: 'Ev & Yaşam & Mobilya', icon: Armchair },
    { label: 'Elektronik & Teknoloji', icon: Cpu },
    { label: 'Diğer', icon: MoreHorizontal }
];

const DB_CATEGORY_MAP = {
    'Alışveriş': 'alisveris',
    'Kırtasiye & Kitap & Hobi': 'kirtasiye_kitap_hobi',
    'Otel': 'otel',
    'Günlük Ev': 'gunluk_ev',
    'Giyim & Ayakkabı': 'giyim_ayakkabi',
    'Eğitim & Eğlence': 'egitim_eglence',
    'Sağlık': 'saglik',
    'Oyun': 'oyun',
    'Yemek': 'yemek',
    'Gezilecek Yer': 'gezilecek_yer',
    'Anne & Bebek & Oyuncak': 'anne_bebek_oyuncak',
    'Kozmetik & Kişisel Bakım': 'kozmetik_kisisel_bakim',
    'Hediyelik Eşya': 'hediyelik_esya',
    'Pet Shop': 'pet_shop',
    'Süpermarket & Gıda': 'supermarket_gida',
    'Çiçek': 'cicek',
    'Yenilebilir Çiçek': 'yenilebilir_cicek',
    'Hizmet': 'hizmet',
    'Kurumsal': 'kurumsal',
    'Spor & Outdoor': 'spor_outdoor',
    'Aksesuar & Takı': 'aksesuar_taki',
    'Ev & Yaşam & Mobilya': 'ev_yasam_mobilya',
    'Elektronik & Teknoloji': 'elektronik_teknoloji',
    'Diğer': 'diger'
};

export default function Dashboard() {
    const navigate = useNavigate();
    const currentToken = localStorage.getItem('token');
    const username = localStorage.getItem('username') || 'Misafir';

    const userFavKey = `${STORAGE_KEYS.favorites}_${username}`;
    const userRateKey = `${STORAGE_KEYS.ratings}_${username}`;
    const userHistKey = `${STORAGE_KEYS.history}_${username}`;

    // --- 1. ADIM: TÜM HOOK'LAR EN TEPEDE ---
    const [tab, setTab] = useState('kesfet');
    const [category, setCategory] = useState('Hepsi');
    const [searchQ, setSearchQ] = useState('');

    const [linkQ, setLinkQ] = useState('');
    const [linkError, setLinkError] = useState('');
    const [analyzeError, setAnalyzeError] = useState(null);

    const [selected, setSelected] = useState(null);
    const [favorites, setFavorites] = useState(() => dbGet(userFavKey) ?? []);
    const [ratings, setRatings] = useState(() => dbGet(userRateKey) ?? {});
    const [history, setHistory] = useState(() => dbGet(userHistKey) ?? []);

    const [profileMenuOpen, setProfileMenuOpen] = useState(false);
    const [profileView, setProfileView] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [loadingStep, setLoadingStep] = useState(0);

    const { ref: observerRef, inView } = useInView();

    // ... (formatCategory ve analyzeSteps değişkenlerin burada kalabilir) ...

    const analyzeSteps = [
        "Hedef sayfa kaynağına erişiliyor...",
        "Kullanıcı yorumları ve meta veriler çekiliyor...",
        "LLM üzerinden duygu analizi gerçekleştiriyor...",
        "Genel trend ve sentez raporu oluşturuluyor..."
    ];

    const formatCategory = (rawCat) => {
        if (!rawCat) return 'Diğer';
        const str = rawCat.toLowerCase().replace(/_/g, ' ');

        if (str.includes('anne') || str.includes('bebek') || str.includes('oyuncak')) return 'Anne & Bebek & Oyuncak';
        if (str.includes('oyun') || str.includes('game')) return 'Oyun';
        if (str.includes('elektronik') || str.includes('teknoloji')) return 'Elektronik & Teknoloji';
        if (str.includes('kırtasiye') || str.includes('kirtasiye') || str.includes('kitap') || str.includes('hobi')) return 'Kırtasiye & Kitap & Hobi';
        if (str.includes('otel') || str.includes('konaklama')) return 'Otel';
        if (str.includes('günlük ev') || str.includes('gunluk')) return 'Günlük Ev';
        if (str.includes('giyim') || str.includes('ayakkabı') || str.includes('ayakkabi')) return 'Giyim & Ayakkabı';
        if (str.includes('eğitim') || str.includes('egitim') || str.includes('eğlence')) return 'Eğitim & Eğlence';
        if (str.includes('sağlık') || str.includes('saglik')) return 'Sağlık';
        if (str.includes('yemek') || str.includes('restoran')) return 'Yemek';
        if (str.includes('gezi') || str.includes('gezilecek')) return 'Gezilecek Yer';
        if (str.includes('kozmetik') || str.includes('bakım') || str.includes('bakim')) return 'Kozmetik & Kişisel Bakım';
        if (str.includes('hediye')) return 'Hediyelik Eşya';
        if (str.includes('pet') || str.includes('hayvan')) return 'Pet Shop';
        if (str.includes('market') || str.includes('gıda') || str.includes('gida') || str.includes('süpermarket')) return 'Süpermarket & Gıda';
        if (str.includes('yenilebilir')) return 'Yenilebilir Çiçek';
        if (str.includes('çiçek') || str.includes('cicek')) return 'Çiçek';
        if (str.includes('hizmet')) return 'Hizmet';
        if (str.includes('kurumsal')) return 'Kurumsal';
        if (str.includes('spor') || str.includes('outdoor')) return 'Spor & Outdoor';
        if (str.includes('aksesuar') || str.includes('takı') || str.includes('taki')) return 'Aksesuar & Takı';
        if (str.includes('ev') || str.includes('yaşam') || str.includes('yasam') || str.includes('mobilya')) return 'Ev & Yaşam & Mobilya';
        if (str.includes('alışveriş') || str.includes('alisveris')) return 'Alışveriş';

        return 'Diğer';
    };

    const fetchProductsPage = async ({ pageParam = 1 }) => {
        const params = {
            PageNumber: pageParam,
            PageSize: 20,
        };

        if (category !== 'Hepsi') params.Category = DB_CATEGORY_MAP[category] || 'diger';
        if (searchQ.trim() !== '') params.SearchTerm = searchQ.trim();
        if (tab === 'begenilenler') params.SortBy = 'mostLiked';
        else if (tab === 'trendler') params.SortBy = 'mostClicked';

        const response = await api.get('/Product/all', {
            params: params,
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });

        return response.data.map(p => ({
            id: p.id,
            name: p.name || p.productName,
            category: formatCategory(p.category),
            plat: p.platformName || p.platform || 'Sistem',
            avgScore: p.modelScore ? p.modelScore.toFixed(1) : (p.averageRating ? p.averageRating.toFixed(1) : "0.0"),
            img: p.imageUrl || 'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=400',
            clickCount: p.clickCount,
            sum: p.guncelOzet || "Yapay zeka modelleri tarafından analiz edilmiştir.",
            isFavorited: p.isFavorited
        }));
    };

    const {
        data,
        fetchNextPage,
        hasNextPage,
        isFetchingNextPage,
        status,
    } = useInfiniteQuery({
        queryKey: ['products', category, searchQ, tab, currentToken],
        queryFn: fetchProductsPage,
        getNextPageParam: (lastPage, allPages) => {
            return lastPage.length === 20 ? allPages.length + 1 : undefined;
        },
        staleTime: 5 * 60 * 1000,
    });

    useEffect(() => {
        if (inView && hasNextPage) {
            fetchNextPage();
        }
    }, [inView, hasNextPage, fetchNextPage]);

    useEffect(() => {
        if (data) {
            const backendFavorites = data.pages
                .flatMap(page => page)
                .filter(p => p.isFavorited);
            
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setFavorites(prevFavs => {
                const newFavs = [...prevFavs];
                let changed = false;

                backendFavorites.forEach(backendFav => {
                    if (!newFavs.some(f => f.id === backendFav.id)) {
                        newFavs.push(backendFav);
                        changed = true;
                    }
                });

                if (changed) {
                    dbSet(userFavKey, newFavs);
                    return newFavs;
                }
                return prevFavs;
            });
        }
    }, [data, userFavKey]);

    const flatProducts = data?.pages.flatMap(page => page) || [];

    const toggleFav = useCallback(async (item, skipApi = false) => {
        setFavorites((prev) => {
            const exists = prev.some((f) => f.id === item.id);
            const next = exists ? prev.filter((f) => f.id !== item.id) : [...prev, item];
            dbSet(userFavKey, next);
            return next;
        });

        if (!skipApi) {
            try {
                const token = localStorage.getItem('token');
                if (token) {
                    const response = await api.post(`/Product/${item.id}/toggle-save`, {}, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    const actualStatus = response.data.isSaved !== undefined ? response.data.isSaved : response.data.IsSaved;

                    if (actualStatus !== undefined) {
                        setFavorites((prev) => {
                            const exists = prev.some((f) => f.id === item.id);
                            let next = [...prev];
                            if (actualStatus && !exists) next.push(item);
                            else if (!actualStatus && exists) next = next.filter((f) => f.id !== item.id);
                            dbSet(userFavKey, next);
                            return next;
                        });
                    }
                }
            } catch (error) {
                console.error("Favori durumu backend'e iletilemedi:", error);
            }
        }
    }, [userFavKey]);

    const handleRate = useCallback((productId, score) => {
        setRatings((prev) => {
            const next = { ...prev, [productId]: score };
            dbSet(userRateKey, next);
            return next;
        });
    }, [userRateKey]);

    const recordSearch = useCallback((term) => {
        if (!term) return;
        setHistory((prev) => {
            const next = [term, ...prev.filter((h) => h !== term)].slice(0, 20);
            dbSet(userHistKey, next);
            return next;
        });
    }, [userHistKey]);

    const handleLinkAnalyze = async () => {
        const query = linkQ.trim();
        if (!query) return;

        setLinkError('');
        setAnalyzeError(null);

        // --- Link Format Kontrolü ---
        const urlPattern = /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([/\w .-]*)*\/?$/;
        if (!urlPattern.test(query)) {
            setLinkError('Lütfen analiz etmek istediğiniz ürünün tam bağlantısını (URL) yapıştırın.');
            return;
        }

        recordSearch(query);
        setIsAnalyzing(true);
        setLoadingStep(0); // 0: "Hedef sayfa kaynağına erişiliyor..."

        try {
            const config = {
                headers: { 'Authorization': `Bearer ${currentToken}` }
            };

            // --- ADIM 1: KAZIMA (SCRAPE) ---
            // Backend'e linki gönderiyoruz ve veritabanında oluşan Product Id'yi alıyoruz
            const step1Res = await api.post('/Product/step1-scrape', { url: query }, config);
            const currentProductId = step1Res.data.productId;
            
            if (!currentProductId) throw new Error("Ürün ID alınamadı");

            // --- ADIM 2: PUANLAMA (SCORE) ---
            setLoadingStep(1); // 1: "Kullanıcı yorumları ve meta veriler çekiliyor..."
            await api.post('/Product/step2-score', { productId: currentProductId }, config);

            // --- ADIM 3: KATEGORİZASYON (CATEGORIZE) ---
            setLoadingStep(2); // 2: "LLM üzerinden duygu analizi gerçekleştiriyor..."
            await api.post('/Product/step3-categorize', { productId: currentProductId }, config);

            // --- ADIM 4: ÖZETLEME (SUMMARIZE) ---
            setLoadingStep(3); // 3: "Genel trend ve sentez raporu oluşturuluyor..."
            await api.post('/Product/step4-summarize', { productId: currentProductId }, config);

            // --- İŞLEM BİTTİ: ÜRÜN BİLGİSİNİ ÇEK VE YÖNLENDİR ---
            const finalProductRes = await api.get(`/Product/${currentProductId}`, config);
            
            const newAnalysis = {
                id: finalProductRes.data.id,
                name: finalProductRes.data.productName,
                category: formatCategory(finalProductRes.data.category),
                plat: finalProductRes.data.platform,
                avgScore: finalProductRes.data.avgModelScore ? finalProductRes.data.avgModelScore.toFixed(1) : "0.0",
                img: finalProductRes.data.imageUrl || 'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=400',
                clickCount: finalProductRes.data.clickCount || 0,
            };

            setIsAnalyzing(false);
            setLinkQ('');
            
            // Kullanıcıyı detay sayfasına atıyoruz!
            openProduct(newAnalysis);

        } catch (error) {
            console.error("Analiz Akışı Hatası:", error);
            setIsAnalyzing(false);
            
            // Hatanın tipine göre kullanıcıya mesaj gösterebiliriz
            if (error.response?.status === 404) {
                 setAnalyzeError('Bağlantıdaki ürün veya yorumları bulunamadı. Lütfen geçerli bir e-ticaret linki girin.');
            } else {
                 setAnalyzeError('Modeller arası veri iletişiminde bir sorun oluştu. Sunucunun yanıt vermesi uzun sürmüş olabilir, lütfen tekrar deneyin.');
            }
        }
    };

    const handleSystemSearch = () => {
        if (!searchQ.trim()) return;
        recordSearch(searchQ.trim());
    };

    const openProduct = async (item) => {
        recordSearch(item.name);
        setSelected(item);
    };

    const handleLogout = async () => {
        try {
            if (currentToken) {
                await api.post('/Auth/logout', {}, {
                    headers: { 'Authorization': `Bearer ${currentToken}` }
                });
            }
        } catch (error) {
            console.error("Çıkış isteği hatası:", error);
        } finally {
            localStorage.removeItem('token');
            localStorage.removeItem('refreshToken');
            localStorage.removeItem('username');
            localStorage.removeItem(userFavKey);
            localStorage.removeItem(userHistKey);
            localStorage.removeItem(userRateKey);

            setFavorites([]);
            setHistory([]);
            setRatings({});
            navigate('/', { replace: true });
        }
    };
    
    if (!currentToken) return <Navigate to="/" replace />;

    if (selected) {
        return (
            <ProductPage
                product={selected}
                isFav={favorites.some((f) => f.id === selected.id)}
                onFav={toggleFav}
                onClose={() => setSelected(null)}
                userRating={ratings[selected.id]}
                onRate={handleRate}
                allProducts={flatProducts}
                openProduct={openProduct}
                favorites={favorites}
                ratings={ratings}
            />
        );
    }

    return (
        <div className="vivid-main-page">

            {/* ANALİZ EDİLİYOR MODALI */}
            {isAnalyzing && (
                <div className="vivid-ai-loader-overlay">
                    <div className="vivid-ai-loader-card">
                        <div className="loader-orbit-container">
                            <div className="loader-orbit-ring ring-1"></div>
                            <div className="loader-orbit-ring ring-2"></div>
                            <div className="loader-core">
                                <Sparkles size={28} color="#ffffff" />
                            </div>
                        </div>
                        <h2 className="loader-title">VividAİ Analize Başladı</h2>
                        <div className="loader-step-text">{analyzeSteps[loadingStep]}</div>
                        <div className="loader-progress-wrap">
                            <div
                                className="loader-progress-bar"
                                style={{ width: `${((loadingStep + 1) / analyzeSteps.length) * 100}%` }}
                            ></div>
                        </div>
                    </div>
                </div>
            )}

            {/* ÜRÜN BULUNAMADI / HATA MODALI (FROSTED GLASS TASARIM) */}
            {analyzeError && (
                <div className="vivid-ai-loader-overlay" onClick={() => setAnalyzeError(null)} style={{ backdropFilter: 'blur(8px)' }}>
                    <div
                        className="vivid-ai-loader-card"
                        style={{
                            background: 'rgba(255, 255, 255, 0.75)',
                            backdropFilter: 'blur(24px)',
                            WebkitBackdropFilter: 'blur(24px)',
                            border: '1px solid rgba(255, 255, 255, 0.5)',
                            boxShadow: '0 24px 48px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(239, 68, 68, 0.15)'
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '16px', borderRadius: '50%', marginBottom: '16px' }}>
                            <AlertCircle size={32} color="#ef4444" />
                        </div>
                        <h2 className="loader-title" style={{ color: '#0f172a', fontSize: '22px' }}>Analiz Başarısız</h2>
                        <p style={{ fontSize: '14px', color: '#475569', margin: '12px 0 28px 0', lineHeight: '1.6', textAlign: 'center', fontWeight: '500' }}>
                            {analyzeError}
                        </p>
                        <button
                            className="search-action-btn"
                            style={{
                                width: '100%',
                                background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                                boxShadow: '0 8px 16px rgba(239, 68, 68, 0.25)',
                                border: 'none',
                                borderRadius: '12px'
                            }}
                            onClick={() => setAnalyzeError(null)}
                        >
                            Tekrar Dene
                        </button>
                    </div>
                </div>
            )}

            <div className="bg-animation-layer">
                <div className="mesh-glow-light mesh-1"></div>
                <div className="mesh-glow-light mesh-2"></div>
                <div className="bg-grid-dashboard"></div>
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
                            <div className="brand-primary">Vivid<span className="brand-accent">Aİ</span></div>
                            <div className="brand-slogan">Yapay Zeka Analiz Motoru</div>
                        </div>
                    </div>

                    <div className="vivid-user-profile-wrapper">
                        <div className="vivid-user-profile" onClick={() => setProfileMenuOpen(!profileMenuOpen)}>
                            <div className="user-avatar-container">
                                <div className="user-avatar-circle">{username.charAt(0).toUpperCase()}</div>
                                <div className="online-indicator"></div>
                            </div>
                            <div className="user-info-stack">
                                <span className="user-name-display">{username}</span>
                            </div>
                            <ChevronDown size={14} className={`profile-chevron ${profileMenuOpen ? 'open' : ''}`} />
                        </div>

                        {profileMenuOpen && (
                            <div className="profile-dropdown-menu">
                                <div className="dropdown-user-header">
                                    <div className="user-avatar-circle large">{username.charAt(0).toUpperCase()}</div>
                                    <div className="dropdown-user-details">
                                        <span className="d-name">{username}</span>
                                        <span className="d-role">Yetkili Kullanıcı</span>
                                    </div>
                                </div>
                                <div className="dropdown-divider-thick"></div>
                                <div className="dropdown-menu-list">
                                    <button className="dropdown-item" onClick={() => { setProfileView('favoriler'); setProfileMenuOpen(false); }}>
                                        <Heart size={16} color="#ec4899" /> Koleksiyonum
                                    </button>
                                    <button className="dropdown-item" onClick={() => { setProfileView('gecmis'); setProfileMenuOpen(false); }}>
                                        <Clock size={16} color="#3b82f6" /> Analiz Geçmişi
                                    </button>
                                </div>
                                <div className="dropdown-divider-thick"></div>
                                <button className="dropdown-item exit-item" onClick={handleLogout}>
                                    <LogOut size={16} /> Oturumu Kapat
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </header>
            <div className="dashboard-academic-bannerr">
                BU PROJE AKADEMİK AMAÇLIDIR VE TİCARİ BİR KULLANIM İÇERMEZ
            </div>
            <section className="vivid-hero-section">
                <div className="hero-top">
                    <div className="hero-text">
                        <h1> Yapay Zeka Destekli Analiz Motoruna <br /><span>Hoş Geldiniz</span></h1>
                        <p>Ürün linkini aşağıya yapıştırın, dil modelleri yardımı ile anında analiz edin.</p>
                    </div>
                </div>
                <div className="search-glow-wrap">
                    <div className={`search-inner-box main-analyze-box ${linkError ? 'error-border' : ''}`} style={linkError ? { borderColor: 'rgba(239, 68, 68, 0.5)', boxShadow: '0 0 0 6px rgba(239, 68, 68, 0.1)' } : {}}>
                        <Link2 size={24} color={linkError ? "#ef4444" : "#7c3aed"} className="search-icon" />
                        <input
                            className="search-input-field"
                            placeholder="E-ticaret platformlarından (Trendyol, vb.) ürün linkini yapıştırın..."
                            value={linkQ}
                            onChange={(e) => {
                                setLinkQ(e.target.value);
                                if (linkError) setLinkError('');
                            }}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleLinkAnalyze(); }}
                        />
                        <button className="search-action-btn pulse-glow" onClick={handleLinkAnalyze}><Zap size={18} /> Analiz Et</button>
                    </div>
                    {/* Hata Mesajı Alt Bilgi (Frosted Box) */}
                    {linkError && (
                        <div style={{
                            color: '#ef4444',
                            fontSize: '13px',
                            marginTop: '12px',
                            fontWeight: '600',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '10px 16px',
                            background: 'rgba(239, 68, 68, 0.05)',
                            backdropFilter: 'blur(8px)',
                            borderRadius: '12px',
                            border: '1px solid rgba(239, 68, 68, 0.15)',
                            width: 'fit-content'
                        }}>
                            <AlertCircle size={16} /> {linkError}
                        </div>
                    )}
                </div>
            </section>

            <div className="system-nav-section">
                <div className="cat-scroll-container">
                    <div className="cat-tile-row">
                        {CATEGORIES.map((c) => {
                            const CurrentIcon = c.icon;
                            return (
                                <button key={c.label} className={`cat-tile-btn ${category === c.label ? 'active' : ''}`} onClick={() => setCategory(c.label)}>
                                    <div className="cat-circle">{CurrentIcon && <CurrentIcon size={24} strokeWidth={1.5} />}</div>
                                    <span className="cat-text">{c.label}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>
            </div>

            <div className="tab-search-wrapper">
                <div className="tab-bar">
                    <button className={`tab-btn ${tab === 'kesfet' ? 'active' : ''}`} onClick={() => setTab('kesfet')}><Compass size={18} /> Keşfet</button>
                    <button className={`tab-btn ${tab === 'begenilenler' ? 'active' : ''}`} onClick={() => setTab('begenilenler')}><Star size={18} /> En Çok Beğenilenler</button>
                    <button className={`tab-btn ${tab === 'trendler' ? 'active' : ''}`} onClick={() => setTab('trendler')}><TrendingUp size={18} /> Trend Sıralaması</button>
                </div>

                {tab === 'kesfet' && (
                    <div className="compact-search-box">
                        <input placeholder="Mevcut sistemde ara..." value={searchQ} onChange={(e) => setSearchQ(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') handleSystemSearch(); }} />
                        <button className="compact-search-btn" onClick={handleSystemSearch}><Search size={14} /> Ara</button>
                    </div>
                )}
            </div>

            <div className="vivid-section">
                {status === 'pending' ? (
                    <div className="empty-state" style={{ padding: '40px' }}>
                        <Loader2 size={40} color="#7c3aed" className="animate-spin" />
                        <br />Ürünler yükleniyor...
                    </div>
                ) : status === 'error' ? (
                    <div className="empty-state" style={{ padding: '40px', color: '#ef4444' }}>
                        Ürünler yüklenirken bir hata oluştu. Lütfen oturumunuzu yenileyin.
                    </div>
                ) : (
                    <>
                        {(tab === 'kesfet' || tab === 'begenilenler') && (
                            flatProducts.length === 0 ? (
                                <div className="empty-state">
                                    <Search size={40} color="#cbd5e1" />
                                    <br />{category === 'Hepsi' && searchQ === '' ? 'Henüz sistemde ürün bulunmuyor.' : 'Aradığınız kritere uygun ürün bulunamadı.'}
                                </div>
                            ) : (
                                <div className="card-grid">
                                    {flatProducts.map((item) => (
                                        <ProductCard
                                            key={item.id}
                                            item={item}
                                            isFav={favorites.some((f) => f.id === item.id)}
                                            onFav={toggleFav}
                                            onClick={() => openProduct(item)}
                                            userRating={ratings[item.id]}
                                        />
                                    ))}

                                    <div ref={observerRef} style={{ width: '100%', height: '20px', display: 'flex', justifyContent: 'center', margin: '20px 0' }}>
                                        {isFetchingNextPage ? <Loader2 size={24} className="animate-spin text-purple-600" /> : null}
                                    </div>
                                </div>
                            )
                        )}

                        {tab === 'trendler' && (
                            flatProducts.filter(p => p.clickCount > 0).length === 0 ? (
                                <div className="empty-state">
                                    <BarChart size={40} color="#cbd5e1" />
                                    <br />Henüz tıklanan ürün bulunamadı.
                                </div>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                    {flatProducts
                                        .filter(p => p.clickCount > 0)
                                        .sort((a, b) => b.clickCount - a.clickCount)
                                        .map((product, i) => {
                                            const platColor = getPlatformColor(product.plat);
                                            return (
                                                <div key={product.id} className="trend-row" onClick={() => openProduct(product)}>
                                                    <span className="t-rank" style={{ color: platColor }}>#{i + 1}</span>
                                                    <div className="t-img-box"><img src={product.img} alt={product.name} /></div>
                                                    <div className="trend-row-info">
                                                        <span className="t-name">{product.name}</span>
                                                        <span className="t-sub">{product.category} · <strong style={{ color: platColor }}>{product.plat}</strong> · {product.clickCount} Tıklama</span>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                </div>
                            )
                        )}
                    </>
                )}
            </div>

            {profileView && (
                <div className="profile-modal-overlay" onClick={() => setProfileView(null)}>
                    <div className="profile-modal-card" onClick={(e) => e.stopPropagation()}>
                        <div className="profile-modal-header">
                            <div className="profile-modal-tabs">
                                <button className={`p-tab-btn ${profileView === 'favoriler' ? 'active' : ''}`} onClick={() => setProfileView('favoriler')}><Heart size={16} /> Koleksiyonum</button>
                                <button className={`p-tab-btn ${profileView === 'gecmis' ? 'active' : ''}`} onClick={() => setProfileView('gecmis')}><Clock size={16} /> Analiz Geçmişim</button>
                            </div>
                            <button className="profile-modal-close" onClick={() => setProfileView(null)}>✕</button>
                        </div>

                        <div className="profile-modal-body">
                            {profileView === 'favoriler' && (
                                <div className="modal-inner-section">
                                    {status === 'pending' ? (
                                        <div className="empty-state" style={{ padding: '60px 20px' }}>
                                            <Loader2 size={40} color="#7c3aed" className="animate-spin" />
                                            <br /><br />Koleksiyonunuz senkronize ediliyor...
                                        </div>
                                    ) : favorites.length === 0 ? (
                                        <div className="empty-state"><Heart size={40} /><br />Henüz koleksiyonunuza ürün eklemediniz.</div>
                                    ) : (
                                        <div className="modal-card-grid card-grid">
                                            {favorites.map((item) => (
                                                <ProductCard key={item.id} item={item} isFav={true} onFav={toggleFav} onClick={() => { openProduct(item); setProfileView(null); }} userRating={ratings[item.id]} />
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {profileView === 'gecmis' && (
                                <div className="modal-inner-section">
                                    {status === 'pending' ? (
                                        <div className="empty-state" style={{ padding: '60px 20px' }}>
                                            <Loader2 size={40} color="#7c3aed" className="animate-spin" />
                                            <br /><br />Analiz geçmişi yükleniyor...
                                        </div>
                                    ) : history.length === 0 ? (
                                        <div className="empty-state"><Clock size={40} /><br />Arama geçmişiniz temiz.</div>
                                    ) : (
                                        <div className="modal-card-grid card-grid">
                                            {history.map((h) => {
                                                const matchedProduct = flatProducts.find((p) => p.name === h);
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
            <div style={{ height: 80 }} />
        </div>
    );
}