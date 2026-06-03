import React from 'react';
import { Heart, Star } from 'lucide-react';
import './ProductCard.css';

// ── PLATFORM RENK ALGORTİMASI ──
export const getPlatformColor = (platName) => {
    if (!platName) return '#8b5cf6'; // Default VividAI Moru
    const str = platName.toLowerCase().replace(/\s+/g, '');
    if (str.includes('trendyolgo')) return '#f27a1a';
    if (str.includes('trendyol')) return '#f27a1a';
    if (str.includes('yemeksepeti')) return '#ea004b';
    if (str.includes('google')) return '#34a853';
    if (str.includes('airbnb')) return '#ff5a5f';
    if (str.includes('hepsiburada')) return '#ff6000';
    if (str.includes('steam')) return '#66c0f4';
    if (str.includes('etstur')) return '#0ea5e9';
    if (str.includes('çiçeksepeti') || str.includes('ciceksepeti')) return '#16a34a';
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
                // Favori seçiliyken arkaplanı ve çerçeveyi platform rengine boyar
                style={{
                    ...(isFav ? { borderColor: platColor, background: `${platColor}20` } : {})
                }}
            >
                <Heart
                    size={14}
                    fill={isFav ? platColor : 'none'}
                    color={isFav ? platColor : 'var(--card-subtext, #94a3b8)'}
                />
            </button>

            <div className="p-img-wrap">
                <img
                    src={item.img}
                    alt={item.name}
                    className="p-img"
                    onError={(e) => {
                        e.target.src = 'https://via.placeholder.com/180x180/111027/8b5cf6?text=N/A';
                    }}
                />
            </div>

            <div className="p-body">
                {/* Platform Adı Dinamik Renk */}
                <div className="p-plat" style={{ color: platColor }}>{item.plat}</div>
                <h4 className="p-name">{item.name}</h4>
                <div className="p-footer">
                    <span className="p-cat">{item.category}</span>
                    {/* Yıldız ve Puan Dinamik Renk */}
                    <span className="p-score" style={{ color: platColor }}>
                        <Star size={11} fill={platColor} color={platColor} />
                        {' '}{userRating || item.avgScore}
                    </span>
                </div>
            </div>
        </div>
    );
}

export default ProductCard;