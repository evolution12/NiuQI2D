import { useState } from 'react';
import { settingsApi } from '../../services/api';
import { toast } from '../common/Toast';

interface ApiConfigSectionProps {
  title: string;
  provider: string;
  keySet: boolean;
  model: string;
  onProviderChange: (v: string) => void;
  onKeyChange: (v: string) => void;
  onModelChange: (v: string) => void;
  testEndpoint: 'testImageApi' | 'testTextApi';
}

export function ApiConfigSection({
  title,
  provider,
  keySet,
  model,
  onProviderChange,
  onKeyChange,
  onModelChange,
  testEndpoint,
}: ApiConfigSectionProps) {
  const [apiKey, setApiKey] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency_ms: number | null } | null>(null);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await settingsApi[testEndpoint]();
      setTestResult(result);
      if (result.success) {
        toast.success(`${title}连接成功 (${result.latency_ms}ms)`);
      } else {
        toast.error(`${title}连接失败：${result.message}`);
      }
    } catch (e: any) {
      setTestResult({ success: false, message: e.message, latency_ms: null });
      toast.error('测试失败');
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="nq-section">
      <div className="nq-section-title">{title}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
        <div className="form-row">
          <label className="form-label">供应商</label>
          <select className="nq-select" value={provider} onChange={(e) => onProviderChange(e.target.value)} style={{ width: '100%' }}>
            <option value="openai">OpenAI</option>
            <option value="other">其他</option>
          </select>
        </div>

        <div className="form-row">
          <label className="form-label">API Key</label>
          <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
            <input
              className="nq-input"
              type="password"
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                onKeyChange(e.target.value);
              }}
              placeholder={keySet ? '已设置（输入以更新）' : '输入 API Key'}
              style={{ flex: 1 }}
            />
            <button className="nq-btn nq-btn--sm" onClick={handleTest} disabled={testing}>
              {testing ? '测试中...' : '测试连接'}
            </button>
          </div>
          {testResult && (
            <div
              style={{
                fontSize: '12px',
                marginTop: 'var(--sp-1)',
                color: testResult.success ? 'var(--green)' : 'var(--red)',
              }}
            >
              {testResult.message}
              {testResult.latency_ms && ` (${testResult.latency_ms}ms)`}
            </div>
          )}
        </div>

        <div className="form-row">
          <label className="form-label">模型</label>
          <input
            className="nq-input"
            value={model}
            onChange={(e) => onModelChange(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>
      </div>
    </div>
  );
}
