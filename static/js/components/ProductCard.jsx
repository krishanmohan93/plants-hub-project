import React, { useState } from 'react';
import ZoomImageModal from './ZoomImageModal';

export default function ProductCard({ product }) {
  const [zoomSrc, setZoomSrc] = useState(null);

  function openZoom() {
    // prefer full-resolution image if available
    const src = product.fullImage || product.image;
    setZoomSrc(src);
  }

  function closeZoom() {
    setZoomSrc(null);
  }

  return (
    <div className="product-card">
      <div className="product-card__img-wrap" onClick={openZoom} role="button" tabIndex={0}>
        <img src={product.image} alt={product.name} className="product-card__img" />
      </div>
      <div className="product-card__meta">
        <h3>{product.name}</h3>
      </div>

      {zoomSrc && (
        <ZoomImageModal src={zoomSrc} alt={product.name} onClose={closeZoom} />
      )}
    </div>
  );
}
