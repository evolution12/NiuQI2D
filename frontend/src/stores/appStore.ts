import { create } from 'zustand';
import type { Project, StyleProfile, TaskInfo } from '../types';

export interface AppState {
  // Python 服务状态
  pythonReady: boolean;
  pythonPort: number | null;

  // 当前项目上下文
  currentProject: Project | null;
  currentStyle: StyleProfile | null;

  // 项目列表
  projects: Project[];

  // 全局任务状态
  activeTasks: TaskInfo[];

  // Actions
  setPythonReady: (ready: boolean) => void;
  setPythonPort: (port: number | null) => void;
  setCurrentProject: (project: Project | null) => void;
  setCurrentStyle: (style: StyleProfile | null) => void;
  setProjects: (projects: Project[]) => void;
  addTask: (task: TaskInfo) => void;
  updateTask: (taskId: string, updates: Partial<TaskInfo>) => void;
  removeTask: (taskId: string) => void;
  loadProjects: () => Promise<void>;
  switchProject: (id: string) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  pythonReady: false,
  pythonPort: null,
  currentProject: null,
  currentStyle: null,
  projects: [],
  activeTasks: [],

  setPythonReady: (ready) => set({ pythonReady: ready }),
  setPythonPort: (port) => set({ pythonPort: port }),
  setCurrentProject: (project) => set({ currentProject: project }),
  setCurrentStyle: (style) => set({ currentStyle: style }),
  setProjects: (projects) => set({ projects }),

  addTask: (task) =>
    set((state) => ({ activeTasks: [...state.activeTasks, task] })),

  updateTask: (taskId, updates) =>
    set((state) => ({
      activeTasks: state.activeTasks.map((t) =>
        t.id === taskId ? { ...t, ...updates } : t,
      ),
    })),

  removeTask: (taskId) =>
    set((state) => ({
      activeTasks: state.activeTasks.filter((t) => t.id !== taskId),
    })),

  loadProjects: async () => {
    try {
      const { projectApi } = await import('../services/api');
      const projects = await projectApi.list();
      set({ projects });
      // 如果有当前项目但不在列表中了，清空
      const { currentProject } = get();
      if (currentProject && !projects.find((p) => p.id === currentProject.id)) {
        set({ currentProject: null });
      }
    } catch {
      // 后端未就绪时静默处理
    }
  },

  switchProject: (id) => {
    const { projects } = get();
    const project = projects.find((p) => p.id === id) ?? null;
    set({ currentProject: project });
  },
}));
