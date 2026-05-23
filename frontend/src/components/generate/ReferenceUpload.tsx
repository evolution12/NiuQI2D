import { useState, useRef } from 'react';
import { uploadApi } from '../../services/api';
import { toast } from '../common/Toast';

export function ReferenceUpload({ onUploadComplete, onRemove, previewUrl, disabled }: { onUploadComplete: (path: string) => void; onRemove: () => void; previewUrl: string | null; disabled?: boolean }) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file.type.startsWith('image/')) { toast.error('Image files only'); return; }
    if (file.size > 10 * 1024 * 1024) { toast.error('Max 10 MB'); return; }
    setUploading(true);
    try {
      const r = await uploadApi.upload(file, 'reference');
      onUploadComplete(r.path); toast.success('Uploaded');
    } catch (e: any) { toast.error('Upload failed: ' + (e.message ?? 'unknown')); }
    finally { setUploading(false); }
  };

  return (
    <div>
      <div className="form-label" style={{ marginBottom: 'var(--sp-1)' }}>Reference image (optional)</div>
      {previewUrl ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
          <div className="checkerboard" style={{ width: 48, height: 48, borderRadius: 'var(--r-md)', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <img src={previewUrl} alt="ref" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
          </div>
          <button className="nq-btn nq-btn--sm nq-btn--danger" onClick={onRemove} disabled={disabled}>Remove</button>
        </div>
      ) : (
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); }}
          style={{ border: `1px dashed ${dragOver ? 'var(--accent)' : 'var(--border-1)'}`, borderRadius: 'var(--r-md)', padding: 'var(--sp-4)', textAlign: 'center', cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.4 : 1, transition: 'border-color var(--t)' }}>
          <div style={{ font: '400 11px var(--font)', color: 'var(--text-3)' }}>{uploading ? 'Uploading...' : 'Drop or click to upload'}</div>
        </div>
      )}
      <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }} style={{ display: 'none' }} />
    </div>
  );
}
