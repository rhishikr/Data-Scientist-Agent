import { useState, useEffect, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Tooltip, TooltipTrigger, TooltipContent } from "../ui/tooltip";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "../ui/collapsible";
import {
  Send,
  Sparkles,
  Copy,
  Check,
  Plus,
  ChevronDown,
  BookOpen,
  Database,
  Search,
  Zap,
  History,
  Trash2,
  MessageSquare,
  X,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Message {
  id: number;
  text: string;
  sender: "user" | "ai";
  timestamp: Date;
  queryType?: "sql" | "insight" | "hybrid";
  sources?: any[] | null;
  dataSummary?: string | null;
  isError?: boolean;
}

interface ChatAssistantProps {
  context?: string;
}

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

interface SessionInfo {
  session_id: string;
  message_count: number;
  last_active: string | null;
  preview: string;
}

// ---------------------------------------------------------------------------
// Markdown custom components (avoids @tailwindcss/typography dependency)
// ---------------------------------------------------------------------------

const markdownComponents = {
  h1: ({ children, ...props }: any) => (
    <h1 className="text-base font-bold mt-4 mb-2" {...props}>{children}</h1>
  ),
  h2: ({ children, ...props }: any) => (
    <h2 className="text-sm font-semibold mt-3 mb-1.5" {...props}>{children}</h2>
  ),
  h3: ({ children, ...props }: any) => (
    <h3 className="text-sm font-medium mt-2 mb-1" {...props}>{children}</h3>
  ),
  p: ({ children, ...props }: any) => (
    <p className="text-sm leading-relaxed my-1.5" {...props}>{children}</p>
  ),
  ul: ({ children, ...props }: any) => (
    <ul className="text-sm list-disc pl-5 my-1.5 space-y-0.5" {...props}>{children}</ul>
  ),
  ol: ({ children, ...props }: any) => (
    <ol className="text-sm list-decimal pl-5 my-1.5 space-y-0.5" {...props}>{children}</ol>
  ),
  li: ({ children, ...props }: any) => (
    <li className="text-sm" {...props}>{children}</li>
  ),
  code: ({ children, className, ...props }: any) => {
    const isBlock = className?.startsWith("language-");
    if (isBlock) {
      return (
        <pre className="bg-slate-800 text-slate-100 rounded-lg p-3 text-xs overflow-x-auto my-2 font-mono">
          <code {...props}>{children}</code>
        </pre>
      );
    }
    return (
      <code className="text-xs bg-slate-200 px-1.5 py-0.5 rounded font-mono" {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children, ...props }: any) => {
    // If children is already a styled <pre> from the code handler, just pass through
    return <>{children}</>;
  },
  table: ({ children, ...props }: any) => (
    <div className="overflow-x-auto my-2">
      <table className="text-xs border-collapse w-full" {...props}>{children}</table>
    </div>
  ),
  th: ({ children, ...props }: any) => (
    <th className="border border-slate-300 bg-slate-50 px-3 py-1.5 text-left font-medium" {...props}>
      {children}
    </th>
  ),
  td: ({ children, ...props }: any) => (
    <td className="border border-slate-200 px-3 py-1.5" {...props}>{children}</td>
  ),
  strong: ({ children, ...props }: any) => (
    <strong className="font-semibold" {...props}>{children}</strong>
  ),
  a: ({ children, href, ...props }: any) => (
    <a
      href={href}
      className="text-teal-600 underline hover:text-teal-700"
      target="_blank"
      rel="noopener noreferrer"
      {...props}
    >
      {children}
    </a>
  ),
  blockquote: ({ children, ...props }: any) => (
    <blockquote className="border-l-2 border-teal-300 pl-3 my-2 text-sm text-slate-600 italic" {...props}>
      {children}
    </blockquote>
  ),
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

import { API_BASE, apiFetch } from "../../lib/api";

const STREAM_URL = `${API_BASE}/api/rag/chat/stream`;

const QUERY_TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  sql: { label: "SQL Query", color: "blue" },
  insight: { label: "Insight", color: "teal" },
  hybrid: { label: "Hybrid", color: "purple" },
};

const PROMPT_ICONS = [Search, Database, Zap];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ChatAssistant({ context = "general" }: ChatAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [showSessionPanel, setShowSessionPanel] = useState(false);
  const [sessionList, setSessionList] = useState<SessionInfo[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ---- Session management ----

  const getSessionId = useCallback(() => {
    const key = "rag_session_id";
    const existing = window.localStorage.getItem(key);
    if (existing) return existing;
    const fresh = `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    window.localStorage.setItem(key, fresh);
    return fresh;
  }, []);

  // ---- Load history on mount ----

  useEffect(() => {
    const sessionId = getSessionId();
    apiFetch(
      `${API_BASE}/api/rag/history?session_id=${encodeURIComponent(sessionId)}`,
    )
      .then((res) => res.json())
      .then((data) => {
        if (data.messages && data.messages.length > 0) {
          const restored: Message[] = data.messages.map(
            (msg: any, idx: number) => ({
              id: idx,
              text: msg.content,
              sender: msg.role === "human" ? ("user" as const) : ("ai" as const),
              timestamp: new Date(),
            }),
          );
          setMessages(restored);
        }
      })
      .catch(() => {}) // silently fail — fresh session is fine
      .finally(() => setHistoryLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ---- Auto-scroll ----

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  // ---- Handlers ----

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
          "Show me key insights from the data",
          "What's my biggest business risk?",
        ];
    }
  };

  const handleCopy = useCallback(async (text: string, messageId: number) => {
    await navigator.clipboard.writeText(text);
    setCopiedId(messageId);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

  const handleNewChat = useCallback(() => {
    setMessages([]);
    setInputValue("");
    const fresh = `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    window.localStorage.setItem("rag_session_id", fresh);
    inputRef.current?.focus();
  }, []);

  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const res = await apiFetch(`${API_BASE}/api/rag/sessions`);
      const data = await res.json();
      setSessionList(data.sessions || []);
    } catch {
      setSessionList([]);
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const handleOpenSessions = useCallback(() => {
    setShowSessionPanel(true);
    fetchSessions();
  }, [fetchSessions]);

  const handleSwitchSession = useCallback(async (sessionId: string) => {
    window.localStorage.setItem("rag_session_id", sessionId);
    setShowSessionPanel(false);
    try {
      const res = await apiFetch(
        `${API_BASE}/api/rag/history?session_id=${encodeURIComponent(sessionId)}`,
      );
      const data = await res.json();
      if (data.messages && data.messages.length > 0) {
        const restored: Message[] = data.messages.map(
          (msg: any, idx: number) => ({
            id: idx,
            text: msg.content,
            sender: msg.role === "human" ? ("user" as const) : ("ai" as const),
            timestamp: new Date(),
          }),
        );
        setMessages(restored);
      } else {
        setMessages([]);
      }
    } catch {
      setMessages([]);
    }
  }, []);

  const handleDeleteSession = useCallback(async (sessionId: string) => {
    try {
      await apiFetch(`${API_BASE}/api/rag/sessions/${encodeURIComponent(sessionId)}`, {
        method: "DELETE",
      });
      setSessionList((prev) => prev.filter((s) => s.session_id !== sessionId));
      // If deleted session is the active one, start a new chat
      const currentSessionId = window.localStorage.getItem("rag_session_id");
      if (currentSessionId === sessionId) {
        handleNewChat();
      }
    } catch {
      // silently fail
    }
  }, [handleNewChat]);

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

    // Create empty AI message placeholder for streaming
    const aiId = Date.now() + 1;
    setMessages((prev) => [
      ...prev,
      { id: aiId, text: "", sender: "ai" as const, timestamp: new Date() },
    ]);

    try {
      const res = await apiFetch(STREAM_URL, {
        method: "POST",
        body: JSON.stringify({
          question: messageText,
          session_id: getSessionId(),
          include_sources: true,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          let data: any;
          try {
            data = JSON.parse(part.slice(6));
          } catch {
            continue;
          }

          if (data.event === "start") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiId ? { ...m, queryType: data.query_type } : m,
              ),
            );
          } else if (data.event === "chunk") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiId ? { ...m, text: m.text + data.content } : m,
              ),
            );
          } else if (data.event === "sources") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiId ? { ...m, sources: data.sources } : m,
              ),
            );
          } else if (data.event === "error") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === aiId
                  ? { ...m, text: data.message || "An error occurred", isError: true }
                  : m,
              ),
            );
          }
        }
      }
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiId
            ? {
                ...m,
                text: err?.message || "Network error — is the backend running?",
                isError: true,
              }
            : m,
        ),
      );
    } finally {
      setIsLoading(false);
    }
  };

  // ---- Derived ----

  const hasMessages = messages.length > 0;

  // ---- Render helpers ----

  const formatTime = (d: Date) =>
    d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const formatRelativeTime = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `${days}d ago`;
    return new Date(iso).toLocaleDateString();
  };

  // ---- JSX ----

  return (
    <div className="relative flex flex-col h-full bg-white">
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-6 py-3 border-b shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-linear-to-br from-teal-500 to-blue-600">
            <Sparkles className="size-4 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-semibold">AI Data Scientist</h2>
            <p className="text-xs text-muted-foreground">
              {isLoading ? "Analyzing your question..." : "Ask me anything about your data"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                onClick={handleOpenSessions}
                className="size-8"
              >
                <History className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Chat history</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                onClick={handleNewChat}
                className="size-8"
              >
                <Plus className="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>New conversation</TooltipContent>
          </Tooltip>
        </div>
      </div>

      {/* ── Session history panel ── */}
      <div
        className="absolute inset-0 z-50 flex justify-end"
        style={{
          visibility: showSessionPanel ? "visible" : "hidden",
          transition: "visibility 0s linear " + (showSessionPanel ? "0s" : "300ms"),
        }}
      >
        {/* Backdrop */}
        <div
          onClick={() => setShowSessionPanel(false)}
          style={{
            position: "absolute",
            inset: 0,
            backgroundColor: showSessionPanel ? "rgba(0,0,0,0.2)" : "rgba(0,0,0,0)",
            transition: "background-color 300ms ease",
          }}
        />
        {/* Panel */}
        <div
          className="relative w-80 max-w-[85%] bg-white border-l shadow-lg flex flex-col"
          style={{
            transform: showSessionPanel ? "translateX(0)" : "translateX(100%)",
            transition: "transform 300ms cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        >
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <h3 className="text-sm font-semibold">Chat History</h3>
              <button
                type="button"
                title="Close panel"
                onClick={() => setShowSessionPanel(false)}
                className="p-1 rounded-md hover:bg-slate-100 transition-colors"
              >
                <X className="size-4 text-muted-foreground" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto">
              {sessionsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="flex items-center gap-1.5">
                    <span className="size-2 rounded-full bg-teal-400 animate-bounce" />
                    <span className="size-2 rounded-full bg-teal-400 animate-bounce [animation-delay:150ms]" />
                    <span className="size-2 rounded-full bg-teal-400 animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              ) : sessionList.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                  <MessageSquare className="size-8 text-slate-300 mb-3" />
                  <p className="text-sm text-muted-foreground">No previous sessions</p>
                  <p className="text-xs text-muted-foreground mt-1">Start a conversation to see it here</p>
                </div>
              ) : (
                <div className="py-2">
                  {sessionList.map((session) => {
                    const isActive =
                      window.localStorage.getItem("rag_session_id") === session.session_id;
                    return (
                      <div
                        key={session.session_id}
                        className={`group flex items-start gap-3 px-4 py-3 cursor-pointer hover:bg-slate-50 transition-colors ${
                          isActive ? "bg-teal-50 border-l-2 border-teal-500" : ""
                        }`}
                        onClick={() => handleSwitchSession(session.session_id)}
                      >
                        <MessageSquare className="size-4 text-slate-400 mt-0.5 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-700 truncate">
                            {session.preview || "New conversation"}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[11px] text-muted-foreground">
                              {session.message_count} messages
                            </span>
                            {session.last_active && (
                              <span className="text-[11px] text-muted-foreground">
                                {formatRelativeTime(session.last_active)}
                              </span>
                            )}
                          </div>
                        </div>
                        <button
                          type="button"
                          title="Delete session"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteSession(session.session_id);
                          }}
                          className="p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-50 hover:text-red-600 transition-all text-slate-400"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

      {/* ── Main area ── */}
      {historyLoading ? (
        /* ── Loading state ── */
        <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
          <div className="flex size-10 items-center justify-center rounded-full bg-teal-100 mb-4 animate-pulse">
            <Sparkles className="size-5 text-teal-600" />
          </div>
          <p className="text-sm text-muted-foreground">Loading conversation...</p>
        </div>
      ) : !hasMessages ? (
        /* ── Welcome state ── */
        <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
          <div className="flex size-16 items-center justify-center rounded-2xl bg-linear-to-br from-teal-500 to-blue-600 mb-6">
            <Sparkles className="size-7 text-white" />
          </div>
          <h2 className="text-xl font-semibold mb-2">
            How can I help you today?
          </h2>
          <p className="text-sm text-muted-foreground mb-8 text-center max-w-md">
            I can analyze your data, run SQL queries, and surface insights.
            Ask me anything about your business metrics.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-2xl">
            {getContextPrompts().map((prompt, index) => {
              const Icon = PROMPT_ICONS[index % PROMPT_ICONS.length];
              return (
                <button
                  type="button"
                  key={index}
                  onClick={() => handleSend(prompt)}
                  disabled={isLoading}
                  className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 text-left hover:border-teal-300 hover:bg-teal-50/50 transition-all group disabled:opacity-50"
                >
                  <Icon className="size-5 text-teal-600 mt-0.5 shrink-0" />
                  <span className="text-sm text-slate-700 group-hover:text-teal-700">
                    {prompt}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        /* ── Message list ── */
        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-6 py-6 space-y-6">
            {messages.map((message) =>
              message.sender === "user" ? (
                /* ── User bubble ── */
                <div key={message.id} className="flex justify-end">
                  <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-linear-to-br from-teal-600 to-blue-600 px-4 py-2.5 text-white">
                    <p className="text-sm">{message.text}</p>
                    <p className="text-[10px] text-white/60 mt-1 text-right">
                      {formatTime(message.timestamp)}
                    </p>
                  </div>
                </div>
              ) : (
                /* ── AI bubble ── */
                <div key={message.id} className="flex items-start gap-3">
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-linear-to-br from-teal-500 to-blue-600 mt-1">
                    <Sparkles className="size-3.5 text-white" />
                  </div>

                  <div className="flex-1 min-w-0 space-y-2">
                    {/* Meta row */}
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-muted-foreground">
                        {formatTime(message.timestamp)}
                      </span>
                    </div>

                    {/* Content */}
                    <div
                      className={`rounded-2xl rounded-tl-sm px-4 py-3 mr-12 ${
                        message.isError
                          ? "bg-red-50 border border-red-200"
                          : "bg-slate-100"
                      }`}
                    >
                      {message.text ? (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={markdownComponents}
                        >
                          {message.text}
                        </ReactMarkdown>
                      ) : (
                        <div className="flex items-center gap-1.5">
                          <span className="size-2 rounded-full bg-teal-400 animate-bounce" />
                          <span className="size-2 rounded-full bg-teal-400 animate-bounce [animation-delay:150ms]" />
                          <span className="size-2 rounded-full bg-teal-400 animate-bounce [animation-delay:300ms]" />
                        </div>
                      )}
                    </div>

                    {/* Action buttons (only when content exists) */}
                    {message.text && (
                    <div className="flex items-center gap-1 ml-1">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <button
                            type="button"
                            onClick={() =>
                              handleCopy(message.text, message.id)
                            }
                            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded-md hover:bg-slate-100"
                          >
                            {copiedId === message.id ? (
                              <>
                                <Check className="size-3" /> Copied
                              </>
                            ) : (
                              <>
                                <Copy className="size-3" /> Copy
                              </>
                            )}
                          </button>
                        </TooltipTrigger>
                        <TooltipContent>Copy response</TooltipContent>
                      </Tooltip>
                    </div>
                    )}

                    {/* Sources */}
                    {message.sources && message.sources.length > 0 && (
                      <Collapsible>
                        <CollapsibleTrigger className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded-md hover:bg-slate-100">
                          <BookOpen className="size-3" />
                          <span>
                            {message.sources.length} source
                            {message.sources.length > 1 ? "s" : ""}
                          </span>
                          <ChevronDown className="size-3 transition-transform data-[state=open]:rotate-180" />
                        </CollapsibleTrigger>
                        <CollapsibleContent>
                          <div className="mt-2 space-y-1.5 ml-2">
                            {message.sources.map(
                              (source: any, idx: number) => (
                                <div
                                  key={idx}
                                  className="flex items-start gap-2 text-xs p-2 rounded-lg bg-slate-50 border border-slate-200"
                                >
                                  <span className="flex size-5 shrink-0 items-center justify-center rounded bg-teal-100 text-teal-700 text-[10px] font-medium">
                                    {idx + 1}
                                  </span>
                                  <span className="text-slate-600 line-clamp-3">
                                    {typeof source === "string"
                                      ? source
                                      : source?.content ||
                                        source?.text ||
                                        source?.page_content ||
                                        JSON.stringify(source)}
                                  </span>
                                </div>
                              ),
                            )}
                          </div>
                        </CollapsibleContent>
                      </Collapsible>
                    )}
                  </div>
                </div>
              ),
            )}

          </div>
        </div>
      )}

      {/* ── Input bar ── */}
      <div className="border-t bg-white px-6 py-4 shrink-0">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder={
              isLoading
                ? "Waiting for response..."
                : "Ask about your data..."
            }
            className="flex-1 py-5 text-sm rounded-xl border-slate-200 focus-visible:ring-teal-500/30"
            disabled={isLoading}
          />
          <Button
            onClick={() => handleSend()}
            size="icon"
            className="shrink-0 size-10 rounded-xl bg-linear-to-br from-teal-500 to-blue-600 hover:from-teal-600 hover:to-blue-700 disabled:opacity-50"
            disabled={isLoading || !inputValue.trim()}
          >
            <Send className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
