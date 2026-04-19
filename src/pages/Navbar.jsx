import React from 'react';
import { Link } from 'react-router-dom';

function Navbar() {
    return (
        <header className="navbar">
            {/* Logoya tıklandığında ana sayfaya döner */}
            <Link to="/" className="logo-wrap" style={{ textDecoration: 'none', color: 'inherit' }}>
                <div className="logo-icon">AI</div>
                <div className="logo-text">
                    <span className="logo-title">AI Review</span>
                    <span className="logo-subtitle">Smart Comment Intelligence</span>
                </div>
            </Link>

            <nav className="menu">
                {/* Sayfa içi kaydırmalar için normal <a>, sayfalar arası için <Link> */}
                <a href="#features">Özellikler</a>
                <a href="#demo">Demo</a>
                <Link to="/login" style={{ color: 'white' }}>Giriş</Link>
            </nav>

            {/* Eğer sağ tarafta ekstra bir buton istersen */}
            <div className="nav-actions">
                <Link to="/login" className="nav-button" style={{ display: 'inline-flex', alignItems: 'center', textDecoration: 'none' }}>
                    Başla
                </Link>
            </div>
        </header>
    );
}

export default Navbar;