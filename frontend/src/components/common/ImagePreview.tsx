import type { CSSProperties } from 'react';
import { backendUrl } from '../../services/api';

export function ImagePreview({ src, alt = '', size, className, style }: { src: string; alt?: string; size?: number | string; className?: string; style?: CSSProperties }) {
  return (
    <div className={`checkerboard ${className ?? ''}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: size ?? '100%', height: size ?? '100%', borderRadius: 'var(--r-md)', overflow: 'hidden', ...style }}>
      <img src={backendUrl(src)} alt={alt} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
    </div>
  );
}
