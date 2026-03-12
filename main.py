from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk


BASELINE_WEEKLY_HOURS = 40.0
BASELINE_WORKING_DAYS = 5
BASELINE_HOURS_PER_DAY = BASELINE_WEEKLY_HOURS / BASELINE_WORKING_DAYS
MIN_HOURS_PER_DAY = 3.0
MAX_HOURS_PER_DAY = 10.0
FULL_PRODUCTIVITY_HOURS_PER_DAY = 6.0
PENALTY_START_HOURS_PER_DAY = 8.0
STRONG_PENALTY_PER_HOUR = 0.25
RECOVERY_PENALTY_START_DAYS = 5
RECOVERY_PENALTY_PER_EXTRA_DAY = 0.10
PLOT_MIN_HOURS_PER_DAY = MIN_HOURS_PER_DAY
PLOT_MAX_HOURS_PER_DAY = MAX_HOURS_PER_DAY
CURVE_CANVAS_WIDTH = 540
CURVE_CANVAS_HEIGHT = 280


def clamp_hours_per_day(hours_per_day: float) -> float:
    return min(max(0.0, hours_per_day), MAX_HOURS_PER_DAY)


def compute_daily_utility_hours(hours_per_day: float) -> float:
    """Convert scheduled daily hours into utility-weighted daily hours."""
    safe_hours = clamp_hours_per_day(hours_per_day)

    if safe_hours < MIN_HOURS_PER_DAY:
        return 0.0

    if safe_hours <= FULL_PRODUCTIVITY_HOURS_PER_DAY:
        return safe_hours

    if safe_hours <= PENALTY_START_HOURS_PER_DAY:
        taper_width = PENALTY_START_HOURS_PER_DAY - FULL_PRODUCTIVITY_HOURS_PER_DAY
        extra_hours = safe_hours - FULL_PRODUCTIVITY_HOURS_PER_DAY
        tapered_extra_utility = extra_hours - (extra_hours**2) / (2 * taper_width)
        return FULL_PRODUCTIVITY_HOURS_PER_DAY + tapered_extra_utility

    utility_at_penalty_start = compute_daily_utility_hours(PENALTY_START_HOURS_PER_DAY)
    hard_penalty_hours = safe_hours - PENALTY_START_HOURS_PER_DAY
    return max(0.0, utility_at_penalty_start - (hard_penalty_hours * STRONG_PENALTY_PER_HOUR))


def get_recovery_penalty_multiplier(working_days: float, weekly_hours: float) -> float:
    safe_days = max(0.0, working_days)
    safe_weekly_hours = max(0.0, weekly_hours)

    if safe_weekly_hours <= BASELINE_WEEKLY_HOURS:
        return 1.0

    extra_days = max(0.0, safe_days - RECOVERY_PENALTY_START_DAYS)
    return max(0.0, 1.0 - (extra_days * RECOVERY_PENALTY_PER_EXTRA_DAY))


def compute_utility_hours(hours_per_day: float, working_days: float) -> float:
    """Convert a daily schedule into utility-weighted weekly hours."""
    safe_days = max(0.0, working_days)
    daily_utility_hours = compute_daily_utility_hours(hours_per_day)
    weekly_hours = clamp_hours_per_day(hours_per_day) * safe_days
    weekly_utility_hours = daily_utility_hours * safe_days
    return weekly_utility_hours * get_recovery_penalty_multiplier(safe_days, weekly_hours)


BASELINE_UTILITY_HOURS = compute_utility_hours(
    BASELINE_HOURS_PER_DAY,
    BASELINE_WORKING_DAYS,
)


def parse_salary(raw_value: str) -> float:
    cleaned_value = raw_value.replace(",", "").strip()
    return float(cleaned_value)


def format_currency(amount: float) -> str:
    return f"{amount:,.2f}"


