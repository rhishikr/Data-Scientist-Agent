import { ChatAssistant } from "../chatAssistant/ChatAssistant";

export function LLMAssistantScreen() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="mb-2">LLM Assistant</h1>
        <p className="text-muted-foreground">
          Full-screen conversational interface with your AI Data Scientist
        </p>
      </div>
      <div className="h-[calc(100vh-12rem)]">
        <ChatAssistant context="general" />
      </div>
    </div>
  );
}
