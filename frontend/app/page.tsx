'use client'

import { useState } from "react";

type Source = { title: string; url: string; summary: string };
type FactCheckResult = {
  confidence_score: number;
  verified_claims: string[];
  questionable_claims: string[];
  notes: string;
};
type ResearchResponse = {
  topic: string;
  report: string;
  sources: Source[];
  key_points_count: number;
  fact_check: FactCheckResult | null;
};
type PdfUploadResponse = {
  doc_id: string;
  filename: string;
  pages: number;
  chunks_count: number;
  preview: string;
  metadata: { title: string | null; author: string | null; file_size_kb: number };
};
type PdfResearchResponse = {
  doc_id: string;
  filename: string;
  question: string;
  report: string;
  key_points: string[];
  contradictions: string[];
  chunks_used: number;
};

const API_BASE = "https://web-production-e01f8.up.railway.app";

function confidenceColor(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function getFavicon(url: string): string | null {
  try {
    const hostname = new URL(url).hostname;
    return `https://www.google.com/s2/favicons?domain=${hostname}&sz=32`;
  } catch {
    return null;
  }
}

function LoadingSkeleton({ label }: { label: string }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3 text-zinc-500">
        <svg
          className="animate-spin h-5 w-5 flex-shrink-0"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        <p className="text-sm">{label}</p>
      </div>
      <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm flex flex-col gap-3">
        <div className="h-4 bg-zinc-200 rounded animate-pulse w-3/4" />
        <div className="h-4 bg-zinc-200 rounded animate-pulse w-full" />
        <div className="h-4 bg-zinc-200 rounded animate-pulse w-5/6" />
        <div className="h-4 bg-zinc-200 rounded animate-pulse w-2/3" />
        <div className="h-4 bg-zinc-200 rounded animate-pulse w-full" />
      </div>
      <div className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm flex flex-col gap-2">
        <div className="h-3 bg-zinc-200 rounded animate-pulse w-1/2" />
        <div className="h-3 bg-zinc-200 rounded animate-pulse w-3/4" />
      </div>
    </div>
  );
}

