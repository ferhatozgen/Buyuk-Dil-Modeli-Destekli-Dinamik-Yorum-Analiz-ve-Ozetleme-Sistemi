import axios from 'axios';

const api = axios.create({
    baseURL: 'https://bubbly-enthusiasm-production-7c3a.up.railway.app/',
    headers: {
        'Content-Type': 'application/json'
    }
});

export default api;
