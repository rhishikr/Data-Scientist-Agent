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
  GitBranch,
  Users,
  MessageSquare,
  Settings,
  Table2,
} from "lucide-react";
import { DataSourcesScreen } from "./components/mockScreens/DataSourcesScreen";
import { PipelineScreen } from "./components/mockScreens/PipelineScreen";
import { CustomerInsightsScreen } from "./components/insightsScreen/CustomerInsightsScreen";
import { LLMAssistantScreen } from "./components/mockScreens/LLMAssistantScreen";
import { SettingsScreen } from "./components/mockScreens/SettingsScreen";
import { DataExplorerScreen } from "./components/insightsScreen/DataExplorerScreen";

const menuItems = [
  // { id: "home", label: "Home", icon: Home },
  // { id: "data-sources", label: "Data Sources", icon: Database },
  { id: "pipelines", label: "Agent Pipeline", icon: GitBranch },
  { id: "customer-insights", label: "Insights and Predictions", icon: Users },
  { id: "data-explorer", label: "Data Explorer", icon: Table2 },
  // { id: "inventory-sales", label: "Inventory & Sales", icon: Package },
  { id: "llm-assistant", label: "LLM Assistant", icon: MessageSquare },
  // { id: "reports", label: "Reports", icon: FileText },
  { id: "settings", label: "Settings", icon: Settings },
];

export default function App() {
  const [activeSection, setActiveSection] = useState("home");

  const renderContent = () => {
    switch (activeSection) {
      // case "home":
      //   return <HomeScreen />;
      case "data-sources":
        return <DataSourcesScreen />;
      case "pipelines":
        return <PipelineScreen />;
      case "customer-insights":
        return <CustomerInsightsScreen />;
      case "data-explorer":
        return <DataExplorerScreen />;
      // case "inventory-sales":
      //   return <InventorySalesScreen />;
      case "llm-assistant":
        return <LLMAssistantScreen />;
      // case "reports":
      //   return <ReportsScreen />;
      case "settings":
        return <SettingsScreen />;
      default:
        return <CustomerInsightsScreen />;
    }
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-slate-50">
        <Sidebar className="border-r bg-white">
          <SidebarContent>
            <div className="px-4 py-6">
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
          <main>{renderContent()}</main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
