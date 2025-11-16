// frontend/src/api.js

import axios from 'axios';

const api = axios.create({
  // ★ 개발 환경: localhost:8000
  // ★ 프로덕션: Nginx 프록시를 통해 /api로 접근
  baseURL: import.meta.env.PROD 
    ? '/api/v1'  // 프로덕션: Nginx 프록시 사용
    : 'http://localhost:8000/api/v1',  // 개발: 직접 연결
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;