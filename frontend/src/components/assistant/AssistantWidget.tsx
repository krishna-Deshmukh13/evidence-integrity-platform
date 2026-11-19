import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ChatCircleText,
  FileText,
  FilmStrip,
  Image as ImageIcon,
  PaperPlaneRight,
  Sparkle,
  SpeakerHigh,
  Trash,
  X,
  ArrowRight,
  Gear,
  Copy,
  Check,
  Lightning,
  ArrowSquareOut,
  Robot,
} from "@phosphor-icons/react";
import { api } from "@/lib/api";
import type { AssistantCard, AssistantMessage, MediaType, Verdict } from "@/lib/types";
import { cx, ScoreChip, VerdictText } from "@/components/ui";

const MEDIA_ICONS: Record<MediaType, typeof ImageIcon> = {
  image: ImageIcon,
  video: FilmStrip,
  audio: SpeakerHigh,
  document: FileText,
};

// Rich Markdown Parser for ChatGPT-like formatting
function MarkdownBody({ content }: { content: string }) {
  const lines = content.split("\n");

  return (
    <div className="space-y-1.5 text-xs sm:text-sm leading-relaxed">
      {lines.map((line, idx) => {
        const trimmed = line.trim();

        // Empty line
        if (!trimmed) {
          return <div key={idx} className="h-1.5" />;
        }

        // H3 Header: ### Title
        if (trimmed.startsWith("### ")) {
          return (
            <h4 key={idx} className="font-bold text-ink mt-2 mb-1 text-sm flex items-center gap-1.5">
              <span className="size-1.5 rounded-full bg-accent" />
              {renderFormattedText(trimmed.replace(/^###\s+/, ""))}
            </h4>
          );
        }

        // H2 Header: ## Title
        if (trimmed.startsWith("## ")) {
          return (
            <h3 key={idx} className="font-bold text-ink mt-2.5 mb-1 text-sm border-b border-line/60 pb-1">
              {renderFormattedText(trimmed.replace(/^##\s+/, ""))}
            </h3>
          );
        }

        // Bullet point: - Item or * Item
        if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          const itemText = trimmed.replace(/^[-*]\s+/, "");
          return (
            <div key={idx} className="flex items-start gap-2 pl-1.5 py-0.5">
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-accent/70" />
              <div className="flex-1">{renderFormattedText(itemText)}</div>
            </div>
          );
        }

        // Numbered list: 1. Item
        const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
        if (numMatch) {
          return (
            <div key={idx} className="flex items-start gap-2 pl-1.5 py-0.5">
              <span className="shrink-0 font-bold text-accent text-xs mt-0.5">{numMatch[1]}.</span>
              <div className="flex-1">{renderFormattedText(numMatch[2])}</div>
            </div>
          );
        }

        // Regular paragraph
        return <p key={idx}>{renderFormattedText(trimmed)}</p>;
      })}
    </div>
  );
}

// Inline formatting: **bold**, `code`, and links
function renderFormattedText(text: string) {
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);

  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-ink">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="rounded bg-surface px-1.5 py-0.5 font-mono text-[11px] text-accent border border-line"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

export default function AssistantWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initialLoaded, setInitialLoaded] = useState(false);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  // Model Engine Settings State
  const [showSettings, setShowSettings] = useState(false);
  const [llmSettings, setLlmSettings] = useState<any>(null);
  const [selectedProvider, setSelectedProvider] = useState("free_online");
  const [apiKey, setApiKey] = useState("");
  const [customModel, setCustomModel] = useState("");
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const loc = useLocation();
  const nav = useNavigate();
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Extract page context
  const getContext = () => {
    const path = loc.pathname;
    let page = "dashboard";
    let caseId: number | undefined;
    let evidenceId: number | undefined;

    if (path === "/") {
      page = "dashboard";
    } else if (path.startsWith("/cases/")) {
      page = "case";
      const parts = path.split("/");
      const id = parseInt(parts[2], 10);
      if (!isNaN(id)) caseId = id;
    } else if (path.startsWith("/evidence/")) {
      page = "evidence";
      const parts = path.split("/");
      const id = parseInt(parts[2], 10);
      if (!isNaN(id)) evidenceId = id;
    } else if (path.startsWith("/search")) {
      page = "search";
    } else if (path.startsWith("/compare")) {
      page = "compare";
    } else if (path.startsWith("/activity")) {
      page = "activity";
    } else if (path.startsWith("/graph")) {
      page = "graph";
    } else if (path.startsWith("/certificates")) {
      page = "certificates";
    } else if (path.startsWith("/timeline")) {
      page = "timeline";
    } else if (path.startsWith("/settings")) {
      page = "settings";
    }

    return { page, caseId, evidenceId };
  };

  const { page, caseId, evidenceId } = getContext();

  const getPageTitle = () => {
    if (page === "dashboard") return "On: Dashboard";
    if (page === "case") return caseId ? `On: Case #${caseId}` : "On: Case Details";
    if (page === "evidence") return evidenceId ? `On: File #${evidenceId}` : "On: Evidence Details";
    if (page === "search") return "On: Search";
    if (page === "compare") return "On: Compare";
    if (page === "graph") return "On: Intelligence Graph";
    if (page === "certificates") return "On: Custody & Certificates";
    if (page === "timeline") return "On: Evidence Timeline";
    return "On: Platform";
  };

  const getSuggestions = () => {
    if (page === "dashboard") {
      return [
        "How does ELA detect tampering?",
        "Explain Section 63 BSA certificate",
        "Show likely manipulated files",
        "How does deepfake detection work?",
        "Compare SHA-256 vs pHash",
      ];
    }
    if (page === "case") {
      return [
        "Which file should I check first?",
        "Summarise this case",
        "Show likely manipulated files here",
        "Are there timestamp contradictions?",
      ];
    }
    if (page === "evidence") {
      return [
        "Why this score?",
        "Where is the edit located?",
        "What should I do next?",
        "How does clone detection work?",
      ];
    }
    return [
      "What needs my attention?",
      "Show likely manipulated files",
      "Explain Section 63 BSA",
      "What is audio voice cloning?",
    ];
  };

  // Fetch settings on open
  useEffect(() => {
    if (isOpen) {
      api.getLlmSettings?.()
        .then((s) => {
          setLlmSettings(s);
          setSelectedProvider(s.provider || "free_online");
          setCustomModel(s.model || "");
        })
        .catch(() => {});
    }
  }, [isOpen]);

  // Load history when opened
  useEffect(() => {
    if (isOpen && !initialLoaded) {
      api.assistantHistory()
        .then((hist) => {
          setMessages(hist);
          setInitialLoaded(true);
        })
        .catch(() => setInitialLoaded(true));
    }
  }, [isOpen, initialLoaded]);

  // Scroll to bottom on message update
  useEffect(() => {
    if (isOpen) {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading, isOpen]);

  // Global keyboard shortcut 'a' and 'Escape'
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) ||
          target.isContentEditable)
      ) {
        if (e.key === "Escape" && isOpen) {
          e.preventDefault();
          if (showSettings) {
            setShowSettings(false);
          } else {
            setIsOpen(false);
          }
        }
        return;
      }

      if (e.key.toLowerCase() === "a") {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (e.key === "Escape" && isOpen) {
        e.preventDefault();
        if (showSettings) {
          setShowSettings(false);
        } else {
          setIsOpen(false);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, showSettings]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    setInput("");
    const userMsg: AssistantMessage = {
      id: Date.now(),
      role: "user",
      content: query,
      source: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const resp = await api.assistantChat({
        message: query,
        context: {
          page,
          case_id: caseId,
          evidence_id: evidenceId,
        },
      });
      setMessages((prev) => [...prev, resp]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          role: "assistant",
          content:
            "I experienced a brief communication interruption. Please ask your question again, and I will be happy to assist you.",
          source: "error",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleClear = async () => {
    try {
      await api.assistantClear();
      setMessages([]);
    } catch {
      // ignore
    }
  };

  const handleCopy = (id: number, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleTestLlm = async () => {
    setTestingConnection(true);
    setTestResult(null);
    try {
      const res = await api.testLlm();
      setTestResult(res);
    } catch (err: any) {
      setTestResult({ ok: false, error: err.message || "Failed to reach server" });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSaveLlmSettings = async () => {
    setSaveStatus("Saving...");
    try {
      const updated = await api.updateLlmSettings({
        provider: selectedProvider,
        model: customModel || undefined,
        key: apiKey || undefined,
      });
      setLlmSettings(updated);
      setSaveStatus("Saved successfully!");
      setTimeout(() => {
        setSaveStatus(null);
        setShowSettings(false);
      }, 1200);
    } catch (err: any) {
      setSaveStatus("Failed to save settings");
    }
  };

  const getEngineDisplayLabel = () => {
    if (!llmSettings) return "Free Online AI";
    if (llmSettings.provider === "free_online") return "Free Online AI (ChatGPT)";
    if (llmSettings.provider === "gemini") return "Google Gemini 2.0 Flash";
    if (llmSettings.provider === "groq") return "Groq Llama 3.3 70B";
    if (llmSettings.provider === "ollama") return `Ollama (${llmSettings.model || "Local"})`;
    return llmSettings.label || "AI Copilot";
  };

  return (
    <>
      {/* Floating launcher button: Collapsible & repositioned to prevent covering cards */}
      {!isOpen && (
        <div className="fixed bottom-4 right-4 z-40 flex items-center gap-1.5">
          {isMinimized ? (
            <button
              onClick={() => setIsMinimized(false)}
              className="flex items-center gap-1.5 rounded-full border border-line bg-surface/95 px-3 py-1.5 text-xs font-semibold text-ink shadow-md backdrop-blur-sm hover:border-accent hover:text-accent transition-all cursor-pointer"
              title="Expand Forensic Assistant"
            >
              <Sparkle size={14} className="text-accent" weight="fill" />
              <span>Forensic Assistant</span>
            </button>
          ) : (
            <div className="flex items-center gap-1">
              <button
                onClick={() => setIsOpen(true)}
                className="flex items-center gap-2 rounded-full bg-accent px-3.5 py-2 text-xs font-bold text-white shadow-xs hover:shadow-xs transition-all cursor-pointer"
                title="Ask the forensic assistant (A)"
                aria-label="Ask the forensic assistant"
              >
                <ChatCircleText size={17} weight="bold" />
                <span>Forensic Assistant</span>
                <span className="size-2 rounded-full bg-[#12B981] animate-pulse" />
              </button>
              <button
                onClick={() => setIsMinimized(true)}
                className="size-7 rounded-full bg-surface border border-line text-muted hover:text-ink hover:bg-surface2 grid place-items-center transition-all shadow-xs cursor-pointer"
                title="Collapse assistant button"
                aria-label="Collapse assistant button"
              >
                <X size={12} weight="bold" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Backdrop for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/40 sm:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Slide-in Assistant Side Panel */}
      <aside
        className={cx(
          "fixed inset-y-0 right-0 z-50 flex flex-col bg-surface border-l border-line shadow-sm transition-transform duration-300 ease-in-out",
          "w-full sm:w-[420px] md:w-[460px]",
          isOpen ? "translate-x-0" : "translate-x-full pointer-events-none"
        )}
      >
        {/* Panel Header */}
        <header className="flex h-15 shrink-0 items-center justify-between border-b border-line px-4 bg-surface2/50 backdrop-blur-sm">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="relative flex size-9 shrink-0 items-center justify-center rounded-full bg-accent/15 text-accent border border-accent/30 shadow-xs">
              <Sparkle size={18} weight="fill" />
              <span className="absolute -top-0.5 -right-0.5 size-2.5 rounded-full bg-good ring-2 ring-surface animate-pulse" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <h2 className="text-sm font-semibold leading-tight text-ink">Forensic AI Assistant</h2>
              </div>
              <p className="truncate text-[11px] text-muted">{getPageTitle()}</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {/* AI Model Badge / Settings Button */}
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="flex items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-[11px] font-medium text-ink hover:border-accent hover:text-accent transition shadow-2xs"
              title="Configure AI Model / Free Online API"
            >
              <span className="size-1.5 rounded-full bg-good animate-pulse" />
              <span className="max-w-[110px] truncate">{getEngineDisplayLabel()}</span>
              <Gear size={13} className="text-muted" />
            </button>

            <button
              onClick={handleClear}
              className="p-1.5 text-muted hover:text-bad rounded-md hover:bg-surface2 transition"
              title="Clear conversation"
              aria-label="Clear thread"
            >
              <Trash size={16} />
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 text-muted hover:text-ink rounded-md hover:bg-surface2 transition"
              title="Close (Esc)"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>
        </header>

        {/* AI Engine Configuration Drawer / Modal Overlay */}
        {showSettings && (
          <div className="border-b border-line bg-surface2/90 p-4 animate-in slide-in-from-top-2 duration-200">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-1.5">
                <Robot size={18} className="text-accent" />
                <h3 className="text-xs font-bold text-ink">AI Model Engine Setup</h3>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="text-muted hover:text-ink p-1 rounded hover:bg-surface"
              >
                <X size={14} />
              </button>
            </div>

            <p className="text-xs text-muted mb-3">
              Connect to a free online AI endpoint for ChatGPT-like intelligence, or configure your personal API key.
            </p>

            <div className="space-y-3">
              {/* Provider Selection */}
              <div>
                <label className="block text-[11px] font-semibold text-muted mb-1">Active AI Provider</label>
                <select
                  value={selectedProvider}
                  onChange={(e) => {
                    setSelectedProvider(e.target.value);
                    if (e.target.value === "free_online") setCustomModel("openai");
                    if (e.target.value === "gemini") setCustomModel("gemini-2.0-flash");
                    if (e.target.value === "groq") setCustomModel("llama-3.3-70b-versatile");
                  }}
                  className="w-full rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs text-ink outline-none focus:border-accent"
                >
                  <option value="free_online">🌟 Free Online AI (Instant, Zero Key Needed)</option>
                  <option value="gemini">⚡ Google Gemini 2.0 Flash (Free API Key)</option>
                  <option value="groq">🚀 Groq Llama 3.3 70B (Free API Key)</option>
                  <option value="openrouter">🌐 OpenRouter Free Tier</option>
                  <option value="ollama">💻 Local Ollama (Offline localhost:11434)</option>
                  <option value="none">🔒 Local Forensic Knowledge Engine (Rule-based)</option>
                </select>
              </div>

              {/* Free API Key Links */}
              {selectedProvider === "gemini" && (
                <div className="rounded-md bg-accent/10 border border-accent/20 p-2 text-[11px] text-ink flex items-center justify-between">
                  <span>Get a 100% free Google Gemini key (no credit card):</span>
                  <a
                    href="https://aistudio.google.com/app/apikey"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 font-semibold text-accent hover:underline shrink-0"
                  >
                    Google AI Studio <ArrowSquareOut size={12} />
                  </a>
                </div>
              )}

              {selectedProvider === "groq" && (
                <div className="rounded-md bg-accent/10 border border-accent/20 p-2 text-[11px] text-ink flex items-center justify-between">
                  <span>Get a free ultra-fast Groq key:</span>
                  <a
                    href="https://console.groq.com/keys"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 font-semibold text-accent hover:underline shrink-0"
                  >
                    Groq Console <ArrowSquareOut size={12} />
                  </a>
                </div>
              )}

              {/* API Key Input (if not free_online or none) */}
              {selectedProvider !== "free_online" && selectedProvider !== "none" && selectedProvider !== "ollama" && (
                <div>
                  <label className="block text-[11px] font-semibold text-muted mb-1">
                    API Key {selectedProvider === "gemini" ? "(Google AI Studio Key)" : "(API Secret Key)"}
                  </label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Paste key here..."
                    className="w-full rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs text-ink outline-none focus:border-accent font-mono"
                  />
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={handleTestLlm}
                  disabled={testingConnection}
                  className="flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs font-semibold text-ink hover:border-accent hover:text-accent transition disabled:opacity-50"
                >
                  <Lightning size={14} className="text-amber-500" />
                  {testingConnection ? "Pinging..." : "Test Connection"}
                </button>

                <div className="flex items-center gap-2">
                  {saveStatus && <span className="text-[11px] text-good font-medium">{saveStatus}</span>}
                  <button
                    type="button"
                    onClick={handleSaveLlmSettings}
                    className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-white hover:brightness-110 transition shadow-xs"
                  >
                    Save & Apply
                  </button>
                </div>
              </div>

              {/* Test Result Feedback */}
              {testResult && (
                <div
                  className={cx(
                    "rounded-lg p-2.5 text-xs border mt-2",
                    testResult.ok ? "bg-good-soft/40 border-good/40 text-good" : "bg-bad-soft/40 border-bad/40 text-bad"
                  )}
                >
                  <div className="font-semibold flex items-center gap-1.5">
                    {testResult.ok ? "✓ Connection Successful" : "✗ Connection Error"}
                    {testResult.latency_ms > 0 && (
                      <span className="text-[10px] opacity-80">({testResult.latency_ms}ms)</span>
                    )}
                  </div>
                  <div className="mt-1 text-[11px] opacity-90">
                    {testResult.message || testResult.error || testResult.answer}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !loading && (
            <div className="py-8 text-center text-sm text-muted">
              <div className="mx-auto mb-3 flex size-12 items-center justify-center rounded-full bg-accent/10 text-accent border border-accent/20 shadow-xs">
                <Sparkle size={24} weight="fill" />
              </div>
              <h3 className="font-semibold text-ink text-base">Forensic AI Assistant</h3>
              <p className="mt-1 text-xs text-muted max-w-xs mx-auto leading-relaxed">
                Ask any question about digital forensics, evidence integrity scores, image manipulation layers, or legal admissibility under Section 63 BSA.
              </p>
              <div className="mt-4 flex flex-wrap justify-center gap-1.5">
                {getSuggestions().slice(0, 3).map((sugg) => (
                  <button
                    key={sugg}
                    onClick={() => handleSend(sugg)}
                    className="rounded-full border border-line bg-surface px-2.5 py-1 text-[11px] text-muted hover:border-accent hover:text-accent hover:bg-surface2 transition"
                  >
                    "{sugg}"
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => (
            <div
              key={m.id}
              className={cx(
                "group flex flex-col gap-1.5",
                m.role === "user" ? "items-end" : "items-start"
              )}
            >
              <div
                className={cx(
                  "relative rounded-lg px-4 py-3 text-sm leading-relaxed max-w-[94%] shadow-2xs transition-all",
                  m.role === "user"
                    ? "bg-accent text-white rounded-tr-xs"
                    : "bg-surface2/90 text-ink border border-line rounded-tl-xs"
                )}
              >
                {/* Formatted body with Markdown support */}
                {m.role === "user" ? (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                ) : (
                  <MarkdownBody content={m.content} />
                )}

                {/* Structured Result Cards */}
                {m.results && m.results.length > 0 && (
                  <div className="mt-3.5 space-y-2">
                    <div className="text-[11px] font-semibold text-muted">
                      Matched Evidence Files ({m.results.length})
                    </div>
                    {m.results.map((card: AssistantCard) => {
                      const Icon = MEDIA_ICONS[card.media_type] || FileText;
                      return (
                        <div
                          key={card.id}
                          onClick={() => {
                            nav(`/evidence/${card.id}`);
                            if (window.innerWidth < 640) setIsOpen(false);
                          }}
                          className="group/card flex flex-col gap-1.5 rounded-lg border border-line bg-surface p-2.5 hover:border-accent hover:bg-surface2/60 cursor-pointer transition text-ink shadow-2xs"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5 min-w-0">
                              <Icon size={16} className="shrink-0 text-muted group-hover/card:text-accent" />
                              <span className="truncate text-xs font-semibold group-hover/card:text-accent">
                                {card.filename}
                              </span>
                            </div>
                            <ScoreChip score={card.score} />
                          </div>
                          <div className="flex items-center justify-between text-[11px] text-muted">
                            <span className="truncate">{card.case_ref}</span>
                            <div className="flex items-center gap-1">
                              <VerdictText verdict={card.verdict as Verdict} />
                              <ArrowRight size={12} className="opacity-0 group-hover/card:opacity-100 transition text-accent" />
                            </div>
                          </div>
                          {/* Working action buttons */}
                          <div className="pt-1.5 border-t border-line/60 flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                            <button
                              onClick={() => {
                                nav(`/evidence/${card.id}`);
                                if (window.innerWidth < 640) setIsOpen(false);
                              }}
                              className="rounded bg-surface2 px-2 py-0.5 text-[10px] font-semibold text-accent hover:bg-accent/15 transition"
                            >
                              Inspect File
                            </button>
                            <button
                              onClick={() => {
                                nav(`/compare?a=${card.id}`);
                                if (window.innerWidth < 640) setIsOpen(false);
                              }}
                              className="rounded bg-surface2 px-2 py-0.5 text-[10px] font-semibold text-muted hover:text-ink transition"
                            >
                              Compare
                            </button>
                            <a
                              href={api.url.section63Pdf(card.id)}
                              target="_blank"
                              rel="noreferrer"
                              className="rounded bg-surface2 px-2 py-0.5 text-[10px] font-semibold text-good hover:bg-good-soft transition"
                            >
                              Certificate
                            </a>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Provenance footer, copy action, and model source tag */}
              {m.role === "assistant" && (
                <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-[11px] text-muted w-full max-w-[94%]">
                  <div className="flex items-center gap-1.5 truncate">
                    <span className="rounded bg-surface2 px-1.5 py-0.5 text-[10px] font-semibold border border-line text-ink/80 flex items-center gap-1">
                      <Sparkle size={10} className="text-accent" />
                      {m.source || "Forensic AI"}
                    </span>
                    {m.based_on && m.based_on.length > 0 && (
                      <span className="truncate text-[10px] text-muted">
                        • {m.based_on[0]}
                      </span>
                    )}
                  </div>

                  <button
                    onClick={() => handleCopy(m.id, m.content)}
                    className="flex items-center gap-1 text-[10px] text-muted hover:text-ink transition opacity-0 group-hover:opacity-100"
                    title="Copy message to clipboard"
                  >
                    {copiedId === m.id ? (
                      <>
                        <Check size={12} className="text-good" />
                        <span className="text-good">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy size={12} />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          ))}

          {/* ChatGPT-like Animated Typing Bubble */}
          {loading && (
            <div className="flex items-start gap-2 animate-in fade-in duration-200">
              <div className="flex items-center gap-2.5 rounded-lg rounded-tl-xs border border-line bg-surface2 px-4 py-2.5 text-xs text-muted shadow-2xs">
                <div className="flex items-center gap-1">
                  <span className="size-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="size-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="size-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
                <span className="font-medium text-ink">Assistant is thinking...</span>
              </div>
            </div>
          )}

          <div ref={endRef} />
        </div>

        {/* Suggestion Chips */}
        <div className="border-t border-line bg-surface px-3 py-2">
          <div className="flex flex-wrap gap-1.5 max-h-20 overflow-y-auto">
            {getSuggestions().map((sugg) => (
              <button
                key={sugg}
                disabled={loading}
                onClick={() => handleSend(sugg)}
                className="rounded-full border border-line bg-surface2/70 px-2.5 py-1 text-[11px] text-muted hover:border-accent hover:bg-surface2 hover:text-ink disabled:opacity-50 transition shrink-0"
              >
                {sugg}
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar */}
        <div className="border-t border-line p-3 bg-surface">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-end gap-2 rounded-xl border border-line bg-surface2 p-1.5 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/15 transition shadow-2xs"
          >
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ask anything about evidence, scores, legal certificates, or algorithms..."
              className="max-h-28 min-h-[36px] w-full resize-none bg-transparent px-2.5 py-1.5 text-xs sm:text-sm outline-none text-ink placeholder:text-muted"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-white hover:brightness-110 disabled:opacity-40 transition shadow-xs"
              title="Send message (Enter)"
              aria-label="Send"
            >
              <PaperPlaneRight size={16} weight="fill" />
            </button>
          </form>
          <div className="mt-1.5 flex items-center justify-between px-1 text-[10px] text-muted">
            <span>Press Enter to send, Shift+Enter for new line</span>
            <span className="flex items-center gap-1">
              <span className="size-1.5 rounded-full bg-good" />
              Online AI Active
            </span>
          </div>
        </div>
      </aside>
    </>
  );
}
