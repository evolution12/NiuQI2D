interface ModelSelectorProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}

export function ModelSelector({ label, value, onChange, options }: ModelSelectorProps) {
  return (
    <div className="form-row">
      <label className="form-label">{label}</label>
      <select className="nq-select" value={value} onChange={(e) => onChange(e.target.value)} style={{ width: '100%' }}>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );
}
