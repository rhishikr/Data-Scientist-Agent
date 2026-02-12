import { useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Send, Sparkles, TrendingUp } from "lucide-react";

interface Message {
  id: number;
  text: string;
  sender: "user" | "ai";
  timestamp: Date;
  hasChart?: boolean;
}

interface ChatAssistantProps {
  context?: string;
}

/**
 * Matches your FastAPI /query response_model (QueryResponse)
 */
type QueryResponse = {
  answer: string;
  query_type: string;
  success: boolean;
  timestamp: string;
  sources?: any[] | null;
  data_summary?: string | null;
};

type QueryRequest = {
  question: string;
  session_id?: string | null;
  include_sources?: boolean;
};

export function ChatAssistant({ context = "general" }: ChatAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: "Hi! I'm your AI Data Scientist. Ask me anything about your analytics, and I'll provide insights based on the current data.",
      sender: "ai",
      timestamp: new Date(),
    },
  ]);

  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Keep a stable session id for the tab/session so the backend can preserve memory
  const sessionId = useMemo(() => {
    const key = "rag_session_id";
    const existing = window.localStorage.getItem(key);
    if (existing) return existing;
    const fresh = `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    window.localStorage.setItem(key, fresh);
    return fresh;
  }, []);

  const API_URL = "http://127.0.0.1:8002/query"; // <-- make sure this matches your FastAPI port

  const getContextPrompts = () => {
    switch (context) {
      case "customer-insights":
        return [
          "Which customers are likely to churn?",
          "What's driving customer retention?",
          "Show me high-value segments",
        ];
      case "inventory-sales":
        return [
          "What should we restock next week?",
          "Why did sales drop last month?",
          "Which products are trending?",
        ];
      default:
        return [
          "What actions should I take this week?",
          "Show me key insights",
          "What's my biggest risk?",
        ];
    }
  };

  const handleSend = async (text?: string) => {
    const messageText = (text ?? inputValue).trim();
    if (!messageText || isLoading) return;

    const userMessage: Message = {
      id: Date.now(),
      text: messageText,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      const payload: QueryRequest = {
        question: messageText,
        session_id: sessionId,
        include_sources: true,
      };

      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      // If backend returns an error, show exactly what backend returned (no hardcoded explanation).
      if (!res.ok) {
        const contentType = res.headers.get("content-type") || "";
        const errPayload = contentType.includes("application/json")
          ? await res.json().catch(() => null)
          : await res.text().catch(() => "");

        const backendMsg =
          (typeof errPayload === "string" && errPayload) ||
          errPayload?.detail ||
          errPayload?.error ||
          "";

        throw new Error(backendMsg || `HTTP ${res.status}`);
      }

      const data = (await res.json()) as QueryResponse;

      const aiMessage: Message = {
        id: Date.now() + 1,
        text: data?.answer ?? "",
        sender: "ai",
        timestamp: new Date(),
        // If you later return structured chart info from backend, wire it here.
        hasChart: Boolean(data?.data_summary),
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (err: any) {
      // For network-level errors, there is no backend message available.
      const aiError: Message = {
        id: Date.now() + 2,
        sender: "ai",
        timestamp: new Date(),
        text: err?.message || "Network error",
      };

      setMessages((prev) => [...prev, aiError]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="flex flex-col h-[calc(100vh-8rem)]">
      <CardHeader className="border-b">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-teal-500 to-blue-600">
            <Sparkles className="size-4 text-white" />
          </div>
          <div>
            <CardTitle className="text-base">AI Data Scientist</CardTitle>
            <CardDescription className="text-xs">
              {isLoading ? "Thinking..." : "Ask me anything"}
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-4 space-y-4">
        {/* Context Tags */}
        <div className="flex flex-wrap gap-2 pb-2 border-b">
          <Badge variant="outline" className="text-xs">
            {context === "customer-insights"
              ? "Customer Data"
              : context === "inventory-sales"
                ? "Inventory Data"
                : "All Data"}
          </Badge>
          <Badge variant="outline" className="text-xs">
            Last 30 days
          </Badge>
        </div>

        {/* Quick Prompts */}
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {getContextPrompts().map((prompt, index) => (
              <button
                key={index}
                onClick={() => handleSend(prompt)}
                disabled={isLoading}
                className="text-xs px-3 py-1.5 rounded-full border border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100 transition-colors disabled:opacity-60"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex items-start gap-2 ${
                message.sender === "user" ? "flex-row-reverse" : ""
              }`}
            >
              <div
                className={`flex size-7 shrink-0 items-center justify-center rounded-lg ${
                  message.sender === "user"
                    ? "bg-slate-700"
                    : "bg-gradient-to-br from-teal-500 to-blue-600"
                }`}
              >
                {message.sender === "user" ? (
                  <span className="text-xs text-white">You</span>
                ) : (
                  <Sparkles className="size-3.5 text-white" />
                )}
              </div>

              <div className="flex-1 space-y-2">
                <div
                  className={`rounded-lg px-3 py-2 ${
                    message.sender === "user"
                      ? "bg-slate-700 text-white ml-4"
                      : "bg-slate-100 mr-4"
                  }`}
                >
                  <p className="text-sm whitespace-pre-line">{message.text}</p>
                </div>

                {/* {message.hasChart && message.sender === "ai" && (
                  <div className="mr-4 rounded-lg border bg-white p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="size-4 text-teal-600" />
                      <p className="text-xs">Related Chart</p>
                    </div>
                    <div className="h-24 bg-gradient-to-r from-teal-50 to-blue-50 rounded flex items-center justify-center">
                      <p className="text-xs text-muted-foreground">
                        Chart visualization
                      </p>
                    </div>
                  </div>
                )} */}
              </div>
            </div>
          ))}
        </div>

        {/* Input */}
        <div className="flex gap-2 pt-2 border-t">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder={
              isLoading ? "Waiting for response..." : "Ask a question..."
            }
            className="text-sm"
            disabled={isLoading}
          />
          <Button
            onClick={() => handleSend()}
            size="icon"
            className="shrink-0 bg-teal-600 hover:bg-teal-700"
            disabled={isLoading}
          >
            <Send className="size-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
