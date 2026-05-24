import { useState } from 'react';
import { settingsApi } from '../../services/api';
import { toast } from '../common/Toast';

interface ApiConfigSectionProps {
  title: string;
  provider: string;
  /** OpenAI fields */
  keySet: boolean;
  model: string;
  /** Volcengine fields */
  volcengineKeySet?: boolean;
  volcengineReqKey?: string;
  /** Doubao fields */
  doubaoKeySet?: boolean;
  doubaoModel?: string;
  /** Callbacks */
  onProviderChange: (v: string) => void;
  onKeyChange: (v: string) => void;
  onModelChange: (v: string) => void;
  onVolcengineAccessKeyChange?: (v: string) => void;
  onVolcengineSecretKeyChange?: (v: string) => void;
  onVolcengineReqKeyChange?: (v: string) => void;
  onDoubaoKeyChange?: (v: string) => void;
  onDoubaoModelChange?: (v: string) => void;
  /** Which test endpoint to call */
  testEndpoint: 'testImageApi' | 'testTextApi';
  /** Show volcengine option */
  showVolcengine?: boolean;
  /** Show doubao option */
  showDoubao?: boolean;
  /** Show deepseek option */
  showDeepSeek?: boolean;
}

export function ApiConfigSection({
  title,
  provider,
  keySet,
  model,
  volcengineKeySet = false,
  volcengineReqKey = '',
  doubaoKeySet = false,
  doubaoModel = '',
  onProviderChange,
  onKeyChange,
  onModelChange,
  onVolcengineAccessKeyChange,
  onVolcengineSecretKeyChange,
  onVolcengineReqKeyChange,
  onDoubaoKeyChange,
  onDoubaoModelChange,
  testEndpoint,
  showVolcengine = false,
  showDoubao = false,
  showDeepSeek = false,
}: ApiConfigSectionProps) {
  const [apiKey, setApiKey] = useState('');
  const [veAk, setVeAk] = useState('');
  const [veSk, setVeSk] = useState('');
  const [doubaoKey, setDoubaoKey] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency_ms: number | null } | null>(null);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      // 构建测试请求体：传入用户当前输入，后端在值为空时回退到已保存配置
      let body: Record<string, string>;
      if (testEndpoint === 'testTextApi') {
        body = { provider, api_key: apiKey, model };
      } else {
        body = {
          provider,
          api_key: apiKey,
          model,
          volcengine_access_key: veAk,
          volcengine_secret_key: veSk,
          volcengine_req_key: volcengineReqKey,
          doubao_api_key: doubaoKey,
          doubao_model: doubaoModel,
        };
      }
      const result = await settingsApi[testEndpoint](body);
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

  const isVolcengine = provider === 'volcengine';
  const isDoubao = provider === 'doubao';
  const isDeepSeek = provider === 'deepseek';
  // OpenAI-compatible providers share the same API Key + Model UI
  const isOpenAIStyle = !isVolcengine && !isDoubao;

  return (
    <div className="nq-section">
      <div className="nq-section-title">{title}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
        {/* Provider selector */}
        <div className="form-row">
          <label className="form-label">供应商</label>
          <select className="nq-select" value={provider} onChange={(e) => onProviderChange(e.target.value)} style={{ width: '100%' }}>
            <option value="openai">OpenAI</option>
            {showDeepSeek && <option value="deepseek">DeepSeek</option>}
            {showDoubao && <option value="doubao">豆包（Ark API）</option>}
            {showVolcengine && <option value="volcengine">火山引擎（Visual API）</option>}
          </select>
        </div>

        {/* OpenAI / DeepSeek fields */}
        {isOpenAIStyle && (
          <>
            <div className="form-row">
              <label className="form-label">API Key</label>
              <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
                <input
                  className="nq-input"
                  type="password"
                  value={apiKey}
                  onChange={(e) => { setApiKey(e.target.value); onKeyChange(e.target.value); }}
                  placeholder={keySet ? '已设置（输入以更新）' : isDeepSeek ? '输入 DeepSeek API Key（sk-...）' : '输入 API Key'}
                  style={{ flex: 1 }}
                />
                <button className="nq-btn nq-btn--sm" onClick={handleTest} disabled={testing}>
                  {testing ? '测试中...' : '测试连接'}
                </button>
              </div>
            </div>
            <div className="form-row">
              <label className="form-label">模型</label>
              <input
                className="nq-input"
                value={model}
                onChange={(e) => onModelChange(e.target.value)}
                placeholder={isDeepSeek ? 'deepseek-chat' : ''}
                style={{ width: '100%' }}
              />
            </div>
          </>
        )}

        {/* Doubao fields */}
        {isDoubao && (
          <>
            <div className="form-row">
              <label className="form-label">API Key</label>
              <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
                <input
                  className="nq-input"
                  type="password"
                  value={doubaoKey}
                  onChange={(e) => { setDoubaoKey(e.target.value); onDoubaoKeyChange?.(e.target.value); }}
                  placeholder={doubaoKeySet ? '已设置（输入以更新）' : '输入 Ark API Key（ark-...）'}
                  style={{ flex: 1 }}
                />
                <button className="nq-btn nq-btn--sm" onClick={handleTest} disabled={testing}>
                  {testing ? '测试中...' : '测试连接'}
                </button>
              </div>
            </div>
            <div className="form-row">
              <label className="form-label">模型</label>
              <input
                className="nq-input"
                value={doubaoModel}
                onChange={(e) => onDoubaoModelChange?.(e.target.value)}
                placeholder="doubao-seedream-4-5-251128"
                style={{ width: '100%' }}
              />
            </div>
          </>
        )}

        {/* Volcengine fields */}
        {isVolcengine && (
          <>
            <div className="form-row">
              <label className="form-label">Access Key (AK)</label>
              <input
                className="nq-input"
                type="password"
                value={veAk}
                onChange={(e) => { setVeAk(e.target.value); onVolcengineAccessKeyChange?.(e.target.value); }}
                placeholder={volcengineKeySet ? '已设置（输入以更新）' : '输入 Access Key'}
                style={{ width: '100%' }}
              />
            </div>
            <div className="form-row">
              <label className="form-label">Secret Key (SK)</label>
              <input
                className="nq-input"
                type="password"
                value={veSk}
                onChange={(e) => { setVeSk(e.target.value); onVolcengineSecretKeyChange?.(e.target.value); }}
                placeholder="输入 Secret Key"
                style={{ width: '100%' }}
              />
            </div>
            <div className="form-row">
              <label className="form-label">模型标识 (req_key)</label>
              <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
                <input
                  className="nq-input"
                  value={volcengineReqKey}
                  onChange={(e) => onVolcengineReqKeyChange?.(e.target.value)}
                  placeholder="high_aes_general_v21"
                  style={{ flex: 1 }}
                />
                <button className="nq-btn nq-btn--sm" onClick={handleTest} disabled={testing}>
                  {testing ? '测试中...' : '测试连接'}
                </button>
              </div>
            </div>
          </>
        )}

        {/* Test result */}
        {testResult && (
          <div style={{ fontSize: '12px', color: testResult.success ? 'var(--green)' : 'var(--red)' }}>
            {testResult.message}
            {testResult.latency_ms != null && ` (${testResult.latency_ms}ms)`}
          </div>
        )}
      </div>
    </div>
  );
}
