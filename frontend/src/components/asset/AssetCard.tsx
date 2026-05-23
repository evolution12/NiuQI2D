import { ImagePreview } from '../common/ImagePreview';
import type { Asset } from '../../types';

interface AssetCardProps {
  asset: Asset;
  selected: boolean;
  onSelect: () => void;
  onDetail: () => void;
}

export function AssetCard({
  asset,
  selected,
  onSelect,
  onDetail,
}: AssetCardProps) {
  return (
    <div
      className="nq-card"
      onClick={onDetail}
      style={{
        border: selected
          ? '2px solid var(--accent)'
          : undefined,
        overflow: 'hidden',
        cursor: 'pointer',
        transition: 'border-color var(--t)',
      }}
    >
      <div
        style={{ position: 'relative' }}
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
      >
        <ImagePreview
          src={asset.thumbnail_path || asset.source_path}
          alt={asset.name}
          style={{ width: '100%', height: '120px' }}
        />
        {selected && (
          <div
            style={{
              position: 'absolute',
              top: 'var(--sp-1)',
              right: 'var(--sp-1)',
              width: '20px',
              height: '20px',
              borderRadius: '50%',
              backgroundColor: 'var(--accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: '12px',
            }}
          >
            &#10003;
          </div>
        )}
      </div>
      <div style={{ padding: 'var(--sp-2)' }}>
        <div className="truncate" style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-1)' }}>
          {asset.name}
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--sp-1)',
            marginTop: 'var(--sp-1)',
          }}
        >
          <span className={`nq-tag nq-tag--${asset.asset_type}`}>
            {asset.asset_type}
          </span>
          <span className={`nq-tag nq-tag--${asset.status}`}>
            {statusLabel(asset.status)}
          </span>
        </div>
      </div>
    </div>
  );
}

function statusLabel(status: string) {
  switch (status) {
    case 'draft': return '草稿';
    case 'selected': return '已选中';
    case 'exported': return '已导出';
    case 'discarded': return '已废弃';
    default: return status;
  }
}
