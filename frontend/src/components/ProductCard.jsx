// frontend/src/components/ProductCard.jsx
import React, { useState } from 'react'; // (★) useState 임포트
import { Link } from 'react-router-dom'; // (★) 클릭 이동을 위한 Link 임포트

// MainPage.jsx에서 product 객체를 props로 받습니다.
function ProductCard({ product }) {
  
  // (★) [버그 수정 1] product가 undefined나 null인 경우 렌더링하지 않음
  // (이것이 "Cannot read properties of undefined (reading 'id')" 오류를 해결합니다.)
  if (!product) {
    return null; 
  }

  // (★) [버그 수정 2] 이미지 로드 실패 시 state로 관리
  // (DOM을 직접 조작하면 React 렌더링 오류가 발생할 수 있습니다.)
  const [imageError, setImageError] = useState(false);
  
  // (★) 카드를 Link로 감싸서, 클릭 시 상세 페이지로 이동시킵니다.
  return (
    <Link to={`/product/${product.id}`} className="product-card-link">
      <div className="product-card">

        {/* (★) [수정] 이미지 로드 실패 시 대체 UI를 보여줌 */}
        {imageError ? (
          <div className="image-error">
            이미지 로드 실패
          </div>
        ) : (
          <img 
            src={product.image_url} 
            alt={product.name} 
            className="product-image"
            // (★) [수정] DOM 직접 조작 대신 state를 변경
            onError={() => { 
              setImageError(true);
            }}
          />
        )}
        
        <div className="product-info">
          <h3>{product.name}</h3>
          <p>{product.description}</p>
        </div>
      </div>
    </Link>
  );
}

export default ProductCard;