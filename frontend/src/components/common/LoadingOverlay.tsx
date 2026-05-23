export function LoadingOverlay({ message = 'Loading...' }: { message?: string }) {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 'var(--sp-2)',
        background: 'rgba(13,13,15,0.7)',
        zIndex: 100,
      }}
    >
      <div style={{ width: 24, height: 24, border: '2px solid var(--border-1)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
      <span style={{ font: '400 12px var(--font)', color: 'var(--text-3)' }}>{message}</span>
    </div>
  );
}
