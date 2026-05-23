interface EmptyStateProps {
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="var(--text-3)" strokeWidth="1.2">
        <rect x="4" y="4" width="24" height="24" rx="4" />
        <path d="M4 20l6-6 5 5 4-4 9 9" opacity="0.4" />
        <circle cx="11" cy="12" r="2.5" opacity="0.4" />
      </svg>
      <div className="empty-state-title">{title}</div>
      {description && <div className="empty-state-desc">{description}</div>}
      {action && (
        <button className="nq-btn nq-btn--accent nq-btn--sm" onClick={action.onClick} style={{ marginTop: 'var(--sp-2)' }}>
          {action.label}
        </button>
      )}
    </div>
  );
}
