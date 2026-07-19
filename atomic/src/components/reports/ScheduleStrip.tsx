import { memo, useMemo } from 'react';

interface ScheduleStripProps {
  /// 6-field cron expression: `SEC MIN HOUR DOM MONTH DOW`, Sun = 0.
  /// Phase 4a only parses the patterns the backend currently emits:
  /// daily (`* * *`) and weekly (`* * <0-6>`). Anything richer falls
  /// back to a neutral strip — the 4b editor will tighten this.
  cron: string;
  /// IANA timezone name. `null` means the report's schedule is naive UTC,
  /// matching the backend default.
  tz: string | null;
  /// When true (e.g. report is disabled), cells render in a muted tone
  /// so the strip still communicates *would-fire-on* without implying
  /// the schedule is live.
  muted?: boolean;
}

/// Parse the DOW field of a 6-field cron expression. Returns the set of
/// weekdays (0=Sun..6=Sat) the report fires on. `*` collapses to the
/// full week. Lists (`1,3,5`), ranges (`1-5`), and step values (`*/2`)
/// are *not* implemented — we degrade to "no preview" by returning null.
function parseDow(field: string): Set<number> | null {
  if (field === '*' || field === '?') {
    return new Set([0, 1, 2, 3, 4, 5, 6]);
  }
  if (/^[0-6]$/.test(field)) {
    return new Set([Number(field)]);
  }
  return null;
}

/// Compute which of the next 7 days (starting today) the report will
/// fire on, in the report's timezone. We don't need the exact time —
/// just whether the day is in the fire-day set — so this is a fast
/// loop over the 7-day window with no cron-library dependency.
function computeNext7(cron: string, tz: string | null): boolean[] | null {
  const parts = cron.trim().split(/\s+/);
  // Be generous: 5-field cron (no seconds) is also valid in some
  // dialects; treat it as if the seconds field were `0`.
  let fields: string[];
  if (parts.length === 6) {
    fields = parts;
  } else if (parts.length === 5) {
    fields = ['0', ...parts];
  } else {
    return null;
  }
  const [, , , dom, month, dowField] = fields;
  // 4a only models the seeded shapes. Anything that constrains the day
  // of month or month falls back to "no preview" rather than rendering
  // a misleading strip.
  if (dom !== '*' || month !== '*') return null;
  const dowSet = parseDow(dowField);
  if (!dowSet) return null;

  // Resolve "today's weekday" in the report's timezone. We render the
  // strip aligned to the timezone the schedule is anchored to so the
  // user sees the same week the report's runner sees.
  const today = new Date();
  let weekdayIndex: number;
  try {
    weekdayIndex = weekdayInTz(today, tz);
  } catch {
    // Bad tz string: fall back to local-time weekday. Strip still
    // renders; the small drift won't mislead.
    weekdayIndex = today.getDay();
  }

  const out: boolean[] = [];
  for (let i = 0; i < 7; i++) {
    const day = (weekdayIndex + i) % 7;
    out.push(dowSet.has(day));
  }
  return out;
}

function weekdayInTz(date: Date, tz: string | null): number {
  if (!tz) return date.getDay();
  const fmt = new Intl.DateTimeFormat('en-US', { timeZone: tz, weekday: 'short' });
  const short = fmt.format(date);
  const order = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const idx = order.indexOf(short);
  return idx === -1 ? date.getDay() : idx;
}

const DAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

export const ScheduleStrip = memo(function ScheduleStrip({ cron, tz, muted = false }: ScheduleStripProps) {
  const days = useMemo(() => computeNext7(cron, tz), [cron, tz]);

  // Letter labels show today on the left, then the next 6 days.
  const todayIdx = useMemo(() => {
    try { return weekdayInTz(new Date(), tz); }
    catch { return new Date().getDay(); }
  }, [tz]);
  const labels = useMemo(
    () => Array.from({ length: 7 }, (_, i) => DAY_LABELS[(todayIdx + i) % 7]),
    [todayIdx]
  );

  if (!days) {
    // Unsupported cron shape: render an empty 7-cell strip with a single
    // muted dash so the row's layout grid doesn't reflow when a custom
    // schedule slides in (4b+).
    return (
      <div className="flex items-center gap-px" title={`Schedule: ${cron}${tz ? ` (${tz})` : ''} — preview unavailable`}>
        {Array.from({ length: 7 }, (_, i) => (
          <div key={i} className="w-2 h-3 rounded-[1px] bg-[var(--color-border)]/40" />
        ))}
      </div>
    );
  }

  const fillOn = muted ? 'bg-[var(--color-text-tertiary)]/60' : 'bg-[var(--color-accent)]';
  const fillOff = 'bg-[var(--color-border)]/40';

  return (
    <div className="flex flex-col items-start gap-0.5" aria-label="Next 7 days schedule preview">
      <div className="flex items-center gap-px">
        {days.map((fires, i) => (
          <div
            key={i}
            className={`w-2 h-3 rounded-[1px] ${fires ? fillOn : fillOff}`}
            title={fires ? 'Fires this day' : 'No fire'}
          />
        ))}
      </div>
      <div className="flex items-center gap-px font-mono text-[8px] text-[var(--color-text-tertiary)] leading-none tracking-[0.04em]">
        {labels.map((l, i) => (
          <div key={i} className="w-2 text-center tabular-nums">{l}</div>
        ))}
      </div>
    </div>
  );
});
