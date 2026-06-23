import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
    ArrowLeft, Heart, Star, ChevronDown, ChevronUp, ShieldCheck, CheckCircle2,
    Clock, ThumbsUp, Sparkles, CheckCircle, Info, TrendingUp,
    MessageCircle, X, Send, Bot, MoreHorizontal, Loader2, HelpCircle
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './ProductPage.css';
import ProductCard from './ProductCard';
import api, { sendChatMessageToVividBot } from '../api';

// ── DİNAMİK GERÇEK PLATFORM RENK HARİTASI ──
const PLATFORM_THEMES = {
    'trendyol': { main: '#F27A1A', light: '#fff4eb' },
    'trendyolgo': { main: '#0cc167', light: '#e8faef' },
    'yemeksepeti': { main: '#EA004B', light: '#ffeef3' },
    'maps': { main: '#4285F4', light: '#e8f0fe' },
    'airbnb': { main: '#FF5A5F', light: '#ffeeef' },
    'hepsiburada': { main: '#FF6000', light: '#fff4eb' },
    'steam': { main: '#2A475E', light: '#f1f5f9' },
    'etstur': { main: '#009FDF', light: '#f0f9ff' },
    'ciceksepeti': { main: '#028139', light: '#f0fdf4' },
    'default': { main: '#8b5cf6', light: '#f5f3ff' }
};

// ── GRAFİK İÇİN ÖZEL TOOLTIP (Dışarıya Alındı - React Performansı İçin) ──
const CustomTooltip = ({ active, payload, label, activeTheme }) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        return (
            <div style={{
                background: '#fff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '10px',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)'
            }}>
                <p style={{ margin: 0, fontWeight: 600, color: '#1e293b', fontSize: '12px' }}>{label}</p>
                <p style={{ margin: '4px 0', color: activeTheme?.main || '#8b5cf6', fontWeight: 'bold', fontSize: '15px' }}>
                    {data.averageScore.toFixed(1)} ⭐
                </p>
                <p style={{ margin: 0, color: '#64748b', fontSize: '11px' }}>
                    {data.reviewCount} Değerlendirme
                </p>
            </div>
        );
    }
    return null;
};

