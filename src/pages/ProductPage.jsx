import React, { useState, useMemo } from 'react';
import {
    ArrowLeft,
    Heart,
    Star,
    ExternalLink,
    ChevronDown,
    ChevronUp,
    ShieldCheck,
    CheckCircle2,
    Clock,
    ThumbsUp,
    MessageSquare,
    Sparkles,
    CheckCircle,
    Info,
    TrendingUp
} from 'lucide-react';
import './ProductPage.css';
import ProductCard from './ProductCard';

// ── DİNAMİK GERÇEK PLATFORM RENK HARİTASI ──
const PLATFORM_THEMES = {
    'trendyol': { main: '#F27A1A', light: '#fff4eb' },      // Trendyol Turuncusu
    'trendyolgo': { main: '#0cc167', light: '#e8faef' },    // Trendyol Go Turuncusu
    'yemeksepeti': { main: '#EA004B', light: '#ffeef3' },   // Yemeksepeti Pembesi
    'googlemaps': { main: '#4285F4', light: '#e8f0fe' },   // Google Yeşili
    'airbnb': { main: '#FF5A5F', light: '#ffeeef' },        // Airbnb Kırmızı/Mercan
    'hepsiburada': { main: '#FF6000', light: '#fff4eb' },   // Hepsiburada Turuncusu
    'steam': { main: '#2A475E', light: '#f1f5f9' },         // Steam Laciverti
    'etstur': { main: '#009FDF', light: '#f0f9ff' },        // Etstur Turkuaz
    'ciceksepeti': { main: '#028139', light: '#f0fdf4' },   // Çiçeksepeti Yeşili
    'default': { main: '#8b5cf6', light: '#f5f3ff' }        // VividAI Moru
};

const CATEGORY_DETAILS = {
    'Yemek & Gıda': [
        { key: 'lezzet', label: 'Lezzet Oranı', score: 4.8, icon: ThumbsUp, desc: 'Kullanıcı yorumlarının genel analizi sos dengesi ve malzeme tazeliğini başarılı buluyor.' },
        { key: 'hiz', label: 'Teslimat Hızı', score: 4.2, icon: Clock, desc: 'Siparişlerin ortalama varış süresi lojistik standartlara tam uyum sağlıyor.' },
        { key: 'kurye', label: 'Kurye & Paketleme', score: 4.5, icon: CheckCircle2, desc: 'Sıcaklığı koruyan özel ambalaj yapısı ve kurye memnuniyeti yüksek.' }
    ],
    'Elektronik & Teknoloji': [
        { key: 'ses', label: 'Ses Kalitesi & ANC', score: 4.9, icon: ThumbsUp, desc: 'Aktif gürültü engelleme performansı ve bas dengesi üst düzeyde raporlanmış.' },
        { key: 'pil', label: 'Pil Ömrü & Şarj', score: 4.7, icon: Clock, desc: 'Tek şarjla uzun süreli kesintisiz kullanım verisi doğrulanmış durumda.' },
        { key: 'ergonomi', label: 'Ergonomi & Konfor', score: 4.6, icon: ShieldCheck, desc: 'Kulak yastıklarının kafa yapısına tam uyum sağladığı belirtilmiş.' }
    ],
    default: [
        { key: 'fp', label: 'Fiyat / Performans', score: 4.5, icon: ThumbsUp, desc: 'Harcanan bütçenin karşılığını verimlilik bazında optimum eğride karşılıyor.' },
        { key: 'kalite', label: 'Genel Kalite Algısı', score: 4.4, icon: ShieldCheck, desc: 'Kullanıcı deneyimi standartların üzerinde, güvenilir bir his uyandırıyor.' }
    ]
};

