import { ChatAssistant } from "../chatAssistant/ChatAssistant";

export function LLMAssistantScreen() {
  return (
    <div>
      <div className="sticky top-0 z-10 bg-white border-b px-6 py-4">
        <h1 className="text-xl font-semibold">LLM Assistant</h1>
        <p className="text-xs text-muted-foreground">
          Full-screen conversational interface with your AI Data Scientist
        </p>
      </div>
      <div className="p-6 max-w-4xl mx-auto">
        <div className="h-[calc(100vh-12rem)]">
          <ChatAssistant context="general" />
        </div>
      </div>
    </div>
  );
}
