"use client";

import { useMutation } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, ChevronDown, SendHorizontal, User, Wrench } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Markdown } from "@/components/ai";
import { PageHeader, Segmented } from "@/components/ui";
import { post, type AskResponse } from "@/lib/api";
import { cn } from "@/lib/format";

interface Msg { role: "user" | "assistant"; content: string; meta?: AskResponse }

const SUGGESTIONS = [
  "What if I put ₹1 lakh in Nifty for 5 years?",
  "₹5000 monthly SIP in gold for 10 years",
  "What happened after gold fell 10% from its peak?",
  "Why did silver move this week?",
  "How risky is the SBI Small Cap Fund?",
  "Should I buy gold now?",
];

function ToolTrace({ meta }: { meta: AskResponse }) {
  const [open, setOpen] = useState(false);
  if (!meta.tool_calls.length && !meta.sources.length) return null;
  return (
    <div className="mt-2 text-xs">
      <button onClick={() => setOpen(!open)} className="inline-flex items-center gap-1 text-subtle hover:text-fg">
        <Wrench className="h-3 w-3" /> Show work ({meta.tool_calls.length} tool call{meta.tool_calls.length === 1 ? "" : "s"}{meta.sources.length ? `, ${meta.sources.length} sources` : ""})
        <ChevronDown className={cn("h-3 w-3 transition-transform", open && "rotate-180")} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="mt-2 space-y-1 rounded-xl bg-muted p-3 font-mono">
              {meta.tool_calls.map((t, i) => <p key={i} className={t.error ? "text-down" : ""}>→ {t.name}({JSON.stringify(t.input)})</p>)}
              {meta.sources.map((s, i) => (
                <p key={s.link} className="font-sans">[{i + 1}] <a className="text-brand underline" href={s.link} target="_blank" rel="noopener noreferrer">{s.title}</a> — {s.source}</p>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <p className="mt-1 text-[10px] uppercase tracking-wider text-subtle">{meta.mode === "llm" ? "Claude + WealthLens tools" : "Offline mode (rule-based)"}{meta.cached ? " · cached" : ""}{meta.category !== "ok" ? ` · guardrail: ${meta.category}` : ""}</p>
    </div>
  );
}

export default function Ask() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [lang, setLang] = useState<"en" | "hi">("en");
  const end = useRef<HTMLDivElement>(null);
  const ask = useMutation({
    mutationFn: (question: string) =>
      post<AskResponse>("/ai/ask", { question, lang, history: msgs.slice(-6).map(({ role, content }) => ({ role, content: content.slice(0, 3900) })) }),
    onSuccess: (r) => setMsgs((m) => [...m, { role: "assistant", content: r.answer, meta: r }]),
    onError: (e) => setMsgs((m) => [...m, { role: "assistant", content: `Sorry — ${(e as Error).message}` }]),
  });
  useEffect(() => {
    // braces matter: newer browsers return a Promise from scrollIntoView, which React would treat as a cleanup fn
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [msgs, ask.isPending]);

  const send = (text: string) => {
    const t = text.trim();
    if (!t || ask.isPending) return;
    setMsgs((m) => [...m, { role: "user", content: t }]);
    setInput("");
    ask.mutate(t);
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col px-4 py-10">
      <PageHeader eyebrow="Ask WealthLens" title="Ask about the data" sub="An AI assistant that looks up WealthLens's own numbers and calculators to answer. It explains history — it won't tell you what to buy or predict prices." />
      <div className="mb-3 flex justify-end"><Segmented value={lang} onChange={setLang} options={[{ value: "en", label: "English" }, { value: "hi", label: "हिंदी" }]} /></div>
      <div className="card min-h-[420px] flex-1 space-y-5 p-4 sm:p-6">
        {!msgs.length && (
          <div className="grid gap-2 sm:grid-cols-2">
            {SUGGESTIONS.map((s, i) => (
              <motion.button key={s} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                onClick={() => send(s)} className="rounded-xl border border-border p-3 text-left text-sm hover:border-brand hover:bg-brand-soft">{s}</motion.button>
            ))}
          </div>
        )}
        <AnimatePresence initial={false}>
          {msgs.map((m, i) => (
            <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={cn("flex gap-3", m.role === "user" && "flex-row-reverse")}>
              <span className={cn("grid h-8 w-8 shrink-0 place-items-center rounded-xl", m.role === "user" ? "bg-muted" : "bg-gradient-to-br from-brand to-gold text-slate-900")}>
                {m.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </span>
              <div className={cn("max-w-[85%] rounded-2xl px-4 py-3", m.role === "user" ? "bg-brand text-white dark:text-slate-900" : "bg-muted/60")}>
                {m.role === "user" ? <p className="text-sm">{m.content}</p> : <Markdown>{m.content}</Markdown>}
                {m.meta && <ToolTrace meta={m.meta} />}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        {ask.isPending && (
          <div className="flex gap-3">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-brand to-gold text-slate-900"><Bot className="h-4 w-4" /></span>
            <div className="flex items-center gap-1 rounded-2xl bg-muted/60 px-4">
              {[0, 1, 2].map((i) => <motion.span key={i} className="h-2 w-2 rounded-full bg-subtle" animate={{ y: [0, -5, 0] }} transition={{ repeat: Infinity, duration: 0.8, delay: i * 0.15 }} />)}
            </div>
          </div>
        )}
        <div ref={end} />
      </div>
      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="sticky bottom-4 mt-4 flex gap-2 rounded-2xl border border-border bg-card p-2 shadow-xl">
        <input value={input} onChange={(e) => setInput(e.target.value)} maxLength={600} placeholder="e.g. What if I invested ₹10,000 a month in Nifty for 15 years?"
          className="flex-1 bg-transparent px-3 text-sm outline-none" />
        <button disabled={!input.trim() || ask.isPending} className="grid h-10 w-10 place-items-center rounded-xl bg-brand text-white disabled:opacity-40 dark:text-slate-900" aria-label="Send">
          <SendHorizontal className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
