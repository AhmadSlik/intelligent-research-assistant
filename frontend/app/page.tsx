'use client'

import { useState } from "react";

type Source = { title: string; url: string; summary: string };
type ResearchResponse = {
  topic: string;
  report: string;
  sources: Source[];
  key_points_count: number;
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

export default function Home() {
  const [tab, setTab] = useState<"web" | "pdf">("web");

  // --- Web search state ---
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    <main dir="rtl" lang="ar" className="flex flex-1 w-full max-w-3xl mx-auto flex-col gap-8 px-6 py-12">
      <div>
        <h1 className="text-3xl font-semibold text-zinc-900">مساعد البحث الذكي</h1>
        <p className="mt-2 text-zinc-500 text-sm">أدخل موضوعاً وسيقوم النظام بالبحث وكتابة تقرير شامل</p>
      </div>

      {/* Tabs */}
      <nav className="flex gap-2">
        <button
          onClick={() => setTab("web")}
          className={`rounded-lg px-5 py-2 text-sm font-medium transition-colors ${
            tab === "web"
              ? "bg-blue-600 text-white"
              : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
          }`}
        >
          بحث في الويب
        </button>
        <button
          onClick={() => setTab("pdf")}
          className={`rounded-lg px-5 py-2 text-sm font-medium transition-colors ${
            tab === "pdf"
              ? "bg-blue-600 text-white"
              : "bg-zinc-100 text-zinc-700 hover:bg-zinc-200"
          }`}
        >
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
              className="w-full rounded-lg border border-zinc-300 px-4 py-2 text-zinc-700 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={!pdfFile || pdfUploading}
              className="self-start rounded-lg bg-blue-600 px-6 py-2 text-white font-medium hover:bg-blue-700 disabled:bg-zinc-400 disabled:cursor-not-allowed transition-colors"
            >
              {pdfUploading ? "جارٍ الرفع..." : "رفع الملف"}
            </button>
          </form>

          {pdfUploading && (
            <p className="text-sm text-zinc-500">جارٍ معالجة الـPDF...</p>
          )}

          {/* Upload success info */}
          {pdfUploadMeta && (
            <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 flex flex-col gap-1 text-sm">
              <p className="font-medium text-zinc-800">{pdfUploadMeta.filename}</p>
              <p className="text-zinc-500">
                {pdfUploadMeta.pages} صفحة · {pdfUploadMeta.chunks_count} جزء · {pdfUploadMeta.metadata.file_size_kb} كيلوبايت
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
                className="w-full rounded-lg border border-zinc-300 px-4 py-2 text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-zinc-100 disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={pdfLoading || !pdfQuestion.trim()}
                className="self-start rounded-lg bg-blue-600 px-6 py-2 text-white font-medium hover:bg-blue-700 disabled:bg-zinc-400 disabled:cursor-not-allowed transition-colors"
              >
                {pdfLoading ? "جارٍ التحليل..." : "ابحث في الملف"}
              </button>
            </form>
          )}

          {pdfLoading && (
            <p className="text-sm text-zinc-500">جارٍ تحليل الملف... قد يستغرق دقيقة أو أكثر</p>
          )}

          {pdfError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 text-sm">
              {pdfError}
            </div>
          )}

          {pdfResult && (
            <section className="flex flex-col gap-3">
              <h2 className="text-xl font-semibold text-zinc-900">التقرير</h2>
              <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm whitespace-pre-wrap leading-7 text-zinc-800 text-sm">
                {pdfResult.report}
              </div>
              {pdfResult.key_points.length > 0 && (
                <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                  <p className="text-sm font-medium text-zinc-700 mb-2">النقاط الرئيسية</p>
                  <ul className="flex flex-col gap-1">
                    {pdfResult.key_points.map((point, i) => (
                      <li key={i} className="text-sm text-zinc-600">• {point}</li>
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
