// frontend/src/api.js
import axios from 'axios';

// Axios 인스턴스 생성
const api = axios.create({
  // (중요!) 백엔드 API의 기본 주소
  baseURL: 'http://localhost:8000/api/v1',
});

export default api;