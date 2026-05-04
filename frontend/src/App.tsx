import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

const API_BASE_URL = "http://localhost:8000";

type ScheduleItem = {
  id: string;
  title: string;
  category: string;
  start: string;
  end: string;
  location?: string | null;
  notes?: string | null;
};

type ScheduleResponse = {
  date: string;
  timezone: string;
  schedules: ScheduleItem[];
};

type Analysis = {
  total_schedules: number;
  total_scheduled_hours: number;
  schedule_conflicts: Array<Record<string, unknown>>;
  insufficient_buffer_time: Array<Record<string, unknown>>;
};

type Briefing = {
  summary: string;
  risk_message: string;
  recommended_actions: string[];
};

type BriefingResponse = {
  analysis: Analysis;
  persona: {
    name: string;
    rationale: string;
  };
  briefing: Briefing;
};

const categoryStyles: Record<string, { label: string; className: string }> = {
  업무: { label: "업무", className: "bg-blue-50 text-blue-700" },
  고객: { label: "고객", className: "bg-orange-50 text-orange-700" },
  개인: { label: "개인", className: "bg-violet-50 text-violet-700" },
  건강: { label: "건강", className: "bg-emerald-50 text-emerald-700" },
  여행: { label: "여행", className: "bg-cyan-50 text-cyan-700" },
  학습: { label: "학습", className: "bg-rose-50 text-rose-700" },
  네트워킹: { label: "네트워킹", className: "bg-sky-50 text-sky-700" },
  회복: { label: "회복", className: "bg-lime-50 text-lime-700" },
};

