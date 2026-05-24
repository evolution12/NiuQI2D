import { useId } from 'react';

interface ModelSelectorProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}

export function ModelSelector({ label, value, onChange, options }: ModelSelectorProps) {
  const listId = useId();

  return (
    <div className="form-row">
      <label className="form-label">{label}</label>
      <input
        className="nq-input"
        list={listId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="选择或输入模型标识"
        style={{ width: '100%' }}
      />
      <datalist id={listId}>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} label={opt.label} />
        ))}
      </datalist>
    </div>
  );
}
