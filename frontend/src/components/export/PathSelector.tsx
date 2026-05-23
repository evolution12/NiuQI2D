interface PathSelectorProps {
  value: string;
  onChange: (path: string) => void;
}

export function PathSelector({ value, onChange }: PathSelectorProps) {
  const handleSelect = async () => {
    const electronAPI = (window as any).electronAPI;
    if (electronAPI?.fs?.selectDirectory) {
      const path = await electronAPI.fs.selectDirectory();
      if (path) onChange(path);
    } else {
      // fallback：手动输入
      const path = prompt('输入导出路径：', value);
      if (path) onChange(path);
    }
  };

  return (
    <div className="form-row">
      <label className="form-label">导出路径</label>
      <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
        <input
          className="nq-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="选择或输入导出目录路径"
          style={{ flex: 1 }}
        />
        <button className="nq-btn" onClick={handleSelect}>
          浏览
        </button>
      </div>
    </div>
  );
}
