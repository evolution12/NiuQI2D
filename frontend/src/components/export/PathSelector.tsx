import { useRef } from 'react';

interface PathSelectorProps {
  value: string;
  onChange: (path: string) => void;
}

export function PathSelector({ value, onChange }: PathSelectorProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSelect = async () => {
    const electronAPI = (window as any).electronAPI;
    if (electronAPI?.fs?.selectDirectory) {
      const path = await electronAPI.fs.selectDirectory();
      if (path) onChange(path);
      return;
    }

    // Dev mode fallback: use native directory picker if available
    if (window.showDirectoryPicker) {
      try {
        const dirHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
        onChange(dirHandle.name);
        return;
      } catch {
        // User cancelled
        return;
      }
    }

    // Final fallback: trigger hidden file input
    fileInputRef.current?.click();
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      // webkitRelativePath gives "folderName/filename"
      const relativePath = files[0].webkitRelativePath;
      const folderName = relativePath.split('/')[0];
      // Use the full path if available (Electron), otherwise just folder name
      const fullPath = (files[0] as any).path || folderName;
      onChange(fullPath);
    }
    // Reset so same folder can be selected again
    e.target.value = '';
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
        <input
          ref={fileInputRef}
          type="file"
          style={{ display: 'none' }}
          onChange={handleFileInput}
          /* @ts-expect-error webkitdirectory is not in React types */
          webkitdirectory=""
          directory=""
        />
      </div>
    </div>
  );
}