@dataclass(frozen=True)
class CalculationResult:
    weekly_hours: float
    working_days: int
    hours_per_day: float
    daily_utility_hours: float
    utility_hours: float
    productivity_ratio: float
    straight_salary: float
    adjusted_salary: float


def calculate_salary(base_salary: float, hours_per_day: float, working_days: int) -> CalculationResult:
    normalized_hours_per_day = clamp_hours_per_day(hours_per_day)
    weekly_hours = normalized_hours_per_day * working_days
    daily_utility_hours = compute_daily_utility_hours(normalized_hours_per_day)
    recovery_penalty_multiplier = get_recovery_penalty_multiplier(working_days, weekly_hours)
    utility_hours = daily_utility_hours * working_days * recovery_penalty_multiplier
    straight_salary = base_salary * (weekly_hours / BASELINE_WEEKLY_HOURS)
    adjusted_salary = base_salary * (utility_hours / BASELINE_UTILITY_HOURS)

    productivity_ratio = 0.0
    if weekly_hours > 0:
        productivity_ratio = utility_hours / weekly_hours

    return CalculationResult(
        weekly_hours=weekly_hours,
        working_days=working_days,
        hours_per_day=normalized_hours_per_day,
        daily_utility_hours=daily_utility_hours,
        utility_hours=utility_hours,
        productivity_ratio=productivity_ratio,
        straight_salary=straight_salary,
        adjusted_salary=adjusted_salary,
    )


class SalaryCalculatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Salary Utility Calculator")
        self.resizable(False, False)
        self.configure(padx=18, pady=18)

        self.salary_var = tk.StringVar(value="5000")
        self.hours_var = tk.DoubleVar(value=BASELINE_HOURS_PER_DAY)
        self.days_var = tk.IntVar(value=BASELINE_WORKING_DAYS)
        self.status_var = tk.StringVar()

        self.weekly_hours_var = tk.StringVar()
        self.daily_utility_var = tk.StringVar()
        self.weekly_utility_var = tk.StringVar()
        self.productivity_var = tk.StringVar()
        self.straight_salary_var = tk.StringVar()
        self.adjusted_salary_var = tk.StringVar()
        self.curve_caption_var = tk.StringVar()

        self._build_layout()
        self._wire_events()
        self.refresh_results()

    def _build_layout(self) -> None:
        header = ttk.Label(
            self,
            text="Salary with declining utility of extra hours",
            font=("TkDefaultFont", 14, "bold"),
        )
        header.grid(row=0, column=0, sticky="w")

        intro = ttk.Label(
            self,
            text=(
                "Base salary assumes 5 working days and 40 hours per week. "
                "The output uses utility-weighted hours instead of raw hours."
            ),
            wraplength=520,
            justify="left",
        )
        intro.grid(row=1, column=0, pady=(6, 14), sticky="w")

        controls = ttk.LabelFrame(self, text="Inputs", padding=14)
        controls.grid(row=2, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Base salary").grid(row=0, column=0, sticky="w")
        salary_entry = ttk.Entry(controls, textvariable=self.salary_var, width=18)
        salary_entry.grid(row=0, column=1, sticky="w")
        ttk.Label(controls, text="same period for all outputs").grid(
            row=0,
            column=2,
            padx=(12, 0),
            sticky="w",
        )

        ttk.Label(controls, text="Working hours / day").grid(
            row=1,
            column=0,
            pady=(16, 0),
            sticky="w",
        )
        self.hours_scale = tk.Scale(
            controls,
            from_=MIN_HOURS_PER_DAY,
            to=MAX_HOURS_PER_DAY,
            orient="horizontal",
            resolution=0.5,
            variable=self.hours_var,
            showvalue=False,
            length=320,
        )
        self.hours_scale.grid(row=1, column=1, columnspan=2, pady=(12, 0), sticky="ew")

        self.hours_value_label = ttk.Label(controls, text="")
        self.hours_value_label.grid(row=2, column=1, sticky="w")

        ttk.Label(controls, text="Working days / week").grid(
            row=3,
            column=0,
            pady=(16, 0),
            sticky="w",
        )
        days_scale = tk.Scale(
            controls,
            from_=1,
            to=7,
            orient="horizontal",
            resolution=1,
            variable=self.days_var,
            showvalue=False,
            length=320,
        )
        days_scale.grid(row=3, column=1, columnspan=2, pady=(12, 0), sticky="ew")

        self.days_value_label = ttk.Label(controls, text="")
        self.days_value_label.grid(row=4, column=1, sticky="w")

        self.status_label = ttk.Label(
            controls,
            textvariable=self.status_var,
            foreground="#b45309",
            wraplength=460,
            justify="left",
        )
        self.status_label.grid(row=5, column=0, columnspan=3, pady=(12, 0), sticky="w")

        visualization = ttk.LabelFrame(self, text="Utility curve", padding=14)
        visualization.grid(row=3, column=0, pady=(14, 0), sticky="ew")

        self.curve_canvas = tk.Canvas(
            visualization,
            width=CURVE_CANVAS_WIDTH,
            height=CURVE_CANVAS_HEIGHT,
            background="#ffffff",
            highlightthickness=1,
            highlightbackground="#d1d5db",
        )
        self.curve_canvas.grid(row=0, column=0, sticky="ew")

        ttk.Label(
            visualization,
            textvariable=self.curve_caption_var,
            wraplength=CURVE_CANVAS_WIDTH,
            justify="left",
        ).grid(row=1, column=0, pady=(10, 0), sticky="w")

        output = ttk.LabelFrame(self, text="Results", padding=14)
        output.grid(row=4, column=0, pady=(14, 0), sticky="ew")
        output.columnconfigure(1, weight=1)

        self._add_result_row(output, 0, "Weekly hours", self.weekly_hours_var)
        self._add_result_row(output, 1, "Utility-weighted hours / day", self.daily_utility_var)
        self._add_result_row(output, 2, "Utility-weighted hours / week", self.weekly_utility_var)
        self._add_result_row(output, 3, "Productivity vs scheduled hours", self.productivity_var)
        self._add_result_row(output, 4, "Straight proportional salary", self.straight_salary_var)
        self._add_result_row(output, 5, "Utility-adjusted salary", self.adjusted_salary_var)

        assumptions = ttk.Label(
            self,
            text=(
                f"Assumptions: the daily-hours input ranges from {MIN_HOURS_PER_DAY:.0f} to "
                f"{MAX_HOURS_PER_DAY:.0f}; utility is fully linear up to {FULL_PRODUCTIVITY_HOURS_PER_DAY:.0f} hours/day; "
                f"hours between {FULL_PRODUCTIVITY_HOURS_PER_DAY:.0f} and {PENALTY_START_HOURS_PER_DAY:.0f} still add value but with diminishing returns; "
                f"hours above {PENALTY_START_HOURS_PER_DAY:.0f} are penalized; and working more than "
                f"{RECOVERY_PENALTY_START_DAYS:.0f} days/week reduces weekly utility only once the schedule exceeds "
                f"{BASELINE_WEEKLY_HOURS:.0f} hours/week."
            ),
            wraplength=520,
            justify="left",
        )
        assumptions.grid(row=5, column=0, pady=(14, 0), sticky="w")

    def _add_result_row(self, parent: ttk.LabelFrame, row: int, label: str, value_var: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, padx=(0, 18), pady=4, sticky="w")
        ttk.Label(parent, textvariable=value_var, font=("TkDefaultFont", 10, "bold")).grid(
            row=row,
            column=1,
            pady=4,
            sticky="e",
        )

    def _wire_events(self) -> None:
        self.salary_var.trace_add("write", self.refresh_results)
        self.hours_var.trace_add("write", self.refresh_results)
        self.days_var.trace_add("write", self.refresh_results)

    def _draw_curve(self, hours_per_day: float, working_days: int) -> None:
        canvas = self.curve_canvas
        canvas.delete("all")

        width = CURVE_CANVAS_WIDTH
        height = CURVE_CANVAS_HEIGHT
        left = 56
        right = 20
        top = 24
        bottom = 42
        plot_width = width - left - right
        plot_height = height - top - bottom
        x_axis_min = PLOT_MIN_HOURS_PER_DAY
        x_axis_max = PLOT_MAX_HOURS_PER_DAY
        x_axis_span = x_axis_max - x_axis_min
        y_axis_max = compute_daily_utility_hours(PENALTY_START_HOURS_PER_DAY) + 0.5

        def x_pos(hours: float) -> float:
            return left + ((hours - x_axis_min) / x_axis_span) * plot_width

        def y_pos(utility: float) -> float:
            return height - bottom - (utility / y_axis_max) * plot_height

        for tick in range(int(x_axis_min), int(x_axis_max) + 1):
            tick_value = float(tick)
            x = x_pos(tick_value)
            canvas.create_line(x, top, x, height - bottom, fill="#e5e7eb")
            canvas.create_text(x, height - bottom + 18, text=f"{tick_value:.0f}", fill="#4b5563")

        for tick in range(0, int(y_axis_max) + 1):
            y = y_pos(float(tick))
            canvas.create_line(left, y, width - right, y, fill="#e5e7eb")
            canvas.create_text(left - 16, y, text=str(tick), fill="#4b5563")

        canvas.create_line(left, top, left, height - bottom, fill="#111827", width=2)
        canvas.create_line(left, height - bottom, width - right, height - bottom, fill="#111827", width=2)
        canvas.create_text(left, top - 10, text="Utility-weighted hours / day", anchor="w", fill="#111827")
        canvas.create_text(width - right, height - 10, text="Working hours / day", anchor="e", fill="#111827")

        reference_lines = [
            (FULL_PRODUCTIVITY_HOURS_PER_DAY, "#16a34a", "diminishing returns start", top + 12),
            (PENALTY_START_HOURS_PER_DAY, "#f59e0b", "penalty starts", top + 28),
        ]
        for marker_hours, color, label, label_y in reference_lines:
            x = x_pos(marker_hours)
            canvas.create_line(x, top, x, height - bottom, fill=color, dash=(4, 4))
            canvas.create_text(x + 4, label_y, text=label, anchor="nw", fill=color)

        curve_points: list[float] = []
        point_count = int((x_axis_max - x_axis_min) * 10) + 1
        for step in range(point_count):
            curve_hours = x_axis_min + (step / 10)
            utility_hours = compute_daily_utility_hours(curve_hours)
            curve_points.extend((x_pos(curve_hours), y_pos(utility_hours)))

        canvas.create_line(*curve_points, fill="#2563eb", width=3)

        selected_utility = compute_daily_utility_hours(hours_per_day)
        selected_x = x_pos(min(max(hours_per_day, x_axis_min), x_axis_max))
        selected_y = y_pos(selected_utility)
        canvas.create_line(selected_x, selected_y, selected_x, height - bottom, fill="#dc2626", dash=(3, 3))
        canvas.create_oval(
            selected_x - 5,
            selected_y - 5,
            selected_x + 5,
            selected_y + 5,
            fill="#dc2626",
            outline="#ffffff",
            width=1,
        )
        label_anchor = "sw"
        label_x = selected_x + 8
        if selected_x > width - 180:
            label_anchor = "se"
            label_x = selected_x - 8
        canvas.create_text(
            label_x,
            selected_y - 8,
            text=f"current: {hours_per_day:.1f}h/day, {selected_utility:.2f} utility/day",
            anchor=label_anchor,
            fill="#dc2626",
        )

        weekly_hours = hours_per_day * working_days
        weekly_utility = selected_utility * working_days
        recovery_penalty_multiplier = get_recovery_penalty_multiplier(working_days, weekly_hours)
        penalized_weekly_utility = weekly_utility * recovery_penalty_multiplier
        self.curve_caption_var.set(
            f"The curve is linear through {FULL_PRODUCTIVITY_HOURS_PER_DAY:.0f} hours/day, rises more slowly until "
            f"{PENALTY_START_HOURS_PER_DAY:.0f} hours/day, and declines after that. "
            f"At {hours_per_day:.1f} hours/day across {working_days} days, that yields "
            f"{weekly_hours:.1f} scheduled hours/week and {penalized_weekly_utility:.1f} utility-weighted hours/week."
            + (
                f" Working more than {RECOVERY_PENALTY_START_DAYS:.0f} days/week applies a "
                f"{(1 - recovery_penalty_multiplier):.0%} recovery penalty."
                if working_days > RECOVERY_PENALTY_START_DAYS and weekly_hours > BASELINE_WEEKLY_HOURS
                else ""
            )
        )

    def refresh_results(self, *_args: object) -> None:
        hours_per_day = min(max(round(self.hours_var.get() * 2) / 2, MIN_HOURS_PER_DAY), MAX_HOURS_PER_DAY)
        working_days = max(1, min(7, int(round(self.days_var.get()))))

        if abs(self.hours_var.get() - hours_per_day) > 1e-9:
            self.hours_var.set(hours_per_day)
            return

        if self.days_var.get() != working_days:
            self.days_var.set(working_days)
            return

        self.hours_value_label.configure(text=f"{hours_per_day:.1f} hours per day")
        self.days_value_label.configure(text=f"{working_days} working days per week")
        self._draw_curve(hours_per_day, working_days)

        try:
            base_salary = parse_salary(self.salary_var.get())
            result = calculate_salary(base_salary, hours_per_day, working_days)
        except ValueError:
            self.status_var.set("Enter a valid numeric salary amount.")
            self._clear_results()
            return

        notes: list[str] = []
        if hours_per_day > PENALTY_START_HOURS_PER_DAY:
            notes.append(
                f"Hours above {PENALTY_START_HOURS_PER_DAY:.0f}/day reduce daily utility."
            )
        elif hours_per_day > FULL_PRODUCTIVITY_HOURS_PER_DAY:
            notes.append(
                f"Hours between {FULL_PRODUCTIVITY_HOURS_PER_DAY:.0f} and {PENALTY_START_HOURS_PER_DAY:.0f}/day still add utility, but with diminishing returns."
            )
        if working_days > RECOVERY_PENALTY_START_DAYS and result.weekly_hours > BASELINE_WEEKLY_HOURS:
            recovery_penalty = 1 - get_recovery_penalty_multiplier(working_days, result.weekly_hours)
            notes.append(
                f"Working more than {RECOVERY_PENALTY_START_DAYS:.0f} days/week adds a {recovery_penalty:.0%} recovery penalty once the schedule exceeds {BASELINE_WEEKLY_HOURS:.0f} hours/week."
            )
        self.status_var.set(" ".join(notes))

        self.weekly_hours_var.set(f"{result.weekly_hours:.2f}")
        self.daily_utility_var.set(f"{result.daily_utility_hours:.2f}")
        self.weekly_utility_var.set(f"{result.utility_hours:.2f}")
        self.productivity_var.set(f"{result.productivity_ratio:.1%}")
        self.straight_salary_var.set(format_currency(result.straight_salary))
        self.adjusted_salary_var.set(format_currency(result.adjusted_salary))

    def _clear_results(self) -> None:
        self.weekly_hours_var.set("n/a")
        self.daily_utility_var.set("n/a")
        self.weekly_utility_var.set("n/a")
        self.productivity_var.set("n/a")
        self.straight_salary_var.set("n/a")
        self.adjusted_salary_var.set("n/a")


def main() -> None:
    app = SalaryCalculatorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
