import { useState, useEffect, useRef } from 'react';
import { backendUrl } from '../../services/api';

interface AnimationPlayerProps {
  frames: string[];
  frameDelayMs: number;
  actions?: Record<string, number[]>;
}

export function AnimationPlayer({
  frames,
  frameDelayMs,
  actions,
}: AnimationPlayerProps) {
  const [playing, setPlaying] = useState(true);
  const [frameIndex, setFrameIndex] = useState(0);
  const [speed, setSpeed] = useState(frameDelayMs);
  const [selectedAction, setSelectedAction] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);

  const activeFrames = selectedAction && actions?.[selectedAction]
    ? actions[selectedAction].map((i) => frames[i]).filter(Boolean)
    : frames;

  useEffect(() => {
    if (playing && activeFrames.length > 0) {
      intervalRef.current = window.setInterval(() => {
        setFrameIndex((prev) => (prev + 1) % activeFrames.length);
      }, speed);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, speed, activeFrames.length]);

  if (frames.length === 0) return null;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--sp-2)',
      }}
    >
      {/* 预览区 */}
      <div
        className="checkerboard"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '100%',
          height: '200px',
          borderRadius: 'var(--r-md)',
          overflow: 'hidden',
        }}
      >
        <img
          src={backendUrl(activeFrames[frameIndex])}
          alt={`Frame ${frameIndex}`}
          style={{
            maxWidth: '100%',
            maxHeight: '100%',
            objectFit: 'contain',
            imageRendering: 'pixelated',
          }}
        />
      </div>

      {/* 控制栏 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--sp-2)',
        }}
      >
        <button className="nq-btn nq-btn--sm" onClick={() => setPlaying(!playing)}>
          {playing ? '暂停' : '播放'}
        </button>

        {/* 帧率调节 */}
        <label
          style={{
            fontSize: '11px',
            color: 'var(--text-3)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--sp-1)',
          }}
        >
          {speed}ms
          <input
            type="range"
            min={50}
            max={500}
            step={50}
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            style={{ width: '80px' }}
          />
        </label>

        <span
          style={{
            fontSize: '11px',
            color: 'var(--text-3)',
            marginLeft: 'auto',
          }}
        >
          {frameIndex + 1} / {activeFrames.length}
        </span>
      </div>

      {/* 动作选择 */}
      {actions && Object.keys(actions).length > 0 && (
        <div style={{ display: 'flex', gap: 'var(--sp-1)', flexWrap: 'wrap' }}>
          <button
            className={selectedAction === null ? 'nq-btn nq-btn--accent nq-btn--sm' : 'nq-btn nq-btn--sm'}
            onClick={() => setSelectedAction(null)}
          >
            全部
          </button>
          {Object.keys(actions).map((action) => (
            <button
              key={action}
              className={selectedAction === action ? 'nq-btn nq-btn--accent nq-btn--sm' : 'nq-btn nq-btn--sm'}
              onClick={() => {
                setSelectedAction(action);
                setFrameIndex(0);
              }}
            >
              {action}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
