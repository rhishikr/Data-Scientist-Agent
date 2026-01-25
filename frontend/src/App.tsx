import { useState } from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarInset,
} from "./components/ui/sidebar";
import {
  Home,
  Database,
  GitBranch,
  Users,
  Package,
  MessageSquare,
  FileText,
  Settings,
  ChevronDown,
} from "lucide-react";
import { Button } from "./components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "./components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./components/ui/dropdown-menu";
import { HomeScreen } from "./components/HomeScreen";
import { DataSourcesScreen } from "./components/DataSourcesScreen";
import { PipelineScreen } from "./components/PipelineScreen";
import { CustomerInsightsScreen } from "./components/CustomerInsightsScreen";
import { InventorySalesScreen } from "./components/InventorySalesScreen";
import { LLMAssistantScreen } from "./components/LLMAssistantScreen";
import { ReportsScreen } from "./components/ReportsScreen";
import { SettingsScreen } from "./components/SettingsScreen";

const menuItems = [
  { id: "home", label: "Home", icon: Home },
  { id: "data-sources", label: "Data Sources", icon: Database },
  { id: "pipelines", label: "Pipelines", icon: GitBranch },
  { id: "customer-insights", label: "Customer Insights", icon: Users },
  { id: "inventory-sales", label: "Inventory & Sales", icon: Package },
  { id: "llm-assistant", label: "LLM Assistant", icon: MessageSquare },
  { id: "reports", label: "Reports", icon: FileText },
  { id: "settings", label: "Settings", icon: Settings },
];

export default function App() {
  const [activeSection, setActiveSection] = useState("home");
  const [environment, setEnvironment] = useState("Demo Store");

  const renderContent = () => {
    switch (activeSection) {
      case "home":
        return <HomeScreen />;
      case "data-sources":
        return <DataSourcesScreen />;
      case "pipelines":
        return <PipelineScreen />;
      case "customer-insights":
        return <CustomerInsightsScreen />;
      case "inventory-sales":
        return <InventorySalesScreen />;
      case "llm-assistant":
        return <LLMAssistantScreen />;
      case "reports":
        return <ReportsScreen />;
      case "settings":
        return <SettingsScreen />;
      default:
        return <HomeScreen />;
    }
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-slate-50">
        <Sidebar className="border-r bg-white">
          <SidebarContent>
            <div className="px-4 py-6 border-b">
              <div className="flex items-center gap-2">
                <div className="size-8 rounded-lg bg-gradient-to-br from-teal-500 to-blue-600 flex items-center justify-center">
                  <GitBranch className="size-4 text-white" />
                </div>
                <div>
                  <h2 className="text-sm">AI Data Scientist</h2>
                  <p className="text-xs text-muted-foreground">Agent</p>
                </div>
              </div>
            </div>
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>
                  {menuItems.map((item) => (
                    <SidebarMenuItem key={item.id}>
                      <SidebarMenuButton
                        onClick={() => setActiveSection(item.id)}
                        isActive={activeSection === item.id}
                        className="px-4 py-3"
                      >
                        <item.icon className="size-5" />
                        <span>{item.label}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
        </Sidebar>

        <SidebarInset className="flex-1">
          {/* Top Bar */}
          <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-6 py-4">
            <div className="flex items-center gap-4">
              <h1 className="text-lg">AI Data Scientist Agent</h1>
              <div className="h-6 w-px bg-border" />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" className="gap-2">
                    {environment}
                    <ChevronDown className="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start">
                  <DropdownMenuLabel>Switch Environment</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => setEnvironment("Demo Store")}
                  >
                    Demo Store
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setEnvironment("Client A")}>
                    Client A
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setEnvironment("Client B")}>
                    Client B
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <div className="flex items-center gap-4">
              <Button variant="ghost" size="sm">
                Documentation
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="rounded-full">
                    <Avatar className="size-8">
                      <AvatarImage src="" />
                      <AvatarFallback>JD</AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>My Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>Profile</DropdownMenuItem>
                  <DropdownMenuItem>Billing</DropdownMenuItem>
                  <DropdownMenuItem>Team</DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>Log out</DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* Main Content */}
          <main className="p-6">{renderContent()}</main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
