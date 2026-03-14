import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";

type AuthContextType = {
  isAuthenticated: boolean;
  login: (password: string) => boolean;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => sessionStorage.getItem("authenticated") === "true"
  );

  if (!import.meta.env.VITE_APP_PASSWORD) {
    console.warn(
      "VITE_APP_PASSWORD is not set. No password will grant access. " +
        "Add VITE_APP_PASSWORD to frontend/.env"
    );
  }

  const login = useCallback((password: string) => {
    if (password === import.meta.env.VITE_APP_PASSWORD) {
      sessionStorage.setItem("authenticated", "true");
      setIsAuthenticated(true);
      return true;
    }
    return false;
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem("authenticated");
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
