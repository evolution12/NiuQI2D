import { useAppStore } from '../../stores/appStore';
import { projectApi } from '../../services/api';
import { toast } from '../common/Toast';

export function ProjectList() {
  const projects = useAppStore((s) => s.projects);
  const currentProject = useAppStore((s) => s.currentProject);
  const switchProject = useAppStore((s) => s.switchProject);
  const loadProjects = useAppStore((s) => s.loadProjects);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this project and all associated assets?')) return;
    try {
      await projectApi.delete(id);
      toast.success('Project deleted');
      loadProjects();
    } catch (err: any) {
      toast.error('Failed: ' + (err.message ?? 'unknown'));
    }
  };

  if (!projects.length) {
    return <div style={{ padding: 'var(--sp-3) var(--sp-4)', font: '400 11px var(--font)', color: 'var(--text-3)' }}>No projects yet</div>;
  }

  return (
    <div>
      {projects.map((p) => (
        <div
          key={p.id}
          className={`sidebar-project ${currentProject?.id === p.id ? 'sidebar-project--active' : ''}`}
          onClick={() => switchProject(p.id)}
        >
          <span className="sidebar-project-name">{p.name}</span>
          <button className="sidebar-project-del" onClick={(e) => handleDelete(p.id, e)} title="Delete">
            <svg width="10" height="10" viewBox="0 0 10 10" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinecap="round"><path d="M1 1l8 8M9 1l-8 8" /></svg>
          </button>
        </div>
      ))}
    </div>
  );
}
