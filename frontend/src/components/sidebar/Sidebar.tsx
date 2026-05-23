import { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAppStore } from '../../stores/appStore';
import { projectApi, styleApi } from '../../services/api';
import { ProjectList } from './ProjectList';
import { ProjectCreateModal } from './ProjectCreateModal';
import { StyleLibrary } from '../style/StyleLibrary';
import { toast } from '../common/Toast';
import type { StyleProfile, CreateProjectRequest } from '../../types';

/* ---- SVG icons as inline components ---- */
const icons = {
  generate: (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41" />
      <circle cx="8" cy="8" r="2.5" />
    </svg>
  ),
  assets: (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="5" height="5" rx="1" /><rect x="9" y="2" width="5" height="5" rx="1" />
      <rect x="2" y="9" width="5" height="5" rx="1" /><rect x="9" y="9" width="5" height="5" rx="1" />
    </svg>
  ),
  export: (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 10v3a1 1 0 001 1h10a1 1 0 001-1v-3M8 2v8M5 5l3-3 3 3" />
    </svg>
  ),
  style: (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="4" cy="4" r="2" /><circle cx="12" cy="4" r="2" />
      <circle cx="4" cy="12" r="2" /><circle cx="12" cy="12" r="2" />
      <path d="M6 4h4M6 12h4M4 6v4M12 6v4" />
    </svg>
  ),
  settings: (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="8" r="2.5" />
      <path d="M13.3 10a1.2 1.2 0 00.2 1.3l.1.1a1.45 1.45 0 11-2.05 2.05l-.1-.1a1.2 1.2 0 00-1.3-.2 1.2 1.2 0 00-.73 1.1v.3a1.45 1.45 0 01-2.9 0v-.15A1.2 1.2 0 005.7 13a1.2 1.2 0 00-1.3.2l-.1.1A1.45 1.45 0 111.25 11.2l.1-.1A1.2 1.2 0 001.55 9.8a1.2 1.2 0 00-1.1-.73h-.3a1.45 1.45 0 010-2.9h.16a1.2 1.2 0 001.09-.75 1.2 1.2 0 00-.2-1.3l-.1-.1A1.45 1.45 0 113.05 1.95l.1.1a1.2 1.2 0 001.3.2h.06a1.2 1.2 0 00.73-1.1v-.3a1.45 1.45 0 012.9 0v.16a1.2 1.2 0 00.73 1.09 1.2 1.2 0 001.3-.2l.1-.1A1.45 1.45 0 1114.75 4.8l-.1.1a1.2 1.2 0 00-.2 1.3v.06a1.2 1.2 0 001.1.73h.3a1.45 1.45 0 010 2.9h-.16a1.2 1.2 0 00-1.09.73z" />
    </svg>
  ),
  plus: (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M6 1v10M1 6h10" />
    </svg>
  ),
};

export function Sidebar() {
  const activeTasks = useAppStore((s) => s.activeTasks);
  const loadProjects = useAppStore((s) => s.loadProjects);
  const switchProject = useAppStore((s) => s.switchProject);
  const runningTasks = activeTasks.filter((t) => t.status === 'running');

  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showStyleLibrary, setShowStyleLibrary] = useState(false);
  const [styles, setStyles] = useState<StyleProfile[]>([]);

  useEffect(() => {
    loadProjects();
    styleApi.list().then(setStyles).catch(() => {});
  }, [loadProjects]);

  const handleCreateProject = async (data: CreateProjectRequest) => {
    try {
      const project = await projectApi.create(data);
      await loadProjects();
      switchProject(project.id);
      setShowCreateProject(false);
      toast.success('项目已创建');
    } catch (e: any) {
      toast.error('操作失败: ' + (e.message ?? '未知错误'));
    }
  };

  return (
    <>
      <aside className="sidebar">
        {/* Brand */}
        <div className="sidebar-brand">
          <span className="sidebar-brand-name">NiuQI2D</span>
        </div>

        {/* Projects */}
        <div className="sidebar-section">
          <div className="sidebar-section-header">
            <span>项目</span>
            <button className="nq-btn nq-btn--sm" onClick={() => setShowCreateProject(true)}>
              {icons.plus}
            </button>
          </div>
          <ProjectList />
        </div>

        {/* Nav */}
        <nav className="sidebar-nav">
          <Nav route="/" label="生成" icon={icons.generate} />
          <Nav
            route="/assets"
            label="素材库"
            icon={icons.assets}
            badge={runningTasks.length || undefined}
          />
          <Nav route="/export" label="导出" icon={icons.export} />
          <NavButton label="风格" icon={icons.style} onClick={() => setShowStyleLibrary(true)} />
        </nav>

        {/* Footer */}
        <div className="sidebar-footer">
          <Nav route="/settings" label="设置" icon={icons.settings} />
        </div>
      </aside>

      {showCreateProject && (
        <ProjectCreateModal
          styles={styles}
          onConfirm={handleCreateProject}
          onCancel={() => setShowCreateProject(false)}
        />
      )}
      {showStyleLibrary && (
        <StyleLibrary onClose={() => setShowStyleLibrary(false)} />
      )}
    </>
  );
}

function Nav({ route, label, icon, badge }: { route: string; label: string; icon: React.ReactNode; badge?: number }) {
  const location = useLocation();
  const active = location.pathname === route;

  return (
    <NavLink
      to={route}
      className={`sidebar-link ${active ? 'sidebar-link--active' : ''}`}
    >
      <span className="sidebar-link-icon">{icon}</span>
      <span className="sidebar-link-label">{label}</span>
      {badge && <span className="sidebar-link-badge">{badge}</span>}
    </NavLink>
  );
}

function NavButton({ label, icon, onClick }: { label: string; icon: React.ReactNode; onClick: () => void }) {
  return (
    <button className="sidebar-link" onClick={onClick}>
      <span className="sidebar-link-icon">{icon}</span>
      <span className="sidebar-link-label">{label}</span>
    </button>
  );
}
