import type { ExportRecord } from '../../types';

interface ExportHistoryProps {
  records: ExportRecord[];
  onOpenFolder: (path: string) => void;
  onDelete: (id: string) => void;
}

const formatLabel: Record<string, string> = {
  png_single: '单图 PNG',
  spritesheet_png_json: 'Sprite Sheet + JSON',
  tileset_png_json: 'Tileset + JSON',
};

export function ExportHistory({ records, onOpenFolder, onDelete }: ExportHistoryProps) {
  if (records.length === 0) return null;

  return (
    <div>
      <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: 'var(--sp-3)', color: 'var(--text-1)' }}>
        导出历史
      </h3>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--sp-2)',
        }}
      >
        {records.map((record) => (
          <div
            key={record.id}
            className="nq-card"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: 'var(--sp-2) var(--sp-3)',
            }}
          >
            <div>
              <div style={{ fontSize: '13px', color: 'var(--text-1)' }}>
                {formatLabel[record.export_format] ?? record.export_format}
                {' · '}
                {record.file_size > 0 ? `${(record.file_size / 1024).toFixed(1)} KB` : '未知大小'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-3)' }}>
                {new Date(record.created_at).toLocaleString()}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 'var(--sp-1)' }}>
              <button
                className="nq-btn nq-btn--sm"
                onClick={() => onOpenFolder(record.export_path)}
              >
                打开文件夹
              </button>
              <button
                className="nq-btn nq-btn--sm nq-btn--danger"
                onClick={() => onDelete(record.id)}
              >
                删除
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
