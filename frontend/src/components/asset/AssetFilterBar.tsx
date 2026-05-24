import type { AssetType, AssetStatus } from '../../types';

interface AssetFilterBarProps {
  assetType: AssetType | '';
  status: AssetStatus | '';
  search: string;
  tags: string[];
  selectedTag: string;
  onAssetTypeChange: (type: AssetType | '') => void;
  onStatusChange: (status: AssetStatus | '') => void;
  onSearchChange: (search: string) => void;
  onTagChange: (tag: string) => void;
}

export function AssetFilterBar({
  assetType,
  status,
  search,
  tags,
  selectedTag,
  onAssetTypeChange,
  onStatusChange,
  onSearchChange,
  onTagChange,
}: AssetFilterBarProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--sp-2)',
        flexWrap: 'wrap',
      }}
    >
      {/* 搜索 */}
      <input
        className="nq-input"
        type="text"
        placeholder="搜索资产..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{ width: '200px' }}
      />

      {/* 类型筛选 */}
      <select
        className="nq-select"
        value={assetType}
        onChange={(e) => onAssetTypeChange(e.target.value as AssetType | '')}
      >
        <option value="">全部类型</option>
        <option value="character">角色</option>
        <option value="tile">Tile</option>
        <option value="prop">道具</option>
        <option value="ui">UI</option>
        <option value="effect">特效</option>
      </select>

      {/* 状态筛选 */}
      <select
        className="nq-select"
        value={status}
        onChange={(e) => onStatusChange(e.target.value as AssetStatus | '')}
      >
        <option value="">全部状态</option>
        <option value="draft">草稿</option>
        <option value="selected">已选中</option>
        <option value="exported">已导出</option>
        <option value="discarded">已废弃</option>
      </select>

      {/* 标签筛选 */}
      {tags.length > 0 && (
        <select
          className="nq-select"
          value={selectedTag}
          onChange={(e) => onTagChange(e.target.value)}
        >
          <option value="">全部标签</option>
          {tags.map((tag) => (
            <option key={tag} value={tag}>
              {tag}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