export default function Home() {
  const [tab, setTab] = useState<"web" | "pdf">("web");

  // --- Web search state ---
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [streamedReport, setStreamedReport] = useState("");

  // --- PDF state ---
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfDocId, setPdfDocId] = useState<string | null>(null);
  const [pdfPreview, setPdfPreview] = useState<string>("");
  const [pdfUploadMeta, setPdfUploadMeta] = useState<PdfUploadResponse | null>(null);
  const [pdfUploading, setPdfUploading] = useState(false);
  const [pdfQuestion, setPdfQuestion] = useState("");
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfResult, setPdfResult] = useState<PdfResearchResponse | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!topic.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120_000);

    try {
      const res = await fetch(`${API_BASE}/research/full`, {
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

  async function handleStreamSubmit() {
    if (!topic.trim() || loading || streaming) return;

    setError(null);
    setResult(null);
    setStreamedReport("");
    setStreaming(true);

    try {
      const res = await fetch(`${API_BASE}/research/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic.trim() }),
      });

      if (!res.ok || !res.body) {
        throw new Error("STREAM_INIT_FAILED");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let accumulated = "";
      let finalSources: Source[] = [];
      let finalFactCheck: FactCheckResult | null = null;
      let finalKeyPoints = 0;
      let sawDone = false;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const evt of parts) {
          const line = evt.trim();
          if (!line.startsWith("data:")) continue;
          const jsonStr = line.replace(/^data:\s*/, "");
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);
            if (data.type === "token") {
              accumulated += data.content;
              setStreamedReport(accumulated);
            } else if (data.type === "done") {
              finalSources = data.sources || [];
              finalFactCheck = data.fact_check || null;
              finalKeyPoints = data.key_points_count || 0;
              sawDone = true;
            } else if (data.type === "error") {
              throw new Error(data.message || "STREAM_ERROR");
            }
          } catch (parseErr) {
            console.warn("SSE parse error", parseErr);
          }
        }
      }

      if (!sawDone) throw new Error("STREAM_INCOMPLETE");

      setResult({
        topic: topic.trim(),
        report: accumulated,
        sources: finalSources,
        key_points_count: finalKeyPoints,
        fact_check: finalFactCheck,
      });
      setStreamedReport("");
    } catch (err) {
      console.warn("Streaming failed, falling back to /research/full:", err);
      setStreaming(false);
      setStreamedReport("");
      await handleSubmit({ preventDefault: () => {} } as React.FormEvent);
      return;
    } finally {
      setStreaming(false);
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!pdfFile) return;

    if (pdfFile.size > 10 * 1024 * 1024) {
      setPdfError("حجم الملف يتجاوز 10 ميغابايت. اختر ملفاً أصغر.");
      return;
    }

    setPdfUploading(true);
    setPdfError(null);
    setPdfDocId(null);
    setPdfUploadMeta(null);
    setPdfResult(null);

    const fd = new FormData();
    fd.append("file", pdfFile);

    try {
      const res = await fetch(`${API_BASE}/pdf/upload`, {
        method: "POST",
        body: fd,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${res.status}`);
      }

      const data: PdfUploadResponse = await res.json();
      setPdfDocId(data.doc_id);
      setPdfPreview(data.preview);
      setPdfUploadMeta(data);
    } catch (err) {
      if (err instanceof TypeError) {
        setPdfError("تعذّر الاتصال بالخادم.");
      } else {
        setPdfError(err instanceof Error ? err.message : "حدث خطأ أثناء رفع الملف");
      }
    } finally {
      setPdfUploading(false);
    }
  }

  async function handleAskPdf(e: React.FormEvent) {
    e.preventDefault();
    if (!pdfDocId || !pdfQuestion.trim()) return;

    setPdfLoading(true);
    setPdfError(null);
    setPdfResult(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120_000);

    try {
      const res = await fetch(`${API_BASE}/pdf/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_id: pdfDocId, question: pdfQuestion.trim() }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${res.status}`);
      }

      const data: PdfResearchResponse = await res.json();
      setPdfResult(data);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        setPdfError("استغرق الطلب وقتاً طويلاً. حاول مجدداً");
      } else if (err instanceof TypeError) {
        setPdfError("تعذّر الاتصال بالخادم.");
      } else {
        setPdfError(err instanceof Error ? err.message : "حدث خطأ غير متوقع");
      }
    } finally {
      clearTimeout(timeoutId);
      setPdfLoading(false);
    }
  }

  return (
    <main className="flex flex-1 w-full max-w-3xl mx-auto flex-col gap-6 md:gap-8 px-4 py-6 md:px-6 md:py-12">

      {/* Hero header */}
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl md:text-4xl font-bold text-zinc-900">
          المساعد البحثي الذكي
        </h1>
        <p className="text-zinc-500 text-sm md:text-base leading-relaxed">
          ابحث في موضوع، نقرأ المصادر، نحلل، نكتب التقرير، ونتحقق من صحته
        </p>
        <span className="self-start mt-1 bg-blue-50 text-blue-700 rounded-full px-3 py-1 text-xs font-medium">
          5 وكلاء ذكاء اصطناعي يعملون بالتوازي
        </span>
      </div>

      {/* Tabs */}
      <nav className="grid grid-cols-2 md:flex gap-2">
        <button
          onClick={() => setTab("web")}
          className={`flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
            tab === "web"
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
          }`}
        >
          {/* Globe icon */}
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
          بحث في الويب
        </button>
        <button
          onClick={() => setTab("pdf")}
          className={`flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
            tab === "pdf"
              ? "bg-blue-600 text-white shadow-sm"
              : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
          }`}
        >
          {/* Document icon */}
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="9" y1="13" x2="15" y2="13" />
            <line x1="9" y1="17" x2="13" y2="17" />
          </svg>
          بحث في PDF
        </button>
      </nav>

      {/* ── Web search tab ── */}
      {tab === "web" && (
        <>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <label htmlFor="topic" className="text-sm font-medium text-zinc-700">
              موضوع البحث
            </label>
            <input
              id="topic"
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              disabled={loading || streaming}
              placeholder="مثال: الذكاء الاصطناعي في التعليم"
              className="w-full rounded-lg border border-zinc-300 px-4 py-2.5 text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-zinc-100 disabled:cursor-not-allowed"
            />
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={loading || streaming || !topic.trim()}
                className="rounded-lg bg-blue-600 px-6 py-2.5 text-white font-medium hover:bg-blue-700 disabled:bg-zinc-400 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? "جارٍ البحث..." : "ابحث"}
              </button>
              <button
                type="button"
                onClick={handleStreamSubmit}
                disabled={loading || streaming || !topic.trim()}
                className="rounded-lg bg-violet-600 px-6 py-2.5 text-white font-medium hover:bg-violet-700 disabled:bg-zinc-400 disabled:cursor-not-allowed transition-colors"
              >
                {streaming ? "يكتب..." : "بحث مع Streaming"}
              </button>
            </div>
          </form>

          {loading && <LoadingSkeleton label="جارٍ البحث... قد يستغرق دقيقة أو أكثر" />}
          {streaming && !streamedReport && <LoadingSkeleton label="يُحضّر المصادر ويحلّل... سيبدأ الكتابة قريباً" />}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 text-sm">
              {error}
            </div>
          )}

          {(streaming || streamedReport || result) && (
            <>
              {/* Report */}
              <section className="flex flex-col gap-3">
                <div className="flex items-center gap-3">
                  <h2 className="text-xl font-semibold text-zinc-900">التقرير</h2>
                  {result && result.key_points_count > 0 && (
                    <span dir="ltr" className="bg-zinc-100 text-zinc-600 rounded-full px-2.5 py-0.5 text-xs font-medium">
                      {result.key_points_count} نقطة
                    </span>
                  )}
                  {streaming && (
                    <span className="text-xs text-violet-600 animate-pulse">يكتب...</span>
                  )}
                </div>
                <div className="rounded-xl border border-zinc-200 bg-white p-4 md:p-6 shadow-sm whitespace-pre-wrap leading-7 text-zinc-800 text-sm">
                  {streaming ? streamedReport : result?.report}
                </div>
              </section>

              {/* Sources */}
              {result && (
              <section className="flex flex-col gap-3">
                <h2 className="text-xl font-semibold text-zinc-900">المصادر</h2>
                {result.sources.length === 0 ? (
                  <p className="text-zinc-500 text-sm">لا توجد مصادر متاحة.</p>
                ) : (
                  <ul className="flex flex-col gap-3">
                    {result.sources.map((source, i) => {
                      const favicon = getFavicon(source.url);
                      return (
                        <li key={i} className="rounded-lg border border-zinc-200 bg-white p-4 hover:bg-zinc-50 transition-colors">
                          <div className="flex items-start gap-3">
                            <span className="flex-shrink-0 w-7 h-7 rounded-full bg-zinc-900 text-white text-xs font-semibold flex items-center justify-center">
                              {i + 1}
                            </span>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                {favicon && (
                                  <img
                                    src={favicon}
                                    alt=""
                                    width={16}
                                    height={16}
                                    className="flex-shrink-0 rounded-sm"
                                  />
                                )}
                                <a
                                  href={source.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  dir="ltr"
                                  className="font-medium text-blue-700 hover:underline truncate text-sm"
                                >
                                  {source.title}
                                </a>
                              </div>
                              <p className="text-sm text-zinc-600 leading-6">{source.summary}</p>
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </section>
              )}

              {/* FactCheck card */}
              {result && (
              <section className="flex flex-col gap-3">
                <h2 className="text-xl font-semibold text-zinc-900">التحقق من الصحة</h2>
                {result.fact_check === null ? (
                  <p className="text-sm text-zinc-500">لم تتوفر نتيجة التحقق هذه المرة.</p>
                ) : (
                  <div className="rounded-xl border border-zinc-200 bg-white p-4 md:p-6 shadow-sm flex flex-col gap-4">
                    {/* Confidence bar */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-zinc-700">درجة الثقة</span>
                        <span dir="ltr" className="text-sm font-semibold text-zinc-900">
                          {result.fact_check.confidence_score}%
                        </span>
                      </div>
                      <div className="h-2 bg-zinc-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${confidenceColor(result.fact_check.confidence_score)}`}
                          style={{ width: `${result.fact_check.confidence_score}%` }}
                        />
                      </div>
                    </div>

                    {/* Verified claims */}
                    {result.fact_check.verified_claims.length > 0 && (
                      <div>
                        <p className="text-sm font-medium text-zinc-700 mb-2">ادعاءات مؤكدة</p>
                        <ul className="flex flex-col gap-1.5">
                          {result.fact_check.verified_claims.map((claim, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-zinc-700">
                              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="20 6 9 17 4 12" />
                              </svg>
                              <span>{claim}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Questionable claims */}
                    {result.fact_check.questionable_claims.length > 0 && (
                      <div>
                        <p className="text-sm font-medium text-zinc-700 mb-2">ادعاءات تحتاج تحقق</p>
                        <ul className="flex flex-col gap-1.5">
                          {result.fact_check.questionable_claims.map((claim, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-zinc-700">
                              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                                <line x1="12" y1="9" x2="12" y2="13" />
                                <line x1="12" y1="17" x2="12.01" y2="17" />
                              </svg>
                              <span>{claim}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Notes */}
                    {result.fact_check.notes && (
                      <p className="text-sm text-zinc-600 leading-6 border-t border-zinc-100 pt-3">
                        {result.fact_check.notes}
                      </p>
                    )}
                  </div>
                )}
              </section>
              )}
            </>
          )}
        </>
      )}

      {/* ── PDF tab ── */}
      {tab === "pdf" && (
        <>
          {/* Step 1: upload */}
          <form onSubmit={handleUpload} className="flex flex-col gap-3">
            <label htmlFor="pdfFile" className="text-sm font-medium text-zinc-700">
              رفع ملف PDF (حد أقصى 10 ميغابايت)
            </label>
            <input
              id="pdfFile"
              type="file"
              accept=".pdf,application/pdf"
              onChange={(e) => {
                setPdfFile(e.target.files?.[0] ?? null);
                setPdfDocId(null);
                setPdfUploadMeta(null);
                setPdfResult(null);
                setPdfError(null);
              }}
              disabled={pdfUploading}
              className="w-full rounded-lg border border-zinc-300 px-4 py-2.5 text-zinc-700 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={!pdfFile || pdfUploading}
              className="w-full md:w-auto md:self-start rounded-lg bg-blue-600 px-6 py-2.5 text-white font-medium hover:bg-blue-700 disabled:bg-zinc-400 disabled:cursor-not-allowed transition-colors"
            >
              {pdfUploading ? "جارٍ الرفع..." : "رفع الملف"}
            </button>
          </form>

          {pdfUploading && <LoadingSkeleton label="جارٍ معالجة الـPDF..." />}

          {/* Upload success info */}
          {pdfUploadMeta && (
            <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 flex flex-col gap-1 text-sm">
              <p className="font-medium text-zinc-800">{pdfUploadMeta.filename}</p>
              <p className="text-zinc-500">
                <span dir="ltr">{pdfUploadMeta.pages}</span> صفحة ·{" "}
                <span dir="ltr">{pdfUploadMeta.chunks_count}</span> جزء ·{" "}
                <span dir="ltr">{pdfUploadMeta.metadata.file_size_kb}</span> كيلوبايت
              </p>
              {pdfPreview && (
                <p className="mt-2 text-zinc-600 leading-6 line-clamp-3 whitespace-pre-wrap">{pdfPreview}</p>
              )}
            </div>
          )}

          {/* Step 2: ask (shown only after successful upload) */}
          {pdfDocId && (
            <form onSubmit={handleAskPdf} className="flex flex-col gap-3">
              <label htmlFor="pdfQuestion" className="text-sm font-medium text-zinc-700">
                سؤالك عن الملف
              </label>
              <input
                id="pdfQuestion"
                type="text"
                value={pdfQuestion}
                onChange={(e) => setPdfQuestion(e.target.value)}
                disabled={pdfLoading}
                placeholder="مثال: ما الفكرة الرئيسية في هذا الملف؟"
                className="w-full rounded-lg border border-zinc-300 px-4 py-2.5 text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-zinc-100 disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={pdfLoading || !pdfQuestion.trim()}
                className="w-full md:w-auto md:self-start rounded-lg bg-blue-600 px-6 py-2.5 text-white font-medium hover:bg-blue-700 disabled:bg-zinc-400 disabled:cursor-not-allowed transition-colors"
              >
                {pdfLoading ? "جارٍ التحليل..." : "ابحث في الملف"}
              </button>
            </form>
          )}

          {pdfLoading && <LoadingSkeleton label="جارٍ تحليل الملف... قد يستغرق دقيقة أو أكثر" />}

          {pdfError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 text-sm">
              {pdfError}
            </div>
          )}

          {pdfResult && (
            <section className="flex flex-col gap-3">
              <h2 className="text-xl font-semibold text-zinc-900">التقرير</h2>
              <div className="rounded-xl border border-zinc-200 bg-white p-4 md:p-6 shadow-sm whitespace-pre-wrap leading-7 text-zinc-800 text-sm">
                {pdfResult.report}
              </div>
              {pdfResult.key_points.length > 0 && (
                <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                  <p className="text-sm font-medium text-zinc-700 mb-2">النقاط الرئيسية</p>
                  <ul className="flex flex-col gap-1.5">
                    {pdfResult.key_points.map((point, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-zinc-600">
                        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <circle cx="12" cy="12" r="4" />
                        </svg>
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          )}
        </>
      )}
    </main>
  );
}
