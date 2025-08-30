import { Outlet } from "react-router-dom";
import { motion } from "framer-motion";
import { AppSidebar } from "./AppSidebar";
import { AppHeader } from "./AppHeader";

interface AppLayoutProps {
  user: any;
  onLogout: () => void;
}

export function AppLayout({ user, onLogout }: AppLayoutProps) {
  return (
    <div className="h-screen flex bg-background">
      {/* Sidebar */}
      <AppSidebar />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <AppHeader user={user} onLogout={onLogout} />

        {/* Page Content */}
        <motion.main
          className="flex-1 overflow-auto p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <Outlet />
        </motion.main>
      </div>
    </div>
  );
}
