import React from 'react';
import { Heart, Star } from 'lucide-react';
import './ProductCard.css';

// ── PLATFORM GERÇEK MARKA RENK ALGORTİMASI ──
export const getPlatformColor = (platName) => {
    if (!platName) return '#8b5cf6'; // Default VividAI Moru
    const str = platName.toLowerCase().replace(/\s+/g, '');

    // Gerçek Marka Renk Kodları (Brand Colors)
    if (str.includes('trendyolgo')) return '#0cc167'; // Trendyol Turuncusu
    if (str.includes('trendyol')) return '#F27A1A';   // Trendyol Turuncusu
    if (str.includes('yemeksepeti')) return '#EA004B';// Yemeksepeti Pembesi
    if (str.includes('google')) return '#4285F4';    // Google Yeşili
    if (str.includes('airbnb')) return '#FF5A5F';     // Airbnb Rausch (Kırmızı/Mercan)
    if (str.includes('hepsiburada')) return '#FF6000';// Hepsiburada Orijinal Turuncu
    if (str.includes('steam')) return '#2A475E';      // Steam Laciverti
    if (str.includes('etstur')) return '#009FDF';     // Etstur Orijinal Turkuaz
    if (str.includes('çiçeksepeti') || str.includes('ciceksepeti')) return '#028139'; // Çiçeksepeti Koyu Yeşili

    return '#8b5cf6';
};

function ProductCard({ item, isFav, onFav, onClick, userRating }) {
    const platColor = getPlatformColor(item.plat);

    return (
        <div className="p-card" onClick={onClick}>
            <button
                className={`p-fav-btn ${isFav ? 'active' : ''}`}
                onClick={(e) => {
                    e.stopPropagation();
                    onFav(item);
                }}
                style={{
                    ...(isFav ? { borderColor: platColor, background: `${platColor}15` } : {})
                }}
            >
                <Heart
                    size={16}
                    fill={isFav ? platColor : 'none'}
                    color={isFav ? platColor : '#94a3b8'}
                />
            </button>

            <div className="p-img-wrap">
                <img
                    src={item.img}
                    alt={item.name}
                    className="p-img"
                    onError={(e) => {
                        e.target.src = 'https://via.placeholder.com/200x200/111027/8b5cf6?text=Görsel+Yok';
                    }}
                />
            </div>

            <div className="p-body">
                <div className="p-plat" style={{ color: platColor }}>{item.plat}</div>
                <h4 className="p-name" title={item.name}>{item.name}</h4>

                <div className="p-footer">
                    {/* Kategori için dinamik renkli şık badge */}
                    <span
                        className="p-cat"
                        style={{ backgroundColor: `${platColor}15`, color: platColor, border: `1px solid ${platColor}30` }}
                    >
                        {item.category}
                    </span>

                    <span className="p-score">
                        <Star size={13} fill="#fbbf24" color="#fbbf24" />
                        <span className="p-score-val">{userRating || item.avgScore}</span>
                    </span>
                </div>
            </div>
        </div>
    );
}

export default ProductCard;