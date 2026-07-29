import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "TeleDrive v2 — Telegram to Google Drive on Colab" },
      {
        name: "description",
        content:
          "Download the complete TeleDrive package and Colab notebook to transfer Telegram media to Google Drive with real backend logic.",
      },
      { property: "og:title", content: "TeleDrive v2 — Telegram → Google Drive" },
      {
        property: "og:description",
        content:
          "A real Python backend (Telethon + Drive API + Gradio) packaged for one-click Colab import.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

const modules = [
  "bootstrap.py",
  "config.py",
  "logging_config.py",
  "utils.py",
  "models.py",
  "state_machine.py",
  "database.py",
  "migrations.py",
  "auth_manager.py",
  "telegram_links.py",
  "telegram_client.py",
  "media_scanner.py",
  "filters.py",
  "drive_client.py",
  "drive_quota.py",
  "duplicate_detector.py",
  "storage_manager.py",
  "checkpoint_manager.py",
  "queue_manager.py",
  "retry_policy.py",
  "transfer_manager.py",
  "progress_tracker.py",
  "error_handler.py",
  "snapshot.py",
  "handoff.py",
  "ui.py",
  "app.py",
  "i18n.py",
  "locale/ar.json",
  "locale/en.json",
];

function Index() {
  return (
    <div
      dir="rtl"
      className="min-h-screen bg-background text-foreground"
      style={{ fontFamily: "system-ui, -apple-system, 'Segoe UI', Tahoma, sans-serif" }}
    >
      <main className="mx-auto max-w-3xl px-6 py-12">
        <header className="mb-10">
          <h1 className="text-3xl font-bold tracking-tight">
            TeleDrive v2 — ناقل تيليجرام إلى Google Drive
          </h1>
          <p className="mt-3 text-muted-foreground leading-relaxed">
            حزمة بايثون كاملة (Telethon + Google Drive API + Gradio) تعمل داخل Google Colab.
            الفرونت-اند دي مجرد صفحة تحميل — التطبيق الحقيقي هو الحزمة اللي هتشغّلها في Colab.
          </p>
        </header>

        <section className="mb-8 rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">1) حمّل الملفين</h2>
          <div className="flex flex-col gap-3 sm:flex-row">
            <a
              href="/teledrive-package.zip"
              download
              className="inline-flex items-center justify-center rounded-md bg-primary px-5 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              تحميل حزمة TeleDrive (ZIP)
            </a>
            <a
              href="/TeleDrive.ipynb"
              download
              className="inline-flex items-center justify-center rounded-md border border-input bg-background px-5 py-3 text-sm font-medium transition-colors hover:bg-accent"
            >
              تحميل ملف Colab (.ipynb)
            </a>
          </div>
        </section>

        <section className="mb-8 rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">2) شغّلها في Colab</h2>
          <ol className="list-decimal space-y-2 pr-6 text-sm leading-relaxed">
            <li>
              افتح{" "}
              <a
                className="text-primary underline"
                href="https://colab.research.google.com"
                target="_blank"
                rel="noreferrer"
              >
                colab.research.google.com
              </a>{" "}
              ثم File → Upload notebook وارفع{" "}
              <code className="rounded bg-muted px-1">TeleDrive.ipynb</code>.
            </li>
            <li>
              الخلية 1: ارفع الملف{" "}
              <code className="rounded bg-muted px-1">teledrive-package.zip</code> لما تُطلَب منك.
            </li>
            <li>
              الخلية 2: <code className="rounded bg-muted px-1">bootstrap.run()</code> ينشئ المجلدات
              وقاعدة البيانات.
            </li>
            <li>
              الخلية 3: أدخل <code className="rounded bg-muted px-1">api_id</code> و{" "}
              <code className="rounded bg-muted px-1">api_hash</code> عبر{" "}
              <code className="rounded bg-muted px-1">getpass</code>.
            </li>
            <li>
              الخلية 4: <code className="rounded bg-muted px-1">app.launch()</code> يفتح واجهة
              Gradio.
            </li>
            <li>
              في الواجهة: سجّل دخول تيليجرام، ارفع OAuth JSON لـ Drive، الصق رابطاً، Analyze →
              Start.
            </li>
          </ol>
        </section>

        <section className="mb-8 rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">3) اللي جوّه الحزمة</h2>
          <p className="mb-3 text-sm text-muted-foreground">
            {modules.length} وحدة بايثون فعلية — مش سلاسل نصية داخل الفرونت، ملفات
            <code className="mx-1 rounded bg-muted px-1">.py</code>حقيقية:
          </p>
          <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground sm:grid-cols-3">
            {modules.map((m) => (
              <li key={m} className="font-mono">
                {m}
              </li>
            ))}
          </ul>
        </section>

        <section className="mb-8 rounded-lg border border-border bg-card p-6">
          <h2 className="mb-4 text-lg font-semibold">
            وظائف الباك-اند (كلها مربوطة بأزرار الواجهة)
          </h2>
          <ul className="list-disc space-y-1 pr-6 text-sm leading-relaxed">
            <li>تسجيل دخول تيليجرام حقيقي (Telethon + phone/code/2FA).</li>
            <li>OAuth حقيقي لـ Google Drive Desktop مع حفظ التوكن.</li>
            <li>
              تحليل روابط: عامة، خاصة <code className="rounded bg-muted px-1">t.me/c/…</code>،
              دعوات، saved، ألبومات.
            </li>
            <li>فلاتر: نوع/امتداد/حجم/تاريخ/نطاق IDs/include/exclude.</li>
            <li>
              Queue + State Machine بـ 12 حالة وانتقالات صارمة (فقط QueueManager يعدّل الحالة).
            </li>
            <li>Semaphore: Safe=1, Balanced=2, Fast=3, Manual≤4 — بدون تجاوز.</li>
            <li>Retry: 5 محاولات، exp x2، cap 60s، jitter، transient فقط. FloodWait يُحترم.</li>
            <li>
              كشف التكرار عبر{" "}
              <code className="rounded bg-muted px-1">appProperties.source_key</code> + الحجم.
            </li>
            <li>
              Checkpoints ذرية تُرفع إلى{" "}
              <code className="rounded bg-muted px-1">TeleDrive_AppData</code> على Drive.
            </li>
            <li>Reconcile بعد إعادة تشغيل Colab: يتحقق من Drive قبل إعادة النقل.</li>
            <li>حذف temp فقط بعد التحقق من الرفع الناجح.</li>
            <li>i18n عربي/إنجليزي حي مع RTL، وسجلّات مع Redaction للأسرار.</li>
          </ul>
        </section>

        <footer className="text-xs text-muted-foreground">
          v1.0.0 — Constitution spec v2.0. لا يُرسَل أي سرّ إلى هذا الموقع، كل شيء يبقى داخل حساباتك
          على Google و Telegram.
        </footer>
      </main>
    </div>
  );
}
