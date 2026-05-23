import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/sidebar/Sidebar';

export function MainLayout() {
  return (
    <div style={{ display: 'flex', height: '100%' }}>
      <Sidebar />
      <main
        style={{
          flex: 1,
          overflow: 'auto',
          background: 'var(--bg-0)',
        }}
      >
        <Outlet />
      </main>
    </div>
  );
}
