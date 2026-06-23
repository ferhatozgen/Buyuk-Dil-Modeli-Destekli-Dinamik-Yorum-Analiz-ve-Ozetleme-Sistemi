import axios from 'axios';

// http://localhost:5009
//https://bubbly-enthusiasm-production-7c3a.up.railway.app
const api = axios.create({
    baseURL: 'https://bubbly-enthusiasm-production-7c3a.up.railway.app/api',
    headers: {
        'Content-Type': 'application/json'
    }
});

//Yapay Zeka (FastAPI) Chatbot Bağlantı Fonksiyonu direkt pcye istek atacak şekilde
export const sendChatMessageToVividBot = async (productId, userMessage) => {
    try {
        const response = await axios.post('http://localhost:8000/api/v1/chat', {
            productId: productId,
            user_message: userMessage
        }, {
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        // FastAPI'den dönen başarı durumunu kontrol ediyoruz
        if (response.data.status === "success") {
            return response.data.response; //botun cevabı
        }
        return "Üzgünüm, şu an yanıt üretemiyorum.";

    } catch (error) {
        console.error("Chatbot API Bağlantı Hatası:", error);
        return "Bağlantı hatası oluştu. FastAPI sunucusunun açık olduğundan emin olun.";
    }
};

export default api;
