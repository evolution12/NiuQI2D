import type { Asset } from '../../types';
import { ImagePreview } from '../common/ImagePreview';

interface AssetSelectorProps {
  assets: Asset[];
  onRemove: (id: string) => void;
}

export function AssetSelector({ assets, onRemove }: AssetSelectorProps) {
  if (assets.length === 0) {
    return (
      <div
        style={{
          padding: 'var(--sp-8)',
          textAlign: 'center',
          color: 'var(--text-3)',
          fontSize: '13px',
        }}
      >
        未选择资产。从资产库页面选择资产后跳转至此。
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        gap: 'var(--sp-2)',
        flexWrap: 'wrap',
      }}
    >
      {assets.map((asset) => (
        <div
          key={asset.id}
          style={{
            width: '80px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 'var(--sp-1)',
          }}
        >
          <ImagePreview
            src={asset.thumbnail_path || asset.source_path}
            alt={asset.name}
            size={64}
          />
          <div
            className="truncate"
            style={{ fontSize: '11px', color: 'var(--text-2)', width: '100%', textAlign: 'center' }}
          >
            {asset.name}
          </div>
          <button
            className="nq-btn nq-btn--sm nq-btn--danger"
            style={{ padding: '1px 6px', fontSize: '10px' }}
            onClick={() => onRemove(asset.id)}
          >
            移除
          </button>
        </div>
      ))}
    </div>
  );
}
