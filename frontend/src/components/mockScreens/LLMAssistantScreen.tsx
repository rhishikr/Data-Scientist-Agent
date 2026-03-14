import { ChatAssistant } from "../chatAssistant/ChatAssistant";

export function LLMAssistantScreen() {
  return (
    <div className="h-screen overflow-hidden">
      <ChatAssistant context="general" />
    </div>
  );
}
