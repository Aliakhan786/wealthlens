"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Button, Card, ErrorBox, PageHeader, Skeleton } from "@/components/ui";
import { api, post, type QuizQuestion, type QuizResult } from "@/lib/api";
import { cn } from "@/lib/format";

const COLORS = ["rgb(var(--subtle))", "rgb(var(--gold))", "rgb(var(--brand))", "#8b5cf6", "#f43f5e"];

export default function Quiz() {
  const qs = useQuery({ queryKey: ["quiz"], queryFn: () => api<QuizQuestion[]>("/quiz/questions") });
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const score = useMutation({ mutationFn: (a: Record<string, number>) => post<QuizResult>("/quiz/risk-profile", { answers: a }) });

  if (qs.error) return <div className="mx-auto max-w-2xl px-4 py-10"><ErrorBox error={qs.error} /></div>;
  const questions = qs.data ?? [];
  const q = questions[step];

  const choose = (idx: number) => {
    const next = { ...answers, [q.id]: idx };
    setAnswers(next);
    if (step + 1 < questions.length) setTimeout(() => setStep(step + 1), 180);
    else score.mutate(next);
  };
  const reset = () => { setStep(0); setAnswers({}); score.reset(); };
  const r = score.data;

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <PageHeader eyebrow="Risk quiz" title="How much ups and downs can you handle?" sub="Six quick questions. You'll get an educational example of how people with similar answers often think about mixing assets." />
      {!questions.length ? <Skeleton className="h-80" /> : r ? (
        <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}>
          <Card>
            <p className="text-sm text-subtle">Your profile</p>
            <h2 className="text-3xl font-extrabold text-gradient">{r.profile}</h2>
            <p className="text-xs text-subtle">Score {r.score}/{r.max_score}{r.capped ? " · capped because of a short horizon or no emergency fund" : ""}</p>
            <div className="mt-4 grid items-center gap-4 sm:grid-cols-2">
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={r.mix} dataKey="pct" nameKey="bucket" innerRadius={60} outerRadius={100} paddingAngle={3} animationDuration={1000} stroke="none">
                    {r.mix.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v: number, n: string) => [`${v}%`, n]} contentStyle={{ background: "rgb(var(--card))", border: "1px solid rgb(var(--border))", borderRadius: 12, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
              <ul className="space-y-2">
                {r.mix.map((m, i) => (
                  <motion.li key={m.bucket} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 + i * 0.1 }} className="text-sm">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-2"><span className="h-3 w-3 rounded" style={{ background: COLORS[i % COLORS.length] }} />{m.bucket}</span>
                      <b className="num">{m.pct}%</b>
                    </div>
                    {m.examples.length > 0 && (
                      <p className="ml-5 text-xs text-subtle">Explore: {m.examples.map((e, j) => <span key={e}>{j ? ", " : ""}<Link className="text-brand" href={`/asset/${e}`}>{e}</Link></span>)}</p>
                    )}
                  </motion.li>
                ))}
              </ul>
            </div>
            <p className="mt-4 rounded-xl bg-gold/10 p-3 text-xs text-gold">{r.note}</p>
            <Button variant="outline" onClick={reset} className="mt-4"><RotateCcw className="h-4 w-4" /> Retake</Button>
          </Card>
        </motion.div>
      ) : (
        <>
          <div className="mb-4 h-2 overflow-hidden rounded-full bg-muted">
            <motion.div className="h-full bg-gradient-to-r from-brand to-gold" animate={{ width: `${(step / questions.length) * 100}%` }} />
          </div>
          <AnimatePresence mode="wait">
            <motion.div key={q.id} initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -40 }} transition={{ type: "spring", stiffness: 300, damping: 30 }}>
              <Card>
                <p className="text-xs font-semibold text-subtle">Question {step + 1} of {questions.length}</p>
                <h2 className="mt-1 text-xl font-bold">{q.text}</h2>
                <div className="mt-5 grid gap-2">
                  {q.options.map((o, i) => (
                    <motion.button key={o.label} whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.98 }} onClick={() => choose(i)}
                      className={cn("rounded-xl border border-border px-4 py-3 text-left text-sm font-medium transition-colors hover:border-brand hover:bg-brand-soft", answers[q.id] === i && "border-brand bg-brand-soft")}>
                      {o.label}
                    </motion.button>
                  ))}
                </div>
                {step > 0 && <button onClick={() => setStep(step - 1)} className="mt-4 inline-flex items-center gap-1 text-sm text-subtle hover:text-fg"><ArrowLeft className="h-4 w-4" /> Back</button>}
              </Card>
            </motion.div>
          </AnimatePresence>
          {score.isPending && <p className="mt-4 text-center text-sm text-subtle">Scoring…</p>}
        </>
      )}
    </div>
  );
}
