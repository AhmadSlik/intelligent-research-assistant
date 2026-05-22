# 📘 ملف تعلّم Claude Code — اليوم الثامن عشر

**الطالب:** أحمد سليق  
**المدرّب:** Claude Sonnet 4.6  
**اليوم:** اليوم الثامن عشر — Deployment  
**التاريخ:** 7 مايو 2026  
**المدة الفعلية:** ~3 ساعات  
**تقييم اليوم:** 8/10

---

## 🎯 شو تعلمنا اليوم؟

اليوم رفعنا المشروع على الإنترنت — أي شخص في العالم يقدر يستخدمه الحين!

---

## 🌍 الروابط النهائية

```
Frontend: https://sprightly-empanada-0cbf25.netlify.app
Backend:  https://web-production-e01f8.up.railway.app
```

---

## 📚 المفاهيم بالتفصيل

### 1. شو هو Deployment؟

```
قبل:   localhost:3000 + localhost:8000 (جهازك فقط)
بعد:   Netlify + Railway (الكل يقدر يوصله)
```

### 2. Railway (Backend)

Railway = منصة cloud لرفع الـPython/FastAPI apps.

**ملفات أضفناها:**

```
Procfile:
web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT

railway.json:
{
  "build": {"builder": "NIXPACKS"},
  "deploy": {
    "startCommand": "cd backend && uvicorn main:app...",
    "healthcheckPath": "/health"
  }
}
```

**ليش `--host 0.0.0.0`؟**
على localhost الـserver يسمع لجهازك فقط. `0.0.0.0` يعني "اسمع لأي اتصال من أي مكان".

**ليش `$PORT`؟**
Railway يحدد الـport تلقائياً — ما نحدده نحن.

### 3. Netlify (Frontend)

Netlify = منصة متخصصة بـNext.js وReact apps.

**netlify.toml:**
```toml
[build]
  base = "frontend"
  command = "npm run build"
  publish = ".next"

[[plugins]]
  package = "@netlify/plugin-nextjs"
```

### 4. CORS للـProduction

```python
# محلي فقط — ما يشتغل للـproduction
allow_origins=["http://localhost:3000"]

# production — يقبل من أي domain
allow_origins=["*"]
```

---

## 🐛 الأخطاء اللي واجهناها وحلولها

**خطأ 1:** `pydantic-core` يحتاج Rust للـbuild
**الحل:** Netlify يبني Python — غيّرنا لـNextjs فقط

**خطأ 2:** `publish = "frontend/.next"` مع `base = "frontend"` = مسار مضاعف
**الحل:** `publish = ".next"` فقط

**خطأ 3:** فراغ في الـAPI key على Railway
**الحل:** حذف الـkey وإعادة كتابته بدون فراغات

**خطأ 4:** `gopenrouter/free` بدل `openrouter/free`
**الحل:** تصحيح الإملاء في Variables

---

## 🧠 أسئلة الاختبار + الأجوبة

**س1:** شو الفرق بين Railway وNetlify؟
**ج:** Railway للـBackend (Python)، Netlify للـFrontend (Next.js) ✅

**س2:** شو هو Procfile؟
**ج:** يخبر Railway كيف يشغّل الـserver ✅

**س3:** شو غيّرنا في CORS للـproduction؟
**ج:** من `["http://localhost:3000"]` لـ`["*"]` عشان يقبل من أي domain ✅

---

## 📅 التحضير ليوم 19

**موضوع يوم 19:** Portfolio Polish — README احترافي + screenshots

---

**نهاية توثيق اليوم الثامن عشر** ✅  
📌 *"مشروعك الحين على الإنترنت — أي شخص في العالم يقدر يستخدمه!"*
