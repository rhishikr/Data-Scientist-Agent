import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Send, Sparkles, TrendingUp, AlertCircle } from "lucide-react";

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

  const handleSend = (text?: string) => {
    const messageText = text || inputValue;
    if (!messageText.trim()) return;

    const userMessage: Message = {
      id: messages.length + 1,
      text: messageText,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages([...messages, userMessage]);
    setInputValue("");

    // Simulate AI response
    setTimeout(() => {
      let responseText = "";
      let hasChart = false;

      if (context === "customer-insights") {
        if (messageText.toLowerCase().includes("churn")) {
          responseText = "Based on the current analysis, 234 customers show high churn probability (>70%). Key indicators:\n\n• 62+ days since last purchase\n• Purchase frequency dropped by 40%\n• Low engagement with recent campaigns\n\nRecommended action: Launch targeted re-engagement campaign with personalized offers for the at-risk segment.";
        } else if (messageText.toLowerCase().includes("retention")) {
          responseText = "Your retention rate is 87.3%, which is strong. Top factors driving retention:\n\n• Personalized product recommendations (+15% engagement)\n• Fast shipping (2-day delivery)\n• Loyalty program participation\n\nThe 'Top Buyer' segment shows 94% retention vs 78% for 'At-Risk' customers.";
        } else if (messageText.toLowerCase().includes("segment")) {
          responseText = "High-value segments identified:\n\n• **Top Buyers** (1,247 customers): $24K+ average value, purchase 40+ times/year\n• **Weekend Browsers** (892 customers): 3.2x higher conversion with evening promotions\n\nConsider creating targeted campaigns for these segments.";
          hasChart = true;
        }
      } else if (context === "inventory-sales") {
        if (messageText.toLowerCase().includes("restock")) {
          responseText = "Priority restock recommendations for next 7 days:\n\n**High Priority (3 SKUs)**\n• Wireless Headphones Pro - 2-3 days to stock-out\n• Smart Watch Series 5 - 2 days to stock-out\n• Designer Sunglasses - 3 days to stock-out\n\n**Medium Priority (5 SKUs)**\nCheck the inventory table for details. Estimated reorder cost: $47K";
        } else if (messageText.toLowerCase().includes("sales drop")) {
          responseText = "Sales decreased by 8.2% last month. Key factors:\n\n• Seasonal trend (historically lower in Feb)\n• Out-of-stock for 2 top SKUs (12 days)\n• Competitor promotion (-15% average)\n\nForecast shows recovery in the next 2 weeks with restocking and planned promotions.";
        } else if (messageText.toLowerCase().includes("trend")) {
          responseText = "Top trending products (30-day growth):\n\n1. Wireless Headphones Pro (+127%)\n2. Yoga Mat Premium (+89%)\n3. Smart Watch Series 5 (+76%)\n\nElectronics category shows strongest momentum overall (+45% vs last month).";
          hasChart = true;
        }
      }

      if (!responseText) {
        responseText = "I've analyzed your data and found several key insights. Based on the current metrics, I recommend focusing on the high-priority items highlighted in the dashboard. Would you like me to explain any specific metric in detail?";
      }

      const aiMessage: Message = {
        id: messages.length + 2,
        text: responseText,
        sender: "ai",
        timestamp: new Date(),
        hasChart,
      };
      setMessages((prev) => [...prev, aiMessage]);
    }, 1000);
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
            <CardDescription className="text-xs">Ask me anything</CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-4 space-y-4">
        {/* Context Tags */}
        <div className="flex flex-wrap gap-2 pb-2 border-b">
          <Badge variant="outline" className="text-xs">
            {context === "customer-insights" ? "Customer Data" :
             context === "inventory-sales" ? "Inventory Data" :
             "All Data"}
          </Badge>
          <Badge variant="outline" className="text-xs">Last 30 days</Badge>
        </div>

        {/* Quick Prompts */}
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">Try asking:</p>
          <div className="flex flex-wrap gap-2">
            {getContextPrompts().map((prompt, index) => (
              <button
                key={index}
                onClick={() => handleSend(prompt)}
                className="text-xs px-3 py-1.5 rounded-full border border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100 transition-colors"
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
                {message.hasChart && message.sender === "ai" && (
                  <div className="mr-4 rounded-lg border bg-white p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp className="size-4 text-teal-600" />
                      <p className="text-xs">Related Chart</p>
                    </div>
                    <div className="h-24 bg-gradient-to-r from-teal-50 to-blue-50 rounded flex items-center justify-center">
                      <p className="text-xs text-muted-foreground">Chart visualization</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input */}
        <div className="flex gap-2 pt-2 border-t">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask a question..."
            className="text-sm"
          />
          <Button onClick={() => handleSend()} size="icon" className="shrink-0 bg-teal-600 hover:bg-teal-700">
            <Send className="size-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
