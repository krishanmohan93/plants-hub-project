import React, { useEffect, useRef, useState } from 'react';

// Props: src, alt, onClose, initialRect (optional for improved animation)
export default function ZoomImageModal({ src, alt = '', onClose }) {
  const overlayRef = useRef(null);
  const imgRef = useRef(null);
  const [visible, setVisible] = useState(false);

  // Transform state
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const lastTouchDistance = useRef(null);
  const isDragging = useRef(false);
  const lastPointer = useRef({ x: 0, y: 0 });

  useEffect(() => {
    // show with fade/scale animation
    requestAnimationFrame(() => setVisible(true));
    // prevent background scroll
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  useEffect(() => {
    // Reset transforms when image changes
    setScale(1);
    setTranslate({ x: 0, y: 0 });
  }, [src]);

  function handleClose() {
    setVisible(false);
    // wait for animation to finish
    setTimeout(() => onClose && onClose(), 220);
  }

  // Wheel zoom (desktop)
  function onWheel(e) {
    e.preventDefault();
    const delta = -e.deltaY;
    const zoomFactor = delta > 0 ? 1.08 : 0.92;
    const rect = imgRef.current.getBoundingClientRect();
    const offsetX = e.clientX - rect.left - rect.width / 2;
    const offsetY = e.clientY - rect.top - rect.height / 2;

    setScale(prev => {
      const next = Math.min(Math.max(prev * zoomFactor, 1), 5);
      // adjust translate so zoom focuses on cursor
      const ratio = next / prev;
      setTranslate(t => ({ x: t.x - offsetX * (ratio - 1), y: t.y - offsetY * (ratio - 1) }));
      return next;
    });
  }

  // Pointer / mouse drag
  function onPointerDown(e) {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    isDragging.current = true;
    lastPointer.current = { x: e.clientX, y: e.clientY };
    e.target.setPointerCapture && e.target.setPointerCapture(e.pointerId);
  }

  function onPointerMove(e) {
    if (!isDragging.current) return;
    const dx = e.clientX - lastPointer.current.x;
    const dy = e.clientY - lastPointer.current.y;
    lastPointer.current = { x: e.clientX, y: e.clientY };
    setTranslate(t => ({ x: t.x + dx, y: t.y + dy }));
  }

  function onPointerUp(e) {
    isDragging.current = false;
    e.target.releasePointerCapture && e.target.releasePointerCapture(e.pointerId);
    maybeResetPosition();
  }

  // Touch pinch
  function getTouchDistance(touches) {
    const [a, b] = touches;
    const dx = a.clientX - b.clientX;
    const dy = a.clientY - b.clientY;
    return Math.hypot(dx, dy);
  }

  function onTouchStart(e) {
    if (e.touches.length === 2) {
      lastTouchDistance.current = getTouchDistance(e.touches);
    } else if (e.touches.length === 1) {
      isDragging.current = true;
      lastPointer.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
  }

  function onTouchMove(e) {
    if (e.touches.length === 2) {
      const d = getTouchDistance(e.touches);
      const prev = lastTouchDistance.current || d;
      const ratio = d / prev;
      lastTouchDistance.current = d;
      setScale(s => Math.min(Math.max(s * ratio, 1), 5));
    } else if (e.touches.length === 1 && isDragging.current) {
      const t0 = e.touches[0];
      const dx = t0.clientX - lastPointer.current.x;
      const dy = t0.clientY - lastPointer.current.y;
      lastPointer.current = { x: t0.clientX, y: t0.clientY };
      setTranslate(t => ({ x: t.x + dx, y: t.y + dy }));
    }
  }

  function onTouchEnd(e) {
    if (e.touches.length < 2) lastTouchDistance.current = null;
    isDragging.current = false;
    maybeResetPosition();
  }

  // Keep image inside bounds when not zoomed out too far
  function maybeResetPosition() {
    // If scale is 1, reset translate
    if (scale <= 1.001) {
      setTranslate({ x: 0, y: 0 });
      setScale(1);
    } else {
      // Optionally clamp translate so edges don't create white space
      // This is a relaxed clamp; exact pixel-perfect clamping would require image natural size
    }
  }

  const transformStyle = {
    transform: `translate3d(${translate.x}px, ${translate.y}px, 0) scale(${scale})`,
    transition: isDragging.current ? 'none' : 'transform 0.12s ease-out',
    touchAction: 'none',
    cursor: scale > 1 ? 'grab' : 'auto',
    maxWidth: '100%',
    maxHeight: '100%'
  };

  return (
    <div
      ref={overlayRef}
      className={`zoom-modal__overlay ${visible ? 'zoom-modal__overlay--visible' : ''}`}
      onMouseDown={e => { if (e.target === overlayRef.current) handleClose(); }}
    >
      <div className={`zoom-modal__close`} onClick={handleClose} aria-label="Close">×</div>
      <div className="zoom-modal__center">
        <img
          ref={imgRef}
          src={src}
          alt={alt}
          className="zoom-modal__img"
          style={transformStyle}
          onWheel={onWheel}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
          draggable={false}
        />
      </div>
    </div>
  );
}
