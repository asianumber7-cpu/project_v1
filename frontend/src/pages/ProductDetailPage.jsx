// frontend/src/pages/ProductDetailPage.jsx
import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom'; // (★) URL의 ID를 가져오기 위한 useParams
import api from '../api.js';
import ProductCard from '../components/ProductCard.jsx'; // 재사용

function ProductDetailPage() {
  const { productId } = useParams(); // URL에서 상품 ID (예: "1")를 가져옴
  const [product, setProduct] = useState(null);
  const [recommended, setRecommended] = useState([]); // (★) AI 추천 상품 목록
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // productId가 바뀔 때마다 데이터를 새로고침
    async function fetchData() {
      try {
        setLoading(true);
        setRecommended([]); // 추천 목록 초기화

        // 1. (API 호출 1) 상품 상세 정보 가져오기
        const productRes = await api.get(`/products/${productId}`);
        setProduct(productRes.data);

        // 2. (API 호출 2 - ★AI 기능★) 유사 상품 추천 목록 가져오기
        const recommendRes = await api.get(`/recommend/by-product/${productId}`);
        setRecommended(recommendRes.data);

      } catch (error) {
        console.error("데이터 조회 실패:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [productId]); // (★) productId가 바뀔 때마다 useEffect 실행

  if (loading) {
    return <div className="loading">상품 정보 로딩 중...</div>;
  }

  if (!product) {
    return <div>상품을 찾을 수 없습니다.</div>;
  }

  return (
    <div className="container detail-page-container">
      {/* 1. 메인 상품 상세 정보 */}
      <div className="main-product-details">
        <Link to="/" className="back-link">← 뒤로가기</Link>
        <img src={product.image_url} alt={product.name} className="detail-product-image" />
        <h2>{product.name}</h2>
        <p>{product.description}</p>
        <p>사이즈: {Object.keys(product.size_info || {}).join(', ')}</p>
      </div>

      {/* 2. AI 추천 상품 목록 */}
      <div className="recommendation-section">
        <h3>✨ AI 추천 유사 상품 ✨</h3>
        <div className="product-grid">
          {recommended.length > 0 ? (
            recommended.map((item) => (
              <ProductCard key={item.id} product={item} />
            ))
          ) : (
            <p>유사한 상품을 찾을 수 없습니다.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default ProductDetailPage;