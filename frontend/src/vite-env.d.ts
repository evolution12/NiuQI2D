/// <reference types="vite/client" />

interface Window {
  electronAPI?: {
    python: {
      getPort(): Promise<number>;
      isReady(): Promise<boolean>;
    };
    fs: {
      selectDirectory(): Promise<string | null>;
      selectFile(filters?: { name: string; extensions: string[] }[]): Promise<string | null>;
    };
    shell: {
      openPath(path: string): Promise<string | null>;
    };
    app: {
      getVersion(): string;
      getDataPath(): string;
      isDev(): boolean;
    };
  };
}
