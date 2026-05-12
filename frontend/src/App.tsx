import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

const API_BASE_URL = "http://localhost:8000";
const WEEKDAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];

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
  encouragement: {
    title: string;
    message: string;
    reminders: string[];
  };
};

type CalendarDay = {
  dateKey: string;
  dayNumber: number;
  isCurrentMonth: boolean;
  isSelected: boolean;
  isBriefingDate: boolean;
  scheduleCount: number;
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
  const [selectedDate, setSelectedDate] = useState<string>("");
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

        const data: ScheduleResponse = await response.json();
        setSchedule(data);
        setSelectedDate(data.date);
      } catch {
        setError("일정을 불러오지 못했어요. 잠시 뒤 다시 시도해주세요.");
      } finally {
        setLoadingSchedule(false);
      }
    }

    loadSchedule();
  }, []);

  const schedules = schedule?.schedules ?? [];
  const fallbackDate = toDateKey(new Date());
  const briefingDate = schedule?.date || selectedDate || fallbackDate;
  const activeSelectedDate = selectedDate || briefingDate;
  const selectedSchedules = useMemo(() => {
    return schedules.filter((item) => getDateKeyFromSchedule(item) === activeSelectedDate);
  }, [activeSelectedDate, schedules]);
  const selectedHours = useMemo(() => {
    return selectedSchedules.reduce((total, item) => total + getDurationHours(item), 0);
  }, [selectedSchedules]);
  const scheduleCountByDate = useMemo(() => countSchedulesByDate(schedules), [schedules]);
  const calendarDays = useMemo(() => {
    return buildCalendarDays(briefingDate, activeSelectedDate, briefingDate, scheduleCountByDate);
  }, [activeSelectedDate, briefingDate, scheduleCountByDate]);
  const canBriefSelectedDate = activeSelectedDate === briefingDate && selectedSchedules.length > 0;
  const cautionCount = briefing
    ? briefing.analysis.schedule_conflicts.length + briefing.analysis.insufficient_buffer_time.length
    : 0;

  async function handleAnalyze() {
    if (!canBriefSelectedDate) {
      setBriefing(null);
      return;
    }

    setAnalyzing(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/briefing`);
      if (!response.ok) {
        throw new Error("브리핑을 만들지 못했어요.");
      }
      setBriefing(await response.json());
    } catch {
      setError("브리핑을 만들지 못했어요. 잠시 뒤 다시 시도해주세요.");
    } finally {
      setAnalyzing(false);
    }
  }

  function handleSelectDate(dateKey: string) {
    setSelectedDate(dateKey);
    if (dateKey !== briefingDate) {
      setBriefing(null);
    }
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,#ffffff_0,#f7fbff_38%,#f7f9fb_72%)] px-5 py-8 sm:px-8 lg:py-12">
      <div className="mx-auto max-w-7xl">
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
            캘린더에서 오늘을 먼저 챙겨요
          </h1>
          <p className="mt-4 max-w-2xl text-lg leading-8 text-calm">
            전체 일정을 한눈에 보고, 오늘 하루의 흐름과 미리 챙길 점을 따뜻하게 정리해드려요.
          </p>
        </section>

        {error && (
          <div className="mb-6 rounded-3xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm font-semibold text-amber-800">
            {error}
          </div>
        )}

        <section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
          <div className="space-y-6">
            <section className="rounded-[1.8rem] border border-line bg-white p-5 shadow-soft sm:p-7">
              <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-calm">전체 캘린더</p>
                  <h2 className="mt-1 text-2xl font-black text-ink">
                    {formatMonthTitle(briefingDate)}
                  </h2>
                </div>
                <span className="rounded-full bg-slate-50 px-3 py-1.5 text-sm font-bold text-calm">
                  오늘 브리핑 가능 날짜 표시
                </span>
              </div>
              <CalendarGrid days={calendarDays} onSelectDate={handleSelectDate} />
            </section>

            <section className="rounded-[1.8rem] border border-line bg-white p-5 shadow-soft sm:p-7">
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-calm">선택한 날짜</p>
                  <h2 className="mt-1 text-xl font-black text-ink">
                    {selectedDate ? formatDate(selectedDate) : "날짜를 선택해주세요"}
                  </h2>
                </div>
                <span className="text-sm font-semibold text-calm">
                  {selectedSchedules.length}개 일정
                </span>
              </div>

              {loadingSchedule && <ScheduleSkeleton />}
              {!loadingSchedule && selectedSchedules.length === 0 && (
                <EmptyState message="이 날짜에는 아직 등록된 일정이 없어요." />
              )}
              {!loadingSchedule && selectedSchedules.length > 0 && (
                <div className="relative space-y-4 before:absolute before:bottom-6 before:left-[1.15rem] before:top-6 before:w-px before:bg-line">
                  {selectedSchedules.map((item) => (
                    <ScheduleCard key={item.id} item={item} />
                  ))}
                </div>
              )}
            </section>
          </div>

          <aside className="space-y-4">
            <section className="rounded-[1.8rem] border border-line bg-white p-6 shadow-soft">
              <p className="text-sm font-bold text-calm">오늘은 이런 하루예요</p>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <StatCard label="일정 수" value={`${selectedSchedules.length}개`} />
                <StatCard label="예정된 시간" value={formatHours(selectedHours)} />
                <StatCard label="주의 구간" value={briefing ? `${cautionCount}곳` : "확인 전"} />
                <StatCard
                  label="일정 유형"
                  value={briefing ? briefing.persona.name.replace(" 플래너", "") : "분석 전"}
                />
              </div>
              <button
                className="mt-5 w-full rounded-2xl bg-coral px-5 py-4 text-base font-black text-white shadow-lg shadow-orange-200 transition hover:bg-[#f06b58] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={loadingSchedule || analyzing || !canBriefSelectedDate}
                onClick={handleAnalyze}
              >
                {analyzing ? "정리하는 중..." : "오늘 일정 분석하기"}
              </button>
              {!canBriefSelectedDate && (
                <p className="mt-3 text-center text-sm font-semibold text-calm">
                  오늘 날짜를 선택하면 브리핑을 볼 수 있어요.
                </p>
              )}
            </section>

            {briefing && (
              <section className="rounded-[1.8rem] border border-rose-100 bg-rose-50/80 p-6 shadow-soft">
                <p className="text-sm font-bold text-rose-500">{briefing.encouragement.title}</p>
                <p className="mt-3 text-sm leading-7 text-rose-900">
                  {briefing.encouragement.message}
                </p>
              </section>
            )}

            {briefing && (
              <section className="rounded-[1.8rem] border border-line bg-white p-6 shadow-soft">
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
                {[...briefing.briefing.recommended_actions, ...briefing.encouragement.reminders].map(
                  (action) => (
                    <li
                      className="flex gap-3 rounded-2xl border border-line bg-white px-4 py-4 text-sm leading-6 text-calm"
                      key={action}
                    >
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-sm font-black text-emerald-700">
                        ✓
                      </span>
                      <span>{action}</span>
                    </li>
                  ),
                )}
              </ul>
            </ResultCard>
          </section>
        )}
      </div>
    </main>
  );
}

function CalendarGrid({
  days,
  onSelectDate,
}: {
  days: CalendarDay[];
  onSelectDate: (dateKey: string) => void;
}) {
  return (
    <div>
      <div className="grid grid-cols-7 gap-2">
        {WEEKDAY_LABELS.map((label) => (
          <div className="pb-2 text-center text-xs font-black text-calm" key={label}>
            {label}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-2">
        {days.map((day) => (
          <button
            className={[
              "min-h-[5.25rem] rounded-2xl border p-2 text-left transition",
              day.isSelected
                ? "border-coral bg-orange-50 shadow-lg shadow-orange-100"
                : "border-line bg-white hover:border-blue-200 hover:bg-blue-50/50",
              !day.isCurrentMonth ? "opacity-35" : "",
            ].join(" ")}
            key={day.dateKey}
            onClick={() => onSelectDate(day.dateKey)}
            type="button"
          >
            <div className="flex items-center justify-between gap-1">
              <span
                className={[
                  "flex h-7 w-7 items-center justify-center rounded-full text-sm font-black",
                  day.isBriefingDate ? "bg-ink text-white" : "text-ink",
                ].join(" ")}
              >
                {day.dayNumber}
              </span>
              {day.scheduleCount > 0 && (
                <span className="rounded-full bg-emerald-50 px-2 py-1 text-[0.68rem] font-black text-emerald-700">
                  {day.scheduleCount}개
                </span>
              )}
            </div>
            {day.isBriefingDate && (
              <p className="mt-3 line-clamp-2 text-xs font-bold leading-5 text-calm">
                오늘 브리핑
              </p>
            )}
          </button>
        ))}
      </div>
    </div>
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

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-[1.4rem] border border-dashed border-line bg-slate-50 px-5 py-12 text-center text-sm font-semibold text-calm">
      {message}
    </div>
  );
}

function buildCalendarDays(
  baseDateKey: string,
  selectedDateKey: string,
  briefingDateKey: string,
  scheduleCountByDate: Record<string, number>,
) {
  const baseDate = parseLocalDate(baseDateKey);
  if (Number.isNaN(baseDate.getTime())) {
    return buildCalendarDays(toDateKey(new Date()), selectedDateKey, briefingDateKey, scheduleCountByDate);
  }

  const firstDayOfMonth = new Date(baseDate.getFullYear(), baseDate.getMonth(), 1);
  const startDate = new Date(firstDayOfMonth);
  startDate.setDate(firstDayOfMonth.getDate() - firstDayOfMonth.getDay());

  return Array.from({ length: 42 }, (_, index): CalendarDay => {
    const currentDate = new Date(startDate);
    currentDate.setDate(startDate.getDate() + index);
    const dateKey = toDateKey(currentDate);

    return {
      dateKey,
      dayNumber: currentDate.getDate(),
      isCurrentMonth: currentDate.getMonth() === baseDate.getMonth(),
      isSelected: dateKey === selectedDateKey,
      isBriefingDate: dateKey === briefingDateKey,
      scheduleCount: scheduleCountByDate[dateKey] ?? 0,
    };
  });
}

function countSchedulesByDate(schedules: ScheduleItem[]) {
  return schedules.reduce<Record<string, number>>((accumulator, item) => {
    const dateKey = getDateKeyFromSchedule(item);
    accumulator[dateKey] = (accumulator[dateKey] ?? 0) + 1;
    return accumulator;
  }, {});
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
  const parsed = parseLocalDate(date);
  if (Number.isNaN(parsed.getTime())) {
    return "날짜 확인 중";
  }
  return `${parsed.getFullYear()}년 ${parsed.getMonth() + 1}월 ${parsed.getDate()}일`;
}

function formatMonthTitle(date: string) {
  const parsed = parseLocalDate(date);
  if (Number.isNaN(parsed.getTime())) {
    return "이번 달";
  }
  return `${parsed.getFullYear()}년 ${parsed.getMonth() + 1}월`;
}

function getDateKeyFromSchedule(item: ScheduleItem) {
  return item.start.split(" ")[0];
}

function parseLocalDate(date: string) {
  if (!date) {
    return new Date(Number.NaN);
  }

  return new Date(`${date}T00:00:00`);
}

function toDateKey(date: Date) {
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function cleanWarningText(text: string) {
  return text.replace("리스크", "주의할 점");
}

export default App;
