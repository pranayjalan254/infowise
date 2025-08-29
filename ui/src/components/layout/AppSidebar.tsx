import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  FileText,
  FlaskConical,
  BarChart3,
  Settings,
  Menu,
  X
} from 'lucide-react';
import { cn } from '@/lib/utils';

const sidebarItems = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard
  },
  {
    title: 'Document Ingestion',
    href: '/ingestion',
    icon: FileText
  },
  {
    title: 'Sandbox',
    href: '/sandbox',
    icon: FlaskConical
  },
  {
    title: 'Reports',
    href: '/reports',
    icon: BarChart3
  },
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings
  }
];

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <motion.div
      className={cn(
        "h-full neumorphic-card border-r transition-all duration-300",
        collapsed ? "w-sidebar-collapsed" : "w-sidebar"
      )}
      initial={false}
      animate={{
        width: collapsed ? 'var(--sidebar-collapsed)' : 'var(--sidebar-width)'
      }}
    >
      {/* Header */}
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center justify-between">
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center space-x-2"
            >
              <div className="w-8 h-8 neumorphic-raised rounded-xl flex items-center justify-center bg-primary">
                <span className="text-primary-foreground font-bold text-sm">I</span>
              </div>
              <span className="text-display text-lg text-foreground">Infowise</span>
            </motion.div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="neumorphic-button p-2 rounded-xl"
          >
            {collapsed ? <Menu size={16} /> : <X size={16} />}
          </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-2">
        {sidebarItems.map((item) => {
          const isActive = location.pathname === item.href;
          
          return (
            <NavLink
              key={item.href}
              to={item.href}
              className={cn(
                "flex items-center space-x-3 px-3 py-3 rounded-xl transition-all duration-200",
                "neumorphic-button text-sidebar-foreground hover:text-sidebar-primary",
                isActive && "neumorphic-pressed bg-sidebar-primary text-sidebar-primary-foreground"
              )}
            >
              <item.icon size={20} className="flex-shrink-0" />
              {!collapsed && (
                <motion.span
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className="text-sm font-medium"
                >
                  {item.title}
                </motion.span>
              )}
            </NavLink>
          );
        })}
      </nav>
    </motion.div>
  );
}