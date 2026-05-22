'use client'

import { useState } from "react";

type Source = { title: string; url: string; summary: string };
type ResearchResponse = {
  topic: string;
  report: string;
  sources: Source[];
  key_points_count: number;
};

export default function Home() {
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120_000);

    try {
      const res = await fetch("https://web-production-e01f8.up.railway.app/research/full", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic.trim() }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        if (res.status >= 500) {
          throw new Error("حدث خطأ في الخادم: " + (data.detail || res.statusText || res.status));
        }
        throw new Error(data.detail || `HTTP ${res.status}`);
      }

      const data: ResearchResponse = await res.json();
      setResult(data);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        setError("استغرق الطلب وقتاً طويلاً. حاول مجدداً");
      } else if (err instanceof TypeError) {
        setError("تعذّر الاتصال بالخادم. تأكد من تشغيل الـbackend");
      } else {
        setError(err instanceof Error ? err.message : "حدث خطأ غير متوقع");
      }
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
    }
  }

  return (
    <main dir="rtl" lang="ar" className="flex flex-1 w-full max-w-3xl mx-auto flex-col gap-8 px-6 py-12">
      <div>
        <h1 className="text-3xl font-semibold text-zinc-900">مساعد البحث الذكي</h1>
        <p className="mt-2 text-zinc-500 text-sm">أدخل موضوعاً وسيقوم النظام بالبحث وكتابة تقرير شامل</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <label htmlFor="topic" className="text-sm font-medium text-zinc-700">
          موضوع البحث
        </label>
        <input
          id="topic"
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          disabled={loading}
          placeholder="مثال: الذكاء الاصطناعي في التعليم"
          className="w-full rounded-lg border border-zinc-300 px-4 py-2 text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-zinc-100 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={loading || !topic.trim()}
          className="self-start rounded-lg bg-blue-600 px-6 py-2 text-white font-medium hover:bg-blue-700 disabled:bg-zinc-400 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "جارٍ البحث..." : "ابحث"}
        </button>
      </form>

      {loading && (
        <p className="text-sm text-zinc-500">جارٍ البحث... قد يستغرق دقيقة أو أكثر</p>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 text-sm">
          {error}
        </div>
      )}

      {result && (
        <>
          <section className="flex flex-col gap-3">
            <h2 className="text-xl font-semibold text-zinc-900">التقرير</h2>
            <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm whitespace-pre-wrap leading-7 text-zinc-800 text-sm">
              {result.report}
            </div>
          </section>

          <section className="flex flex-col gap-3">
            <h2 className="text-xl font-semibold text-zinc-900">المصادر</h2>
            {result.sources.length === 0 ? (
              <p className="text-zinc-500 text-sm">لا توجد مصادر متاحة.</p>
            ) : (
              <ul className="flex flex-col gap-3">
                {result.sources.map((source, i) => (
                  <li key={i} className="rounded-lg border border-zinc-200 bg-white p-4 hover:bg-zinc-50 transition-colors">
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-blue-700 hover:underline"
                    >
                      {source.title}
                    </a>
                    <p className="mt-1 text-sm text-zinc-600">{source.summary}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </main>
  );
}
