import React from 'react';

export type ImageWithFallbackProps = {
  src: string;
  alt: string;
  className?: string;
  onErrorSrc?: string;
};

// Vector-first image component. Falls back to provided onErrorSrc if load fails.
// Note: Prefer SVG/WebP assets per policy.
const ImageWithFallback: React.FC<ImageWithFallbackProps> = ({ src, alt, className, onErrorSrc }) => {
  const [currentSrc, setCurrentSrc] = React.useState(src);
  const handleError = () => {
    if (onErrorSrc && onErrorSrc !== currentSrc) {
      setCurrentSrc(onErrorSrc);
    }
  };
  return <img src={currentSrc} alt={alt} className={className} onError={handleError} role="img" aria-label={alt} />;
};

export default ImageWithFallback;
