import type { StyleProfile } from '../../types';

interface StylePreviewProps {
  style: StyleProfile;
}

export function StylePreview({ style }: StylePreviewProps) {
  return (
    <div
      className="nq-card"
      style={{ padding: 'var(--sp-3)' }}
    >
      <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: 'var(--sp-2)', color: 'var(--text-1)' }}>
        风格参数
      </h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-1)', fontSize: '12px', color: 'var(--text-2)' }}>
        <div>画风：{style.art_style}</div>
        <div>尺寸：{style.default_size.w} x {style.default_size.h}</div>
        <div>视角：{style.perspective}</div>
        {style.reference_image_path && (
          <div>
            参考图：
            <img
              src={style.reference_image_path}
              alt="参考图"
              style={{ maxWidth: '100px', maxHeight: '100px', marginTop: 'var(--sp-1)', borderRadius: 'var(--r-sm)' }}
            />
          </div>
        )}
        {style.extra_params && (
          <div>
            额外参数：
            <pre style={{ font: '400 11px var(--mono)', margin: 0, whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(style.extra_params, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