const MOCK_XAI_COMMENTS = {
    1: [
        { id: 101, user: "Ahmet K.", date: "12.05.2026", sentiment: "positive", text: "Hayatımda gördüğüm en iyi gürültü engelleme teknolojisine sahip. Müzik dinlerken ses kalitesi muazzam berrak." },
        { id: 102, user: "Zeynep T.", date: "02.05.2026", sentiment: "negative", text: "Ses harika ancak uzun kullanımda kulaklarımda ağrı yaptı. Konfor ve ergonomi bence zayıf." }
    ],
    3: [
        { id: 301, user: "Selin B.", date: "29.04.2026", sentiment: "positive", text: "Burger köftesi sıcacık geldi. Gerçekten tam bir lezzet şöleni, porsiyon büyüklüğü çok tatmin edici." },
        { id: 302, user: "Berk G.", date: "18.04.2026", sentiment: "negative", text: "Yemek tam 1 saatte ulaştı. Teslimat süresi ve hız performansı korkunç derecede yavaş." }
    ],
    'default': [
        { id: 901, user: "Kullanıcı A.", date: "01.05.2026", sentiment: "positive", text: "Genel olarak performansı çok iyi ve kalitesi yüksek, kesinlikle tavsiye ederim." }
    ]
};

function ProductPage({ product, isFav, onFav, onClose, userRating, onRate, allProducts = [], openProduct, favorites = [], ratings = {} }) {
    const [hoveredStar, setHoveredStar] = useState(0);
    const [expandedParam, setExpandedParam] = useState(null);
    const [selectedWord, setSelectedWord] = useState(null);
    const [hoveredWord, setHoveredWord] = useState(null);

    if (!product) return null;

    // ── PLATFORM TESPİT ALGORTİMASI ──
    const getPlatformTheme = (platName) => {
        if (!platName) return PLATFORM_THEMES['default'];
        const str = platName.toLowerCase().replace(/\s+/g, '');
        if (str.includes('trendyolgo')) return PLATFORM_THEMES['trendyolgo'];
        if (str.includes('trendyol')) return PLATFORM_THEMES['trendyol'];
        if (str.includes('yemeksepeti')) return PLATFORM_THEMES['yemeksepeti'];
        if (str.includes('google')) return PLATFORM_THEMES['googlemaps'];
        if (str.includes('airbnb')) return PLATFORM_THEMES['airbnb'];
        if (str.includes('hepsiburada')) return PLATFORM_THEMES['hepsiburada'];
        if (str.includes('steam')) return PLATFORM_THEMES['steam'];
        if (str.includes('etstur')) return PLATFORM_THEMES['etstur'];
        if (str.includes('çiçeksepeti') || str.includes('ciceksepeti')) return PLATFORM_THEMES['ciceksepeti'];
        return PLATFORM_THEMES['default'];
    };

    const activeTheme = getPlatformTheme(product.plat);

    const cleanToken = (word) => word.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, "").trim();
    const isStopWord = (word) => ['ve', 'veya', 'da', 'de', 'bir', 'bu', 'tarafından', 'için', 'en', 'ile', 'o', 'ise', 'içinde'].includes(cleanToken(word));

    const aiModelScore = useMemo(() => (product.avgScore - 0.2).toFixed(1), [product.avgScore]);
    const varianceScore = useMemo(() => {
        const diff = Math.abs(product.avgScore - aiModelScore);
        return Math.min(94, Math.max(8, (diff * 40) + 12)).toFixed(0);
    }, [product.avgScore, aiModelScore]);

    const similarProducts = useMemo(() => {
        return allProducts
            .filter((p) => p.category === product.category && p.id !== product.id)
            .slice(0, 6);
    }, [allProducts, product.category, product.id]);

    const params = CATEGORY_DETAILS[product.category] || CATEGORY_DETAILS.default;
    const comments = MOCK_XAI_COMMENTS[product.id] || MOCK_XAI_COMMENTS.default;
    const summaryWords = useMemo(() => product.sum.split(/\s+/), [product.sum]);

    const filteredComments = useMemo(() => {
        if (!selectedWord) return comments;
        return comments.filter(comment =>
            comment.text.toLowerCase().replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, "").split(/\s+/).includes(selectedWord)
        );
    }, [selectedWord, comments]);

    const handleWordClick = (word) => {
        const clean = cleanToken(word);
        if (isStopWord(clean)) return;
        setSelectedWord(selectedWord === clean ? null : clean);
    };

    const renderInteractiveWords = (textArray) => {
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

    return (
        // CSS Değişkenlerini (Variables) En Üst Kapsayıcıya Enjekte Ediyoruz
        <div
            className="tc-page-wrapper"
            style={{
                '--theme-main': activeTheme.main,
                '--theme-light': activeTheme.light
            }}
        >
            {/* ÜST BİLGİ ÇUBUĞU */}
            <div className="tc-top-bar">
                <button className="tc-back-btn" onClick={onClose}>
                    <ArrowLeft size={16} /> Keşif Paneline Dön
                </button>
                <div className="tc-breadcrumb">
                    Anasayfa {'>'} {product.category} {'>'} <span>{product.name}</span>
                </div>
            </div>

            {/* ANA 3'LÜ YERLEŞİM */}
            <div className="tc-main-grid">

                {/* 1. SOL: TEK RESİM */}
                <div className="tc-image-column">
                    <div className="tc-main-image-box">
                        <img src={product.img} alt={product.name} />
                        <div className="tc-image-badges">
                            <span className="tc-badge-ai">VividAI Analizör</span>
                        </div>
                    </div>
                </div>

                {/* 2. ORTA: DETAYLAR */}
                <div className="tc-details-column">
                    <div className="tc-product-header">
                        <h1 className="tc-product-title">
                            <span className="tc-brand">{product.plat}</span> {product.name}
                        </h1>
                        <div className="tc-rating-summary">
                            <div className="tc-stars">
                                <Star size={14} fill={activeTheme.main} color={activeTheme.main} />
                                <Star size={14} fill={activeTheme.main} color={activeTheme.main} />
                                <Star size={14} fill={activeTheme.main} color={activeTheme.main} />
                                <Star size={14} fill={activeTheme.main} color={activeTheme.main} />
                                <Star size={14} fill={activeTheme.main} color={activeTheme.main} />
                            </div>
                            <span className="tc-rating-count">Platform Puanı: {product.avgScore}</span>
                        </div>
                    </div>

                    <div className="tc-score-cards-row">
                        <div className="tc-score-card">
                            <div className="tc-score-top">
                                <span className="tc-score-val">{aiModelScore}</span>
                                <div className="tc-score-labels">
                                    <strong>VividAI Endeksi</strong>
                                    <span>Anlamsal Model Skoru</span>
                                </div>
                            </div>
                        </div>
                        <div className="tc-score-card">
                            <div className="tc-score-top">
                                <span className="tc-score-val-alt">% {varianceScore}</span>
                                <div className="tc-score-labels">
                                    <strong>Çelişki Oranı</strong>
                                    <span>Yorum Standart Sapması</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* KATEGORİK ÖZET DETAYLARI */}
                    <div className="tc-specs-section">
                        <div className="tc-specs-title-group">
                            <TrendingUp size={16} color={activeTheme.main} />
                            <h3 className="tc-section-title">Kategorik Özet Parametreleri</h3>
                        </div>
                        <div className="tc-params-list">
                            {params.map((p) => {
                                const IconComp = p.icon;
                                const isExpanded = expandedParam === p.key;
                                return (
                                    <div key={p.key} className={`tc-param-row-wrapper ${isExpanded ? 'active-row' : ''}`}>
                                        <div className="tc-param-clickable-row" onClick={() => setExpandedParam(isExpanded ? null : p.key)}>
                                            <div className="tc-param-left">
                                                <div className="tc-icon-frame">{IconComp && <IconComp size={14} />}</div>
                                                <span className="tc-param-label">{p.label}</span>
                                            </div>
                                            <div className="tc-param-right">
                                                <div className="tc-progress-bg">
                                                    <div className="tc-progress-fill" style={{ width: `${(p.score / 5) * 100}%` }}></div>
                                                </div>
                                                <span className="tc-param-score">{p.score}</span>
                                                {isExpanded ? <ChevronUp size={16} color={activeTheme.main} /> : <ChevronDown size={16} color="#64748b" />}
                                            </div>
                                        </div>
                                        {isExpanded && (
                                            <div className="tc-param-expanded-content">
                                                <p className="tc-expanded-text">{p.desc}</p>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* AI Sentez Özeti */}
                    <div className="tc-ai-summary-box">
                        <div className="tc-ai-summary-header">
                            <Sparkles size={16} color={activeTheme.main} />
                            <strong>{product.plat} Verisi Sentez Raporu</strong>
                        </div>
                        <p className="tc-interactive-text">
                            {renderInteractiveWords(summaryWords)}
                        </p>
                    </div>

                    {/* Yorumlar */}
                    <div className="tc-reviews-section">
                        <h3 className="tc-section-title">Duygu Yoğunluklu Değerlendirmeler ({filteredComments.length})</h3>
                        {selectedWord && (
                            <div className="tc-filter-alert">
                                <strong>"{selectedWord}"</strong> kelimesini içeren kaynak veri yorumları filtrelendi.
                            </div>
                        )}
                        <div className="tc-reviews-list">
                            {filteredComments.map(review => {
                                const commentWords = review.text.split(/\s+/);
                                return (
                                    <div key={review.id} className="tc-review-card">
                                        <div className="tc-review-header">
                                            <div className="tc-review-stars">
                                                <Star size={12} fill={review.sentiment === 'positive' ? '#10b981' : '#ef4444'} color={review.sentiment === 'positive' ? '#10b981' : '#ef4444'} />
                                                <span style={{ color: review.sentiment === 'positive' ? '#10b981' : '#ef4444', fontSize: '11px', fontWeight: 'bold', marginLeft: '4px', textTransform: 'uppercase' }}>
                                                    {review.sentiment === 'positive' ? 'Pozitif Duygu' : 'Negatif Duygu'}
                                                </span>
                                            </div>
                                            <span className="tc-review-user">{review.user} · {review.date}</span>
                                        </div>
                                        <p className="tc-interactive-text">
                                            {renderInteractiveWords(commentWords)}
                                        </p>
                                    </div>
                                )
                            })}
                        </div>
                    </div>

                </div>

                {/* 3. SAĞ: SATICI VE AKSİYONLAR */}
                <div className="tc-action-column">
                    <div className="tc-seller-box">
                        <div className="tc-seller-header">
                            <span className="tc-seller-name">{product.plat}</span>
                            <span className="tc-seller-badge"><CheckCircle size={12} /> Orijinal Kaynak</span>
                        </div>
                        <div className="tc-seller-info-row">
                            <Info size={14} color={activeTheme.main} />
                            <span>Bu analiz, {product.plat} üzerindeki açık veriler kullanılarak oluşturulmuştur.</span>
                        </div>
                    </div>

                    <a href={product.productUrl} target="_blank" rel="noreferrer" className="tc-btn-primary">
                        Mağazaya Git ve İncele
                    </a>

                    <button className={`tc-btn-secondary ${isFav ? 'fav-active' : ''}`} onClick={() => onFav(product)}>
                        <Heart size={16} fill={isFav ? activeTheme.main : 'none'} color={isFav ? activeTheme.main : '#475569'} />
                        {isFav ? 'Koleksiyona Eklendi' : 'Koleksiyona Ekle'}
                    </button>

                    {/* Değerlendirme Alanı */}
                    <div className="tc-rate-box">
                        <strong>Model Çıktısını Değerlendir</strong>
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
                                        onClick={() => onRate(product.id, s)}
                                        style={{ cursor: 'pointer', transition: 'transform 0.1s' }}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* 4. ALT KISIM: BENZER ÜRÜNLER */}
            <div className="tc-similar-section">
                <h2 className="tc-similar-title">Kategorideki Benzer Ürünler</h2>
                <div className="tc-similar-scroll-container">
                    {similarProducts.map(item => (
                        <div key={item.id} className="tc-similar-card-wrapper">
                            <ProductCard
                                item={item}
                                isFav={favorites.some((f) => f.id === item.id)}
                                onFav={onFav}
                                onClick={() => {
                                    window.scrollTo({ top: 0, behavior: 'smooth' });
                                    openProduct(item);
                                }}
                                userRating={ratings[item.id]}
                            />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default ProductPage;