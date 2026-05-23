import type { ExportFormat } from '../../types';

interface ExportTypeSelectorProps {
  value: ExportFormat;
  onChange: (format: ExportFormat) => void;
}

const exportTypes: { format: ExportFormat; label: string; desc: string }[] = [
  { format: 'png_single', label: '单图 PNG', desc: '每个资产输出独立 PNG 文件' },
  { format: 'spritesheet_png_json', label: 'Sprite Sheet + JSON', desc: '多帧拼合为 Sprite Sheet，附 JSON 元数据' },
  { format: 'tileset_png_json', label: 'Tileset + JSON', desc: '多 Tile 拼合为 Tileset，附 JSON 元数据' },
];

export function ExportTypeSelector({ value, onChange }: ExportTypeSelectorProps) {
  return (
    <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
      {exportTypes.map(({ format, label, desc }) => (
        <button
          key={format}
          className={value === format ? 'nq-btn nq-btn--accent' : 'nq-btn'}
          onClick={() => onChange(format)}
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: 'var(--sp-3)',
            gap: 'var(--sp-1)',
          }}
        >
          <span style={{ fontSize: '13px', fontWeight: 500 }}>{label}</span>
          <span style={{ fontSize: '11px', color: 'var(--text-3)', fontWeight: 400 }}>
            {desc}
          </span>
        </button>
      ))}
    </div>
  );
}
