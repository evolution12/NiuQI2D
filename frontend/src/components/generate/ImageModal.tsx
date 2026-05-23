import { backendUrl } from '../../services/api';

export function ImageModal({ src, onClose }: { src: string; alt?: string; onClose: () => void }) {
  return (
    <div style={{ position: 'fixed', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.8)', zIndex: 9000, cursor: 'pointer' }} onClick={onClose}>
      <div className="checkerboard" style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: 'var(--r-lg)', overflow: 'hidden' }}>
        <img src={backendUrl(src)} alt="" style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain' }} />
      </div>
    </div>
  );
}