// YENİ EKLENEN FAVORİLER PARAMETRESİ BURADA (favorites = [])
export default function ProductPage({ product, onFav, onClose, userRating, onRate, allProducts = [], openProduct, ratings = {}, favorites = [] }) {
    // ── API VERİ STATE'LERİ ──
    const [productDetail, setProductDetail] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    // ── TREND ANALİZİ STATE'LERİ ──
    const [trendData, setTrendData] = useState(null);
    const [trendLoading, setTrendLoading] = useState(false);

    // ── UI STATE'LERİ ──
    const [hoveredStar, setHoveredStar] = useState(0);
    const [expandedParam, setExpandedParam] = useState(null);
    const [selectedWord, setSelectedWord] = useState(null);
    const [hoveredWord, setHoveredWord] = useState(null);

    // ── CHATBOT STATE'LERİ ──
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [isTyping, setIsTyping] = useState(false);
    const [chatMessages, setChatMessages] = useState([]);
    const [chatInput, setChatInput] = useState('');
    const chatEndRef = useRef(null);

    // ── KATEGORİ FORMATLAYICI ──
    const formatCategory = (rawCat) => {
        if (!rawCat) return 'Diğer';
        const str = rawCat.toLowerCase().replace(/_/g, ' ');
        if (str.includes('elektronik') || str.includes('teknoloji')) return 'Elektronik & Teknoloji';
        if (str.includes('kırtasiye') || str.includes('kirtasiye') || str.includes('kitap') || str.includes('hobi')) return 'Kırtasiye & Kitap & Hobi';
        if (str.includes('otel') || str.includes('konaklama')) return 'Otel';
        if (str.includes('günlük ev') || str.includes('gunluk')) return 'Günlük Ev';
        if (str.includes('giyim') || str.includes('ayakkabı') || str.includes('ayakkabi')) return 'Giyim & Ayakkabı';
        if (str.includes('eğitim') || str.includes('egitim') || str.includes('eğlence')) return 'Eğitim & Eğlence';
        if (str.includes('sağlık') || str.includes('saglik')) return 'Sağlık';
        if (str.includes('oyun') || str.includes('game')) return 'Oyun';
        if (str.includes('yemek') || str.includes('restoran')) return 'Yemek';
        if (str.includes('gezi') || str.includes('gezilecek')) return 'Gezilecek Yer';
        if (str.includes('anne') || str.includes('bebek') || str.includes('oyuncak')) return 'Anne & Bebek & Oyuncak';
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
        return rawCat.charAt(0).toUpperCase() + rawCat.slice(1);
    };

    // ── YENİ API İSTEKLERİ (TIKLAMA & FAVORİ) ──
    const handleIncrementClick = useCallback(async () => {
        try {
            if (product?.id) {
                await api.patch(`/Product/${product.id}/click`);
            }
        } catch (error) {
            console.error("Tıklama sayısı güncellenemedi:", error);
        }
    }, [product]);

    const handleToggleSave = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await api.post(`/Product/${product.id}/toggle-save`, {}, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 200) {
                const newSaveStatus = response.data.isSaved !== undefined ? response.data.isSaved : response.data.IsSaved;
                setProductDetail(prev => ({ ...prev, isFavorited: newSaveStatus }));

                const updatedProductForDashboard = {
                    id: productDetail.id,
                    name: productDetail.productName,
                    category: productDetail.category,
                    plat: productDetail.platform,
                    avgScore: productDetail.avgModelScore ? productDetail.avgModelScore.toFixed(1) : "0.0",
                    img: productDetail.imageUrl,
                    clickCount: productDetail.clickCount || 0,
                    isFavorited: newSaveStatus
                };

                if (onFav) {
                    onFav(updatedProductForDashboard, true);
                }
            }
        } catch (error) {
            console.error("Favori işlemi başarısız:", error);
        }
    };

    // ── API VE TREND VERİSİNİ ÇEKME ──
    useEffect(() => {
        // Fonksiyonları Effect'in İÇİNDE tanımlıyoruz (React'in en sevdiği yöntem)
        const fetchProductDetails = async () => {
            if (!product?.id) return;
            setIsLoading(true);
            try {
                const token = localStorage.getItem('token');
                const response = await api.get(`/Product/${product.id}`, {
                    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
                });
                setProductDetail(response.data);

                setChatMessages([
                    { sender: 'ai', text: `Merhaba! Ben VividAI Asistan. 👋 ${response.data.productName} hakkında merak ettiklerini bana sorabilirsin.` }
                ]);
            } catch (error) {
                console.error("Ürün detayları yüklenirken hata oluştu:", error);
            } finally {
                setIsLoading(false);
            }
        };

        const fetchTrendData = async () => {
            if (!product?.id) return;
            setTrendLoading(true);
            try {
                const response = await api.get(`/Product/${product.id}/trend`);
                setTrendData(response.data);
            } catch (error) {
                console.error("Trend verisi alınamadı:", error);
            } finally {
                setTrendLoading(false);
            }
        };

        // Ve tanımladığımız fonksiyonları çağırıyoruz
        fetchProductDetails();
        fetchTrendData();
        
    }, [product?.id]); // Sadece product.id değiştiğinde tetiklenecek

    useEffect(() => {
        handleIncrementClick();
    }, [handleIncrementClick]);

    useEffect(() => {
        if (isChatOpen && chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [chatMessages, isChatOpen, isTyping]);

    const getPlatformTheme = (platName) => {
        if (!platName) return PLATFORM_THEMES['default'];
        const str = platName.toLowerCase().replace(/\s+/g, '');
        const match = Object.keys(PLATFORM_THEMES).find(key => str.includes(key));
        return match ? PLATFORM_THEMES[match] : PLATFORM_THEMES['default'];
    };

    const cleanToken = (word) => word.toLowerCase().replace(/[.,/#!$%^&*;:{}=\-_`~()]/g, "").trim();
    const isStopWord = (word) => ['ve', 'veya', 'da', 'de', 'bir', 'bu', 'için', 'en', 'ile', 'o', 'ise', 'içinde', 'çok', 'daha', 'gibi'].includes(cleanToken(word));

    const handleWordClick = (word) => {
        const clean = cleanToken(word);
        if (isStopWord(clean)) return;
        setSelectedWord(selectedWord === clean ? null : clean);
    };

    const handleSendMessage = async (e) => {
        e.preventDefault();
        
        // Koruma kalkanı: Mesaj boşsa veya ürün yüklenemediyse isteği durdur
        if (!chatInput.trim() || !productDetail?.id) return;

        const userQuestion = chatInput.trim();

        // 1. Kullanıcının yazdığı soruyu arayüz baloncuğuna anında ekliyoruz
        const newUserMsg = { sender: 'user', text: userQuestion };
        setChatMessages(prev => [...prev, newUserMsg]);
        
        // Input kutusunu temizliyoruz
        setChatInput('');
        
        // 2. Üç nokta yanıp sönen "Yazıyor..." animasyonunu aktif ediyoruz
        setIsTyping(true);

        try {
            // 3. Bizim api.js içerisindeki asıl RAG bağlantı fonksiyonumuzu ateşliyoruz
            const botResponse = await sendChatMessageToVividBot(productDetail.id, userQuestion);
            
            // 4. FastAPI'den gelen o kurallı Türkçe cevabı ekrandaki bot baloncuğuna basıyoruz
            setChatMessages(prev => [...prev, {
                sender: 'ai',
                text: botResponse
            }]);
            
        } catch (error) {
            console.error("Chatbot akışında hata:", error);
            setChatMessages(prev => [...prev, {
                sender: 'ai',
                text: "Şu anda teknik bir aksaklık nedeniyle yanıt üretemiyorum. Lütfen biraz sonra tekrar deneyin."
            }]);
        } finally {
            // 5. İşlem başarılı da olsa hata da alsa "Yazıyor..." animasyonunu kapatıyoruz
            setIsTyping(false);
        }
    };

    if (!product) return null;

    if (isLoading) {
        return (
            <div className="tc-page-wrapper" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh', flexDirection: 'column', gap: '15px' }}>
                <Loader2 size={48} color="#8b5cf6" className="animate-spin" />
                <h3 style={{ color: '#475569' }}>VividAI Analiz Raporu Yükleniyor...</h3>
            </div>
        );
    }

    if (!productDetail) {
        return (
            <div className="tc-page-wrapper" style={{ padding: '40px', textAlign: 'center' }}>
                <h2>Ürün detayları bulunamadı.</h2>
                <button className="tc-btn-primary" onClick={onClose} style={{ marginTop: '20px' }}>Geri Dön</button>
            </div>
        );
    }

    const {
        productName, platform, imageUrl, originalUrl,
        avgOrjScore, avgModelScore, celiskiScore,
        guncelOzet, categoricalStats, sourceReviews, isFavorited
    } = productDetail;

    const activeTheme = getPlatformTheme(platform);
    const summaryWords = (guncelOzet || "").split(/\s+/);
    const activeTargetWord = hoveredWord || selectedWord;

    const displayPlatform = platform ? platform.charAt(0).toUpperCase() + platform.slice(1) : '';

    const similarProducts = allProducts
        .filter((p) => {
            if (!p.category || !productDetail?.category) return false;
            const dashboardCat = p.category;
            const currentProductCat = formatCategory(productDetail.category);
            return dashboardCat === currentProductCat && p.id !== productDetail.id;
        })
        .slice(0, 6);

    const renderInteractiveSummary = (textArray) => {
        return textArray.map((word, idx) => {
            const clean = cleanToken(word);
            const stopWord = isStopWord(word);
            const isGlow = !stopWord && (hoveredWord === clean || selectedWord === clean);
            const isLocked = !stopWord && selectedWord === clean;

            return (
                <span
                    key={idx}
                    className={`tc-dynamic-word ${isGlow ? 'active' : ''} ${isLocked ? 'locked' : ''} ${stopWord ? 'stop-word' : ''}`}
                    onMouseEnter={() => { if (!stopWord) setHoveredWord(clean); }}
                    onMouseLeave={() => { setHoveredWord(null); }}
                    onClick={() => handleWordClick(word)}
                >
                    {word}{' '}
                </span>
            );
        });
    };

    const renderHighlightedCommentText = (text, targetWord) => {
        if (!targetWord) return text;
        const regex = new RegExp(`(${targetWord})`, 'gi');
        const parts = text.split(regex);
        return parts.map((part, i) =>
            part.toLowerCase() === targetWord.toLowerCase() ?
                <span key={i} className="tc-word-highlight-match">{part}</span> : part
        );
    };

    return (
        <div className="tc-page-wrapper" style={{ '--theme-main': activeTheme.main, '--theme-light': activeTheme.light }}>

            <div className="tc-top-bar">
                <button className="tc-back-btn" onClick={onClose}>
                    <ArrowLeft size={16} /> Keşif Paneline Dön
                </button>
                <div className="tc-breadcrumb">
                    Anasayfa {'>'} {formatCategory(productDetail.category)} {'>'} <span>{productName}</span>
                </div>
            </div>

            <div className="tc-main-grid">
                {/* 1. SOL: RESİM & AI ÖZETİ */}
                <div className="tc-image-column">
                    <div className="tc-main-image-box">
                        <img src={imageUrl || product.img} alt={productName} />
                        <div className="tc-image-badges">
                            <span className="tc-badge-ai">VividAI </span>
                        </div>
                    </div>

                    <div className="tc-ai-summary-box">
                        <div className="tc-ai-summary-header">
                            <Sparkles size={16} color={activeTheme.main} />
                            <strong>{displayPlatform} Verisi Sentez Raporu</strong>
                        </div>
                        <p className="tc-interactive-text">
                            {renderInteractiveSummary(summaryWords)}
                        </p>
                        <div className="tc-summary-hint">
                            * Özetteki kelimelerin hangi yorumlardan geldiğini görmek için kelimelere tıklayın veya üzerine gelin.
                        </div>
                    </div>
                </div>

                {/* 2. ORTA: DETAYLAR & KAYNAK YORUMLAR */}
                <div className="tc-details-column">
                    <div className="tc-product-header">
                        <h1 className="tc-product-title">
                            <span className="tc-brand">{displayPlatform}</span> {productName}
                        </h1>
                        <div className="tc-rating-summary">
                            <div className="tc-stars">
                                {[...Array(5)].map((_, i) => (
                                    <Star key={i} size={14} fill={activeTheme.main} color={activeTheme.main} />
                                ))}
                            </div>
                            <span className="tc-rating-count">Orijinal Puan: {avgOrjScore?.toFixed(1)}</span>
                            <div className="tc-tooltip-wrap">
                                <HelpCircle size={14} className="tc-help-icon" />
                                <div className="tc-tooltip-content">
                                    <strong>Orijinal Puan:</strong> {displayPlatform} platformunda yer alan ham, müdahale edilmemiş ortalama kullanıcı puanıdır.
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="tc-score-cards-row">
                        <div className="tc-score-card">
                            <div className="tc-score-top" style={{ display: 'flex', alignItems: 'center' }}>
                                <span className="tc-score-val" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    {avgModelScore?.toFixed(1)}
                                </span>
                                <div className="tc-score-labels">
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                        <strong>VividAI Endeksi</strong>
                                        <div className="tc-tooltip-wrap">
                                            <HelpCircle size={12} className="tc-help-icon" />
                                            <div className="tc-tooltip-content">
                                                <strong>VividAI Endeksi:</strong> LLM motorumuzun yorumları doğal dil işleme ile analiz ederek hesapladığı ağırlıklı, gerçek kullanıcı memnuniyet skorudur. Manipülatif yorumlar filtrelenerek oluşturulur.
                                            </div>
                                        </div>
                                    </div>
                                    <span>Anlamsal Model Skoru</span>
                                </div>
                            </div>
                        </div>
                        <div className="tc-score-card">
                            <div className="tc-score-top" style={{ display: 'flex', alignItems: 'center' }}>
                                <span className="tc-score-val-alt" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <span style={{ fontSize: '15px', marginRight: '4px' }}>%</span>
                                    <span>{celiskiScore ? (celiskiScore * 100).toFixed(0) : "0"}</span>
                                </span>
                                <div className="tc-score-labels">
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                        <strong>Çelişki Oranı</strong>
                                        <div className="tc-tooltip-wrap">
                                            <HelpCircle size={12} className="tc-help-icon" />
                                            <div className="tc-tooltip-content">
                                                <strong>Çelişki Oranı:</strong> Kullanıcı deneyimlerindeki duygu zıtlıklarını ölçer. Oranın yüksek olması, ürünü çok sevenler kadar nefret edenlerin de olduğunu (standart sapmanın yüksek olduğunu) gösterir.
                                            </div>
                                        </div>
                                    </div>
                                    <span>Yorum Standart Sapması</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="tc-specs-section">
                        <div className="tc-specs-title-group">
                            <TrendingUp size={16} color={activeTheme.main} />
                            <h3 className="tc-section-title">Kategorik Özet Parametreleri</h3>
                        </div>
                        <div className="tc-params-list">
                            {categoricalStats && categoricalStats.length > 0 ? (
                                categoricalStats.map((stat, idx) => {
                                    const isExpanded = expandedParam === idx;
                                    return (
                                        <div key={idx} className={`tc-param-row-wrapper ${isExpanded ? 'active-row' : ''}`}>
                                            <div className="tc-param-clickable-row" onClick={() => setExpandedParam(isExpanded ? null : idx)}>
                                                <div className="tc-param-left">
                                                    <div className="tc-icon-frame"><CheckCircle2 size={14} /></div>
                                                    <span className="tc-param-label">{formatCategory(stat.categoryName)}</span>
                                                </div>
                                                <div className="tc-param-right">
                                                    <div className="tc-progress-bg">
                                                        <div className="tc-progress-fill" style={{ width: `${(stat.categoryModelAvgScore / 5) * 100}%` }}></div>
                                                    </div>
                                                    <span className="tc-param-score">
                                                        {stat.categoryModelAvgScore ? (stat.categoryModelAvgScore * 20).toFixed(0) : "0"}%
                                                    </span>
                                                    {isExpanded ? <ChevronUp size={16} color={activeTheme.main} /> : <ChevronDown size={16} color="#64748b" />}
                                                </div>
                                            </div>
                                            {isExpanded && (
                                                <div className="tc-param-expanded-content">
                                                    <p className="tc-expanded-text">{stat.categorySummary}</p>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })
                            ) : (
                                <p className="tc-expanded-text" style={{ padding: '10px 0' }}>Bu ürün için kategorik detay henüz oluşturulmadı.</p>
                            )}
                        </div>
                    </div>

                    <div className="tc-reviews-section">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                            <h3 className="tc-section-title" style={{ margin: 0 }}>Özeti Oluşturan Kaynak Yorumlar</h3>
                            {selectedWord && (
                                <button className="tc-clear-filter" onClick={() => setSelectedWord(null)}>
                                    Seçimi Temizle
                                </button>
                            )}
                        </div>

                        <div className="tc-reviews-scroll-box">
                            {sourceReviews && sourceReviews.length > 0 ? (
                                sourceReviews.map((review, idx) => {
                                    const textLower = review.text.toLocaleLowerCase('tr-TR');
                                    const targetLower = activeTargetWord ? activeTargetWord.toLocaleLowerCase('tr-TR') : '';
                                    const isMatch = activeTargetWord && textLower.includes(targetLower);
                                    let cardStateClass = activeTargetWord ? (isMatch ? 'tc-card-highlight' : 'tc-card-dimmed') : '';

                                    return (
                                        <div key={idx} className={`tc-review-card-mini ${cardStateClass}`}>
                                            <div className="tc-review-header-mini">
                                                <span className="tc-review-user-masked">Doğrulanmış Alıcı</span>
                                            </div>
                                            <p className="tc-interactive-text-mini">
                                                {activeTargetWord && isMatch
                                                    ? renderHighlightedCommentText(review.text, activeTargetWord)
                                                    : review.text}
                                            </p>
                                        </div>
                                    )
                                })
                            ) : (
                                <p className="tc-expanded-text">Gösterilecek kaynak yorum bulunamadı.</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* 3. SAĞ: SATICI VE AKSİYONLAR */}
                <div className="tc-action-column">
                    <div className="tc-seller-box">
                        <div className="tc-seller-header">
                            <span className="tc-seller-name">{displayPlatform}</span>
                            <span className="tc-seller-badge"><CheckCircle size={12} /> Orijinal Kaynak</span>
                        </div>
                        <div className="tc-seller-info-row">
                            <Info size={14} color={activeTheme.main} />
                            <span>Bu analiz, {displayPlatform} üzerindeki açık veriler kullanılarak oluşturulmuştur.</span>
                        </div>
                    </div>

                    {originalUrl && (
                        <a href={originalUrl} target="_blank" rel="noreferrer" className="tc-btn-primary">
                            Mağazaya Git ve İncele
                        </a>
                    )}

                    <button className={`tc-btn-secondary ${isFavorited ? 'fav-active' : ''}`} onClick={handleToggleSave}>
                        <Heart size={16} fill={isFavorited ? activeTheme.main : 'none'} color={isFavorited ? activeTheme.main : '#475569'} />
                        {isFavorited ? 'Koleksiyona Eklendi' : 'Koleksiyona Ekle'}
                    </button>

                    <div className="tc-rate-box">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <strong>Model Çıktısını Değerlendir</strong>
                            <div className="tc-tooltip-wrap">
                                <HelpCircle size={14} className="tc-help-icon" />
                                <div className="tc-tooltip-content" style={{ right: 0, transform: 'translateX(0)', left: 'auto' }}>
                                    <strong>Geri Bildirim Sistemi:</strong> AI modelimizin analiz başarısını puanlayarak algoritmamızın öğrenme sürecine ve doğruluğunun artmasına doğrudan katkı sağlayabilirsiniz.
                                </div>
                            </div>
                        </div>
                        {userRating ? (
                            <div className="tc-rate-success">Geri Bildirim Alındı ({userRating} Yıldız)</div>
                        ) : (
                            <div className="tc-rate-stars">
                                {[1, 2, 3, 4, 5].map((s) => (
                                    <Star
                                        key={s} size={20}
                                        fill={hoveredStar >= s ? activeTheme.main : 'none'}
                                        color={hoveredStar >= s ? activeTheme.main : '#cbd5e1'}
                                        onMouseEnter={() => setHoveredStar(s)}
                                        onMouseLeave={() => setHoveredStar(0)}
                                        onClick={() => onRate && onRate(productDetail.id, s)}
                                        style={{ cursor: 'pointer', transition: 'transform 0.1s' }}
                                    />
                                ))}
                            </div>
                        )}
                    </div>

                    {/* ZAMAN BAZLI TREND KARTI / GRAFİĞİ */}
                    {trendLoading ? (
                        <div className="tc-trend-box" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '20px' }}>
                            <Loader2 size={20} color={activeTheme?.main || '#8b5cf6'} className="animate-spin" />
                            <span style={{ marginLeft: '8px', fontSize: '12px', color: '#64748b' }}>Trend hesaplanıyor...</span>
                        </div>
                    ) : trendData && trendData.trends && trendData.trends.length > 0 ? (
                        <div className="tc-trend-box">
                            <div className="tc-trend-header">
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <TrendingUp size={16} color={activeTheme?.main || '#8b5cf6'} />
                                    <strong>
                                        {trendData.periodType === "SinglePoint" ? "Genel Puan Dağılımı" :
                                            trendData.periodType === "Monthly" ? "Aylık Trend" :
                                                trendData.periodType === "Quarterly" ? "Çeyreklik Trend" :
                                                    "Yıllık Trend"}
                                    </strong>
                                </div>
                            </div>

                            {/* DİNAMİK RENDER */}
                            {trendData.trends.length === 1 ? (
                                <div style={{ background: activeTheme?.light || '#f5f3ff', borderRadius: '8px', padding: '16px', textAlign: 'center', marginTop: '10px' }}>
                                    <div style={{ fontSize: '24px', fontWeight: 'bold', color: activeTheme?.main || '#8b5cf6' }}>
                                        {trendData.trends[0].averageScore.toFixed(1)} ⭐
                                    </div>
                                    <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px', fontWeight: '500' }}>
                                        {trendData.trends[0].periodLabel} Genel Ortalaması
                                    </div>
                                    <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '6px' }}>
                                        {trendData.trends[0].reviewCount} Toplam Değerlendirme
                                    </div>
                                </div>
                            ) : (
                                <div className="tc-trend-chart-wrapper" style={{ width: '100%', height: '220px', marginTop: '10px' }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <AreaChart
                                            data={trendData.trends}
                                            margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
                                        >
                                            <defs>
                                                <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor={activeTheme?.main || '#8b5cf6'} stopOpacity={0.6} />
                                                    <stop offset="95%" stopColor={activeTheme?.main || '#8b5cf6'} stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                            <XAxis
                                                dataKey="periodLabel"
                                                axisLine={false}
                                                tickLine={false}
                                                tick={{ fontSize: 10, fill: '#94a3b8' }}
                                                dy={10}
                                            />
                                            <YAxis
                                                domain={[1, 5]}
                                                axisLine={false}
                                                tickLine={false}
                                                tick={{ fontSize: 10, fill: '#94a3b8' }}
                                                tickCount={5}
                                            />
                                            <Tooltip content={(props) => <CustomTooltip {...props} activeTheme={activeTheme} />} />
                                            <Area
                                                type="monotone"
                                                dataKey="averageScore"
                                                stroke={activeTheme?.main || '#8b5cf6'}
                                                strokeWidth={3}
                                                fillOpacity={1}
                                                fill="url(#colorScore)"
                                                activeDot={{ r: 6, strokeWidth: 0, fill: activeTheme?.main || '#8b5cf6' }}
                                            />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </div>
                            )}
                        </div>
                    ) : null}

                </div>
            </div>

            {/* 4. BENZER ÜRÜNLER (YATAY SCROLL / KAYDIRMALI) - FAVORİLER DİNAMİK YAPILDI */}
            <div className="tc-similar-section">
                <h2 className="tc-similar-title">Kategorideki Benzer Ürünler</h2>
                <div className="tc-similar-scroll-container">
                    {similarProducts.length > 0 ? (
                        similarProducts.map(item => (
                            <div key={item.id} className="tc-similar-card-wrapper">
                                <ProductCard
                                    item={item}
                                    isFav={favorites.some((f) => f.id === item.id)} // BURASI GÜNCELLENDİ
                                    onFav={onFav}
                                    onClick={() => {
                                        window.scrollTo({ top: 0, behavior: 'smooth' });
                                        openProduct(item);
                                    }}
                                    userRating={ratings[item.id]}
                                />
                            </div>
                        ))
                    ) : (
                        <p style={{ color: '#64748b' }}>Bu kategoride başka ürün bulunamadı.</p>
                    )}
                </div>
            </div>

            {/* CHATBOT FAB & MODAL */}
            <button className={`tc-chatbot-fab ${isChatOpen ? 'hidden' : ''}`} onClick={() => setIsChatOpen(true)}>
                <Bot size={28} />
            </button>

            <div className={`tc-chatbot-modal ${isChatOpen ? 'open' : ''}`}>
                <div className="tc-chatbot-header">
                    <div className="tc-chatbot-header-left">
                        <div className="tc-bot-avatar-container">
                            <Bot size={22} />
                            <div className="tc-bot-online-dot"></div>
                        </div>
                        <div className="tc-chatbot-title-box">
                            <span className="tc-chatbot-title">VividAI Asistan</span>
                            <span className="tc-chatbot-subtitle">Sizin için burada</span>
                        </div>
                    </div>
                    <button className="tc-chatbot-close" onClick={() => setIsChatOpen(false)}>
                        <X size={20} />
                    </button>
                </div>

                <div className="tc-chatbot-body">
                    <div className="tc-chat-disclaimer">
                        Gerçek zamanlı AI analiz asistanı ile görüşüyorsunuz.
                    </div>
                    {chatMessages.map((msg, idx) => (
                        <div key={idx} className={`tc-chat-bubble ${msg.sender}`}>
                            {msg.text}
                        </div>
                    ))}

                    {isTyping && (
                        <div className="tc-chat-bubble ai typing">
                            <MoreHorizontal size={20} className="tc-typing-icon" />
                        </div>
                    )}

                    <div ref={chatEndRef} />
                </div>

                <form className="tc-chatbot-footer" onSubmit={handleSendMessage}>
                    <input
                        type="text"
                        placeholder="Bir şeyler sorun..."
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                    />
                    <button type="submit" disabled={!chatInput.trim()} className={chatInput.trim() ? 'active' : ''}>
                        <Send size={18} />
                    </button>
                </form>
            </div>
        </div>
    );
}
