import { ImagePreview } from '../common/ImagePreview';
import { AnimationPlayer } from './AnimationPlayer';
import type { Asset, GenerationRecord, AnimationResponse } from '../../types';

interface AssetDetailPanelProps {
  asset: Asset;
  records: GenerationRecord[];
  animation: AnimationResponse | null;
  onClose: () => void;
  onReproduce: (recordId: string) => void;
  onVariant: (recordId: string) => void;
  onDelete: (assetId: string) => void;
}

export function AssetDetailPanel({
  asset,
  records,
  animation,
  onClose,
  onReproduce,
  onVariant,
  onDelete,
}: AssetDetailPanelProps) {
  return (
    <div
      style={{
        position: 'fixed',
        right: 0,
        top: 0,
        bottom: 0,
        width: '400px',
        backgroundColor: 'var(--bg-1)',
        borderLeft: '1px solid var(--border-1)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 1000,
        animation: 'slideInRight 0.2s ease',
        overflowY: 'auto',
      }}
    >
      {/* 标题栏 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 'var(--sp-3) var(--sp-4)',
          borderBottom: '1px solid var(--border-1)',
        }}
      >
        <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-1)' }}>{asset.name}</h3>
        <button
          className="nq-btn nq-btn--sm"
          onClick={onClose}
        >
          &#10005;
        </button>
      </div>

      <div
        style={{
          flex: 1,
          padding: 'var(--sp-4)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--sp-4)',
        }}
      >
        {/* 图片预览 / 动画播放 */}
        {animation && animation.frames.length > 0 ? (
          <AnimationPlayer
            frames={animation.frames}
            frameDelayMs={animation.frame_delay_ms}
            actions={animation.actions}
          />
        ) : (
          <ImagePreview
            src={asset.source_path}
            alt={asset.name}
            style={{ width: '100%', height: '200px' }}
          />
        )}

        {/* 基本信息 */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--sp-2)',
          }}
        >
          <InfoRow label="类型" value={asset.asset_type} />
          <InfoRow label="状态" value={asset.status} />
          {asset.tags.length > 0 && (
            <div>
              <span
                style={{
                  fontSize: '12px',
                  color: 'var(--text-3)',
                  marginRight: 'var(--sp-2)',
                }}
              >
                标签
              </span>
              {asset.tags.map((tag) => (
                <span
                  key={tag}
                  className="nq-tag"
                  style={{
                    background: 'rgba(255,255,255,0.04)',
                    marginRight: 'var(--sp-1)',
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* 生成参数 */}
        {records.length > 0 && (
          <div>
            <h4
              style={{
                fontSize: '13px',
                fontWeight: 600,
                marginBottom: 'var(--sp-2)',
                color: 'var(--text-1)',
              }}
            >
              生成参数
            </h4>
            {records.map((record) => (
              <div
                key={record.id}
                style={{
                  fontSize: '12px',
                  color: 'var(--text-2)',
                  lineHeight: 1.6,
                  marginBottom: 'var(--sp-2)',
                }}
              >
                <InfoRow label="原始 Prompt" value={record.user_prompt} />
                <InfoRow label="优化 Prompt" value={record.optimized_prompt} />
                <InfoRow label="模型" value={`${record.api_provider}/${record.api_model}`} />
              </div>
            ))}
          </div>
        )}

        {/* 操作按钮 */}
        <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
          {records.length > 0 && (
            <>
              <button
                className="nq-btn nq-btn--sm"
                onClick={() => onReproduce(records[0].id)}
              >
                复现
              </button>
              <button
                className="nq-btn nq-btn--sm"
                onClick={() => onVariant(records[0].id)}
              >
                变体
              </button>
            </>
          )}
          <button
            className="nq-btn nq-btn--sm nq-btn--danger"
            onClick={() => onDelete(asset.id)}
          >
            删除
          </button>
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', gap: 'var(--sp-2)', fontSize: '12px' }}>
      <span style={{ color: 'var(--text-3)', minWidth: '80px' }}>
        {label}
      </span>
      <span
        style={{
          color: 'var(--text-2)',
          wordBreak: 'break-word',
          flex: 1,
        }}
      >
        {value}
      </span>
    </div>
  );
}
