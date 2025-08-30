import { Bell, Search, User, LogOut, Settings } from "lucide-react";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { authApi } from "@/lib/api";

interface AppHeaderProps {
  user: any;
  onLogout: () => void;
}

export function AppHeader({ user, onLogout }: AppHeaderProps) {
  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      onLogout();
    }
  };

  return (
    <motion.header
      className="h-header neumorphic-card border-b border-border/50 px-6 flex items-center justify-between"
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Search */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground"
            size={16}
          />
          <Input
            placeholder="Search documents, policies, or compliance rules..."
            className="neumorphic-input pl-10 pr-4 py-2 w-full"
          />
        </div>
      </div>

      {/* Right side actions */}
      <div className="flex items-center space-x-3">
        {/* Notifications */}
        <Button
          variant="ghost"
          size="sm"
          className="neumorphic-button p-2 rounded-xl relative"
        >
          <Bell size={18} />
          <span className="absolute -top-1 -right-1 h-4 w-4 bg-danger rounded-full text-xs text-danger-foreground flex items-center justify-center">
            3
          </span>
        </Button>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="neumorphic-button p-2 rounded-xl"
            >
              <User size={18} />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-56 neumorphic-card border-0"
          >
            <DropdownMenuLabel>
              {user?.first_name} {user?.last_name}
              <div className="text-xs text-muted-foreground font-normal">
                {user?.email}
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </motion.header>
  );
}
