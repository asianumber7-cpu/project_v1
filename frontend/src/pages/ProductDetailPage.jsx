// frontend/src/pages/ProductDetailPage.jsx (★ UI 대폭 개선 ★)

import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api.js';
import ProductCard from '../components/ProductCard.jsx';

function ProductDetailPage() {
  const { productId } = useParams();
  const [product, setProduct] = useState(null);
  const [recommended, setRecommended] = useState([]);
  const [colorVariants, setColorVariants] = useState([]);
  const [priceRange, setPriceRange] = useState([]);
  const [coordination, setCoordination] = useState([]);
  const [activeTab, setActiveTab] = useState('similar');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setRecommended([]);

        // 1. 현재 상품 정보
        const productRes = await api.get(`/products/${productId}`);
        setProduct(productRes.data);

        // 2. AI 추천 (유사 상품)
        // (이 부분은 기존 API 유지. 나중에 벡터 검색으로 고도화 가능)
        try {
            const recommendRes = await api.get(`/recommend/by-product/${productId}`);
            setRecommended(recommendRes.data);
        } catch (e) {
            console.log("추천 상품 없음");
        }

        // 3. ★ [수정] 다른 색상 (주소 변경!) ★
        // 옛날 주소: /recommend/by-color/...
        // 새 주소:   /products/.../colors
        try {
          const colorRes = await api.get(`/products/${productId}/colors`);
          setColorVariants(colorRes.data);
        } catch (e) {
          console.log("색상별 추천 없음");
        }

        // 4. 가격대별 추천 (기존 유지)
        try {
          const priceRes = await api.get(`/recommend/by-price-range/${productId}?price_diff=30000`);
          setPriceRange(priceRes.data);
        } catch (e) {
          console.log("가격대별 추천 없음");
        }

        // 5. 코디 추천 (기존 유지)
        try {
          const coordRes = await api.get(`/recommend/coordination/${productId}`);
          setCoordination(coordRes.data);
        } catch (e) {
          console.log("코디 추천 없음");
        }

      } catch (error) {
        console.error("데이터 조회 실패:", error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [productId]);

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>상품 정보를 불러오는 중...</p>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="error-container">
        <h2>😔 상품을 찾을 수 없습니다</h2>
        <Link to="/" className="btn-primary">홈으로 돌아가기</Link>
      </div>
    );
  }

  return (
    <div className="product-detail-page">
      <div className="container">
        {/* 뒤로가기 버튼 */}
        <Link to="/" className="back-button">
          ← 뒤로가기
        </Link>

        {/* 상품 상세 섹션 */}
        <div className="product-detail-wrapper">
          {/* 왼쪽: 이미지 */}
          <div className="product-image-section">
            <img 
              src={product.image_url} 
              alt={product.name} 
              className="product-main-image"
            />
          </div>

          {/* 오른쪽: 상품 정보 */}
          <div className="product-info-section">
            <h1 className="product-title">{product.name}</h1>
            
            {product.price && (
              <div className="product-price">
                {product.price.toLocaleString()}원
              </div>
            )}

            <div className="product-meta">
              {product.color && (
                <div className="meta-item">
                  <span className="meta-label">색상</span>
                  <span className="meta-value">{product.color}</span>
                </div>
              )}
              {product.category && (
                <div className="meta-item">
                  <span className="meta-label">카테고리</span>
                  <span className="meta-value">{product.category}</span>
                </div>
              )}
              {product.season && (
                <div className="meta-item">
                  <span className="meta-label">시즌</span>
                  <span className="meta-value">{product.season}</span>
                </div>
              )}
            </div>

            <div className="product-description">
              <h3>상품 설명</h3>
              <p>{product.description}</p>
            </div>

            <div className="product-size">
              <h3>사이즈</h3>
              <div className="size-options">
                {Object.keys(product.size_info || {}).map(size => (
                  <span key={size} className="size-badge">{size}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 추천 탭 섹션 */}
        <div className="recommendation-wrapper">
          <h2 className="section-title">추천 상품</h2>
          
          {/* 탭 버튼 */}
          <div className="tabs">
            <button 
              className={`detail-tab ${activeTab === 'similar' ? 'active' : ''}`}
              onClick={() => setActiveTab('similar')}
            >
              <span className="tab-icon">🎯</span>
              <span className="tab-text">AI 추천</span>
              <span className="tab-count">({recommended.length})</span>
            </button>
            
            {colorVariants.length > 0 && (
              <button 
                className={`detail-tab ${activeTab === 'color' ? 'active' : ''}`}
                onClick={() => setActiveTab('color')}
              >
                <span className="tab-icon">🎨</span>
                <span className="tab-text">다른 색상</span>
                <span className="tab-count">({colorVariants.length})</span>
              </button>
            )}
            
            {priceRange.length > 0 && (
              <button 
                className={`detail-tab ${activeTab === 'price' ? 'active' : ''}`}
                onClick={() => setActiveTab('price')}
              >
                <span className="tab-icon">💰</span>
                <span className="tab-text">비슷한 가격</span>
                <span className="tab-count">({priceRange.length})</span>
              </button>
            )}
            
            {coordination.length > 0 && (
              <button 
                className={`detail-tab ${activeTab === 'coordination' ? 'active' : ''}`}
                onClick={() => setActiveTab('coordination')}
              >
                <span className="tab-icon">👔</span>
                <span className="tab-text">코디 추천</span>
                <span className="tab-count">({coordination.length})</span>
              </button>
            )}
          </div>

          {/* 탭 콘텐츠 */}
          <div className="tab-content">
            {activeTab === 'similar' && (
              <div className="product-grid">
                {recommended.length > 0 ? (
                  recommended.map((item) => (
                    <ProductCard key={item.id} product={item} />
                  ))
                ) : (
                  <p className="empty-message">추천 상품이 없습니다.</p>
                )}
              </div>
            )}

            {activeTab === 'color' && (
              <div className="product-grid">
                {colorVariants.map((item) => (
                  <ProductCard key={item.id} product={item} />
                ))}
              </div>
            )}

            {activeTab === 'price' && (
              <div className="product-grid">
                {priceRange.map((item) => (
                  <ProductCard key={item.id} product={item} />
                ))}
              </div>
            )}

            {activeTab === 'coordination' && (
              <div className="product-grid">
                {coordination.map((item) => (
                  <ProductCard key={item.id} product={item} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProductDetailPage;