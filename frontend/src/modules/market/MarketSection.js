/**
 * MarketSection - Digital products marketplace component.
 * Displays available products (starting with Zoom accounts).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { apiClient } from '../../apiService';
import ZoomPurchaseModal from './ZoomPurchaseModal';
import './MarketSection.css';

// Zoom icon component (no emojis per project rules)
const ZoomIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M15 10l4.553-2.276A1 1 0 0 1 21 8.618v6.764a1 1 0 0 1-1.447.894L15 14v-4z" />
    <rect x="1" y="6" width="14" height="12" rx="2" ry="2" />
  </svg>
);

// Check icon
const CheckIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

// X icon
const XIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

// Shopping bag icon
const ShoppingBagIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
    <line x1="3" y1="6" x2="21" y2="6" />
    <path d="M16 10a4 4 0 0 1-8 0" />
  </svg>
);

const MarketSection = () => {
  const location = useLocation();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [showPurchaseModal, setShowPurchaseModal] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState(null); // 'success' | 'fail' | null

  // Check URL for payment status
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const status = params.get('status');
    if (status === 'success' || status === 'fail') {
      setPaymentStatus(status);
      // Clear status after 5 seconds
      setTimeout(() => setPaymentStatus(null), 5000);
    }
  }, [location.search]);

  const fetchProducts = useCallback(async () => {
    try {
      const response = await apiClient.get('/market/products/');
      setProducts(response.data || []);
    } catch (err) {
      console.error('Failed to fetch products:', err);
    }
  }, []);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await fetchProducts();
      setLoading(false);
    };
    loadData();
  }, [fetchProducts]);

  const handleBuyClick = (product) => {
    setSelectedProduct(product);
    setShowPurchaseModal(true);
  };

  const handleCloseModal = () => {
    setShowPurchaseModal(false);
    setSelectedProduct(null);
  };

  const handlePurchaseComplete = (paymentUrl) => {
    handleCloseModal();
    // Redirect to payment
    if (paymentUrl) {
      window.location.href = paymentUrl;
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('ru-RU').format(price);
  };

  if (loading) {
    return (
      <div className="market-section">
        <div className="market-loading">
          <div className="market-loading-spinner" />
          <span>Загрузка...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="market-section">
      {/* Payment Status Banner */}
      {paymentStatus && (
        <div className={`payment-status-banner ${paymentStatus}`}>
          {paymentStatus === 'success' ? (
            <>
              <CheckIcon />
              <span>Оплата прошла успешно! Мы свяжемся с вами в ближайшее время.</span>
            </>
          ) : (
            <>
              <XIcon />
              <span>Оплата не прошла. Попробуйте снова или свяжитесь с поддержкой.</span>
            </>
          )}
        </div>
      )}

      <div className="market-header">
        <h2>Маркет</h2>
        <p>Цифровые услуги для вашего обучения</p>
      </div>

      {/* Custom Services Banner */}
      <div className="market-custom-banner">
        <div className="custom-banner-row">
          <div className="custom-banner-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M2 12h20" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
          </div>
          <div className="custom-banner-content">
            <span className="custom-banner-title">Нужен другой сервис?</span>
            <span className="custom-banner-text">
              Поможем оплатить любую зарубежную подписку: ChatGPT, Midjourney, Notion, Figma и другие. Цены ниже рынка.
            </span>
          </div>
        </div>
        <a 
          href="https://t.me/help_lectio_space_bot" 
          target="_blank" 
          rel="noopener noreferrer"
          className="custom-banner-button"
        >
          Написать в поддержку
        </a>
      </div>

      {/* Products Grid */}
      {products.length > 0 ? (
        <div className="market-products">
          {products.map((product) => (
            <div
              key={product.id}
              className="market-product-card"
              onClick={() => handleBuyClick(product)}
            >
              <div className="product-icon">
                {product.product_type === 'zoom' ? <ZoomIcon /> : <ShoppingBagIcon />}
              </div>
              <h3 className="product-title">{product.title}</h3>
              <p className="product-description">{product.description}</p>
              <div className="product-price">
                <span>
                  <span className="price-value">{formatPrice(product.price)}</span>
                  <span className="price-period"> ₽/мес</span>
                </span>
                <button
                  className="product-buy-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleBuyClick(product);
                  }}
                >
                  Купить
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="market-empty">
          <ShoppingBagIcon className="market-empty-icon" />
          <p>Товары скоро появятся</p>
        </div>
      )}

      {/* Purchase Modal */}
      {showPurchaseModal && selectedProduct && (
        <ZoomPurchaseModal
          product={selectedProduct}
          onClose={handleCloseModal}
          onComplete={handlePurchaseComplete}
        />
      )}
    </div>
  );
};

export default MarketSection;
