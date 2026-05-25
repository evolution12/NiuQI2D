import { api } from '../../services/api';

interface PathSelectorProps {
  value: string;
  onChange: (path: string) => void;
}

export function PathSelector({ value, onChange }: PathSelectorProps) {
  const handleSelect = async () => {
    // Try Electron native dialog first
    const electronAPI = (window as any).electronAPI;
    if (electronAPI?.fs?.selectDirectory) {
      const path = await electronAPI.fs.selectDirectory();
      if (path) onChange(path);
      return;
    }

    // Use Python backend for native OS directory picker
    try {
      const res = await api.post<{ path: string | null }>('/utils/select-directory');
      if (res.path) onChange(res.path);
    } catch {
      // Fallback to browser File System Access API
      try {
        // @ts-expect-error File System Access API not in all TS libs
        const dirHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
        onChange(dirHandle.name);
      } catch {
        // User cancelled
      }
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
          placeholder="例如: C:\exports 或 /home/user/exports"
          style={{ flex: 1 }}
        />
        <button className="nq-btn" onClick={handleSelect}>
          浏览
        </button>
      </div>
    </div>
  );
}
