// frontend/src/App.jsx
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import MainPage from './pages/MainPage.jsx';
import ProductDetailPage from './pages/ProductDetailPage.jsx';
import ScrollToTop from './components/ScrollToTop.jsx';

function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/product/:productId" element={<ProductDetailPage />} />
      </Routes>
    </>
  );
}
export default App;