import type { Asset } from '../../types';
import { AssetCard } from './AssetCard';
import { EmptyState } from '../common/EmptyState';

interface AssetGridProps {
  assets: Asset[];
  selectedIds: Set<string>;
  onToggleSelect: (id: string) => void;
  onDetail: (id: string) => void;
}

export function AssetGrid({
  assets,
  selectedIds,
  onToggleSelect,
  onDetail,
}: AssetGridProps) {
  if (assets.length === 0) {
    return (
      <EmptyState
        title="暂无资产"
        description="从生成页选中候选后，资产将出现在这里"
      />
    );
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
        gap: 'var(--sp-3)',
      }}
    >
      {assets.map((asset) => (
        <AssetCard
          key={asset.id}
          asset={asset}
          selected={selectedIds.has(asset.id)}
          onSelect={() => onToggleSelect(asset.id)}
          onDetail={() => onDetail(asset.id)}
        />
      ))}
    </div>
  );
}