function App() {
  const [schedule, setSchedule] = useState<ScheduleResponse | null>(null);
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [loadingSchedule, setLoadingSchedule] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadSchedule() {
      try {
        const response = await fetch(`${API_BASE_URL}/schedule`);
        if (!response.ok) {
          throw new Error("일정을 불러오지 못했어요.");
        }
        setSchedule(await response.json());
      } catch {
        setError("백엔드 서버를 먼저 실행한 뒤 화면을 새로고침해주세요.");
      } finally {
        setLoadingSchedule(false);
      }
    }

    loadSchedule();
  }, []);

  const schedules = schedule?.schedules ?? [];
  const previewHours = useMemo(() => {
    return schedules.reduce((total, item) => total + getDurationHours(item), 0);
  }, [schedules]);

  const cautionCount = briefing
    ? briefing.analysis.schedule_conflicts.length + briefing.analysis.insufficient_buffer_time.length
    : 0;

  async function handleAnalyze() {
    setAnalyzing(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/briefing`);
      if (!response.ok) {
        throw new Error("브리핑을 만들지 못했어요.");
      }
      setBriefing(await response.json());
    } catch {
      setError("브리핑을 만들지 못했어요. 백엔드 서버 상태를 확인해주세요.");
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#ffffff_0,#f7fbff_38%,#f7f9fb_72%)] px-5 py-8 sm:px-8 lg:py-12">
      <div className="mx-auto max-w-6xl">
        <section className="mb-8 rounded-[2rem] border border-line bg-white/85 p-7 shadow-soft backdrop-blur sm:p-10">
          <div className="mb-6 flex flex-wrap items-center gap-3">
            <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-sm font-bold text-emerald-700">
              아 맞다,
            </span>
            {schedule && (
              <span className="rounded-full border border-line bg-white px-3 py-1.5 text-sm font-semibold text-calm">
                {formatDate(schedule.date)} · {schedule.timezone}
              </span>
            )}
          </div>
          <h1 className="max-w-3xl text-4xl font-black leading-tight text-ink sm:text-6xl">
            오늘 일정 브리핑
          </h1>
          <p className="mt-4 max-w-2xl text-lg leading-8 text-calm">
            오늘 하루의 흐름과 미리 챙길 점을 한눈에 정리해드려요.
          </p>
        </section>

        {error && (
          <div className="mb-6 rounded-3xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm font-semibold text-amber-800">
            {error}
          </div>
        )}

        <section className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-black text-ink">오늘 일정</h2>
              <span className="text-sm font-semibold text-calm">{schedules.length}개 일정</span>
            </div>
            <div className="relative space-y-4 before:absolute before:bottom-6 before:left-[1.15rem] before:top-6 before:w-px before:bg-line">
              {loadingSchedule && <ScheduleSkeleton />}
              {!loadingSchedule &&
                schedules.map((item) => <ScheduleCard key={item.id} item={item} />)}
            </div>
          </div>

          <aside className="space-y-4">
            <section className="rounded-[1.6rem] border border-line bg-white p-6 shadow-soft">
              <p className="text-sm font-bold text-calm">오늘은 이런 하루예요</p>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <StatCard label="일정 수" value={`${schedules.length}개`} />
                <StatCard label="예정된 시간" value={formatHours(previewHours)} />
                <StatCard label="주의 구간" value={briefing ? `${cautionCount}곳` : "확인 전"} />
                <StatCard
                  label="일정 유형"
                  value={briefing ? briefing.persona.name.replace(" 플래너", "") : "분석 전"}
                />
              </div>
              <button
                className="mt-5 w-full rounded-2xl bg-coral px-5 py-4 text-base font-black text-white shadow-lg shadow-orange-200 transition hover:bg-[#f06b58] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={loadingSchedule || analyzing}
                onClick={handleAnalyze}
              >
                {analyzing ? "정리하는 중..." : "오늘 일정 분석하기"}
              </button>
            </section>

            {briefing && (
              <section className="rounded-[1.6rem] border border-line bg-white p-6 shadow-soft">
                <p className="text-sm font-bold text-calm">나의 일정 유형</p>
                <h3 className="mt-2 text-2xl font-black text-ink">{briefing.persona.name}</h3>
                <p className="mt-3 text-sm leading-7 text-calm">{briefing.persona.rationale}</p>
              </section>
            )}
          </aside>
        </section>

        {briefing && (
          <section className="mt-8 grid gap-5 lg:grid-cols-3">
            <ResultCard title="오늘 하루 요약" className="lg:col-span-2">
              <p>{briefing.briefing.summary}</p>
            </ResultCard>

            <ResultCard title="조심할 점" tone="warning">
              <p>{cleanWarningText(briefing.briefing.risk_message)}</p>
            </ResultCard>

            <ResultCard title="미리 챙기면 좋은 것" className="lg:col-span-3">
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {briefing.briefing.recommended_actions.map((action) => (
                  <li
                    className="flex gap-3 rounded-2xl border border-line bg-white px-4 py-4 text-sm leading-6 text-calm"
                    key={action}
                  >
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-sm font-black text-emerald-700">
                      ✓
                    </span>
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </ResultCard>
          </section>
        )}
      </div>
    </main>
  );
}

function ScheduleCard({ item }: { item: ScheduleItem }) {
  const badge = categoryStyles[item.category] ?? {
    label: item.category,
    className: "bg-slate-100 text-slate-600",
  };

  return (
    <article className="relative ml-12 rounded-[1.4rem] border border-line bg-white p-5 shadow-[0_12px_30px_rgba(31,41,55,0.06)]">
      <span className="absolute -left-[2.95rem] top-6 h-4 w-4 rounded-full border-4 border-white bg-mint shadow" />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-sm font-black text-blue-600">{formatTimeRange(item)}</span>
        <span className={`rounded-full px-3 py-1 text-xs font-black ${badge.className}`}>
          {badge.label}
        </span>
      </div>
      <h3 className="mt-3 text-lg font-black text-ink">{item.title}</h3>
      <p className="mt-2 text-sm font-bold text-slate-500">{item.location ?? "장소 미정"}</p>
      <p className="mt-3 text-sm leading-7 text-calm">{item.notes ?? "메모 없음"}</p>
    </article>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-line bg-slate-50 px-4 py-4">
      <p className="text-xs font-bold text-calm">{label}</p>
      <strong className="mt-1 block text-xl font-black text-ink">{value}</strong>
    </div>
  );
}

function ResultCard({
  title,
  children,
  tone = "calm",
  className = "",
}: {
  title: string;
  children: ReactNode;
  tone?: "calm" | "warning";
  className?: string;
}) {
  const toneClass =
    tone === "warning"
      ? "border-amber-200 bg-amber-50 text-amber-900"
      : "border-line bg-white text-calm";

  return (
    <section className={`rounded-[1.6rem] border p-6 shadow-soft ${toneClass} ${className}`}>
      <h2 className="mb-3 text-xl font-black text-ink">{title}</h2>
      <div className="text-sm leading-7">{children}</div>
    </section>
  );
}

function ScheduleSkeleton() {
  return (
    <>
      {[0, 1, 2].map((item) => (
        <div
          className="ml-12 h-36 animate-pulse rounded-[1.4rem] border border-line bg-white"
          key={item}
        />
      ))}
    </>
  );
}

function formatTimeRange(item: ScheduleItem) {
  return `${item.start.split(" ")[1]} - ${item.end.split(" ")[1]}`;
}

function getDurationHours(item: ScheduleItem) {
  const start = new Date(item.start.replace(" ", "T"));
  const end = new Date(item.end.replace(" ", "T"));
  return Math.max(0, (end.getTime() - start.getTime()) / 1000 / 60 / 60);
}

function formatHours(hours: number) {
  if (Number.isInteger(hours)) {
    return `${hours}시간`;
  }
  return `${hours.toFixed(2).replace(/0+$/, "").replace(/\.$/, "")}시간`;
}

function formatDate(date: string) {
  const parsed = new Date(`${date}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return date;
  }
  return `${parsed.getFullYear()}년 ${parsed.getMonth() + 1}월 ${parsed.getDate()}일`;
}

function cleanWarningText(text: string) {
  return text.replace("리스크", "주의할 점");
}

export default App;
