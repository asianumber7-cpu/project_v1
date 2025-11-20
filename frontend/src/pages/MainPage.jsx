// frontend/src/pages/MainPage.jsx

import React, { useState, useEffect } from 'react';
import api from '../api';
import ProductCard from '../components/ProductCard';

function MainPage() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // (★) AI 검색을 위한 State
  const [query, setQuery] = useState(""); // 텍스트 검색어
  const [size, setSize] = useState(""); // 사이즈 필터
  const [selectedFile, setSelectedFile] = useState(null); // 업로드할 이미지 파일
  const [searchLoading, setSearchLoading] = useState(false); // 검색 로딩

  // 1. 처음 로드될 때 전체 상품 목록을 가져옴
  async function fetchAllProducts() {
    try {
      setLoading(true);
      const response = await api.get('/products/');
      setProducts(response.data);
    } catch (error) {
      console.error("상품 목록 조회 실패:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAllProducts();
  }, []);

  // 2. (★) AI 텍스트 검색 핸들러 (아이디어 2+3)
  const handleTextSearch = async () => {
    if (!query) {
      console.warn("검색어를 입력하세요.");
      return;
    }
    try {
      setSearchLoading(true);
      
      // [변경] GET -> POST (우리가 만든 새 API는 POST 방식입니다)
      // [변경] 주소: /recommend/by-text -> /products/search
      const response = await api.post('/products/search', {
        query: query, // 검색어
        // size는 나중에 필터링 로직 추가되면 사용 (지금은 일단 보냄)
        size: size || undefined 
      });
      
      setProducts(response.data);
    } catch (error) {
      console.error("AI 텍스트 검색 실패:", error);
      alert("검색 중 오류가 발생했습니다.");
    } finally {
      setSearchLoading(false);
    }
  };

  // 3. (★) AI 이미지 검색 핸들러 (아이디어 4)
  const handleImageSearch = async () => {
    if (!selectedFile) {
      console.warn("이미지를 선택하세요.");
      return;
    }
    
    const formData = new FormData();
    formData.append("file", selectedFile); 

    try {
      setSearchLoading(true);
      const response = await api.post('/recommend/by-image-upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setProducts(response.data);
    } catch (error) {
      console.error("AI 이미지 검색 실패:", error);
    } finally {
      setSearchLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="header-container">
        <h1>AI 쇼핑몰</h1>
        <button onClick={fetchAllProducts} className="reset-button">
          전체 상품 보기
        </button>
      </div>

      {/* (★) AI 검색 컨트롤 패널 */}
      <div className="search-container">
        {/* 1. 텍스트 검색 (아이디어 2+3) */}
        <div className="search-box text-search">
          <h4>AI 텍스트로 검색</h4>
          <input
            type="text"
            className="search-bar"
            placeholder="예: 빨간색 바지"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <input
            type="text"
            className="size-filter"
            placeholder="사이즈 (예: M)"
            value={size}
            onChange={(e) => setSize(e.target.value)}
          />
          <button onClick={handleTextSearch} disabled={searchLoading}>
            {searchLoading ? '검색 중...' : '텍스트 검색'}
          </button>
        </div>

        {/* 2. 이미지 검색 (아이디어 4) */}
        <div className="search-box image-search">
          <h4>AI 이미지로 검색</h4>
          <input
            type="file"
            className="file-input"
            accept="image/*"
            onChange={(e) => setSelectedFile(e.target.files[0])}
          />
          <button onClick={handleImageSearch} disabled={!selectedFile || searchLoading}>
            {searchLoading ? '검색 중...' : '이미지 검색'}
          </button>
        </div>
      </div>

      {/* 상품 목록 */}
      <h2>{searchLoading ? "AI 추천 상품 검색 중..." : "상품 목록"}</h2>
      {loading ? (
        <div className="loading">로딩 중...</div>
      ) : (
        <div className="product-grid">
          {products.length > 0 ? (
            products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))
          ) : (
            <p>표시할 상품이 없습니다.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default MainPage;