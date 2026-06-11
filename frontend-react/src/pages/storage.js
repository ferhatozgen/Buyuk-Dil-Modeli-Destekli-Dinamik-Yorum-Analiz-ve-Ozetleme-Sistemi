export const STORAGE_KEYS = {
    ratings: 'vividai:ratings',
    favorites: 'vividai:favorites',
    history: 'vividai:history',
    searches: 'vividai:searches',
};

// ── GERÇEK TARAYICI LOCALSTORAGE ENTEGRASYONU ──
export function dbGet(key) {
    try {
        const val = localStorage.getItem(key);
        if (val === null || val === undefined) return null;
        return JSON.parse(val);
    } catch (error) {
        console.error("Storage verisi okunurken hata oluştu:", error);
        return null;
    }
}

export function dbSet(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
        console.error("Storage verisi yazılırken hata oluştu:", error);
    }
}