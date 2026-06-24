"""Mobile Android UI for v2ray-finder.

This Kivy entrypoint wraps the existing Python Pipeline in a touch-first UI.
It is intentionally dependency-light so Buildozer can package it into an APK.

Layer-3 xray probing is disabled in this mobile UI for the first Android
release because bundling and running the native xray binary on Android needs a
separate platform-specific implementation.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Optional

# The project uses a src/ layout. When packaged by Buildozer from the repository
# root, add src/ to sys.path so the mobile app can import v2ray_finder directly.
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from v2ray_finder import Pipeline, StopController


BG = (0.035, 0.047, 0.075, 1)
SURFACE = (0.075, 0.095, 0.145, 1)
SURFACE_2 = (0.105, 0.130, 0.195, 1)
ACCENT = (0.188, 0.529, 0.964, 1)
ACCENT_2 = (0.333, 0.831, 0.694, 1)
TEXT = (0.93, 0.96, 1.0, 1)
MUTED = (0.63, 0.70, 0.80, 1)
DANGER = (0.95, 0.27, 0.35, 1)
WARNING = (0.98, 0.69, 0.25, 1)
SUCCESS = (0.25, 0.85, 0.55, 1)


def _parse_int(value: str, default: int, minimum: int = 0, maximum: int = 5000) -> int:
    try:
        num = int(value.strip())
    except Exception:
        return default
    return max(minimum, min(maximum, num))


def _parse_float(value: str, default: float, minimum: float = 0.0, maximum: float = 120.0) -> float:
    try:
        num = float(value.strip())
    except Exception:
        return default
    return max(minimum, min(maximum, num))


class Card(BoxLayout):
    """Rounded dark container."""

    bg_color = ListProperty(SURFACE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.padding = kwargs.get("padding", dp(14))
        self.spacing = kwargs.get("spacing", dp(8))
        with self.canvas.before:
            Color(*self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(18)])
        self.bind(pos=self._update_rect, size=self._update_rect, bg_color=self._update_color)

    def _update_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _update_color(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(18)])


class GhostButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_color = kwargs.get("background_color", ACCENT)
        self.color = TEXT
        self.bold = True
        self.font_size = sp(14)
        self.size_hint_y = None
        self.height = dp(46)


class SmallLabel(Label):
    def __init__(self, text: str = "", color=MUTED, **kwargs):
        super().__init__(text=text, color=color, **kwargs)
        self.font_size = kwargs.get("font_size", sp(12))
        self.halign = kwargs.get("halign", "left")
        self.valign = kwargs.get("valign", "middle")
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))


class StatCard(Card):
    def __init__(self, title: str, value: str = "0", **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.size_hint_y = None
        self.height = dp(72)
        self.title_label = SmallLabel(title.upper(), color=MUTED, font_size=sp(10))
        self.value_label = Label(
            text=value,
            color=TEXT,
            bold=True,
            font_size=sp(22),
            halign="left",
            valign="middle",
        )
        self.value_label.bind(size=lambda *_: setattr(self.value_label, "text_size", self.value_label.size))
        self.add_widget(self.title_label)
        self.add_widget(self.value_label)

    def set_value(self, value: object) -> None:
        self.value_label.text = str(value)


class ResultRow(Card):
    def __init__(self, index: int, score, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.size_hint_y = None
        self.height = dp(112)
        self.bg_color = SURFACE_2
        grade = getattr(score, "grade", "?")
        total = getattr(score, "total", 0.0)
        protocol = getattr(score, "protocol", "?")
        latency = getattr(score, "latency_ms", None)
        config = getattr(score, "config", "")

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(28), spacing=dp(8))
        badge_color = SUCCESS if grade in ("A", "B") else WARNING if grade in ("C", "D") else DANGER
        grade_badge = Label(
            text=f"[b]{grade}[/b]",
            markup=True,
            color=(0.02, 0.03, 0.05, 1),
            size_hint_x=None,
            width=dp(38),
            font_size=sp(13),
        )
        with grade_badge.canvas.before:
            Color(*badge_color)
            grade_badge._rect = RoundedRectangle(pos=grade_badge.pos, size=grade_badge.size, radius=[dp(10)])
        grade_badge.bind(pos=lambda w, *_: setattr(w._rect, "pos", w.pos), size=lambda w, *_: setattr(w._rect, "size", w.size))

        title = Label(
            text=f"#{index}  {protocol.upper()}  •  score {total:.2f}",
            color=TEXT,
            bold=True,
            halign="left",
            valign="middle",
            font_size=sp(14),
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        latency_text = "n/a" if latency is None else f"{latency:.0f} ms"
        meta = Label(
            text=latency_text,
            color=MUTED,
            size_hint_x=None,
            width=dp(78),
            font_size=sp(12),
        )
        header.add_widget(grade_badge)
        header.add_widget(title)
        header.add_widget(meta)

        cfg_label = Label(
            text=config,
            color=MUTED,
            font_size=sp(11),
            halign="left",
            valign="top",
            shorten=True,
            shorten_from="right",
        )
        cfg_label.bind(size=lambda *_: setattr(cfg_label, "text_size", cfg_label.size))

        self.add_widget(header)
        self.add_widget(cfg_label)


class V2RayFinderMobileApp(App):
    title = "V2Ray Finder"

    def build(self):
        self.stop_controller: Optional[StopController] = None
        self.worker: Optional[threading.Thread] = None
        self.latest_result = None
        self.latest_configs: list[str] = []

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        with root.canvas.before:
            Color(*BG)
            root._rect = RoundedRectangle(pos=root.pos, size=root.size, radius=[0])
        root.bind(pos=lambda w, *_: setattr(w._rect, "pos", w.pos), size=lambda w, *_: setattr(w._rect, "size", w.size))

        header = Card(orientation="vertical", bg_color=(0.06, 0.09, 0.17, 1), size_hint_y=None, height=dp(118))
        header.add_widget(Label(text="[b]V2Ray Finder[/b]", markup=True, color=TEXT, font_size=sp(28), halign="left"))
        header.add_widget(SmallLabel("Find, validate, rank and export public V2Ray configs", color=MUTED, font_size=sp(13)))
        root.add_widget(header)

        controls = Card(orientation="vertical", bg_color=SURFACE, size_hint_y=None, height=dp(230))
        row1 = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(48))
        self.token_input = TextInput(
            hint_text="GitHub token optional",
            password=True,
            multiline=False,
            foreground_color=TEXT,
            hint_text_color=MUTED,
            background_color=(0.12, 0.15, 0.22, 1),
            cursor_color=ACCENT,
            padding=[dp(12), dp(12), dp(12), dp(12)],
        )
        row1.add_widget(self.token_input)
        controls.add_widget(row1)

        row2 = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(48))
        self.limit_input = TextInput(
            text="200",
            hint_text="Limit",
            multiline=False,
            input_filter="int",
            foreground_color=TEXT,
            hint_text_color=MUTED,
            background_color=(0.12, 0.15, 0.22, 1),
            padding=[dp(12), dp(12), dp(12), dp(12)],
        )
        self.timeout_input = TextInput(
            text="5",
            hint_text="Timeout",
            multiline=False,
            input_filter="float",
            foreground_color=TEXT,
            hint_text_color=MUTED,
            background_color=(0.12, 0.15, 0.22, 1),
            padding=[dp(12), dp(12), dp(12), dp(12)],
        )
        row2.add_widget(self.limit_input)
        row2.add_widget(self.timeout_input)
        controls.add_widget(row2)

        row3 = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(38))
        self.health_check = CheckBox(active=False, size_hint_x=None, width=dp(42), color=ACCENT)
        row3.add_widget(self.health_check)
        row3.add_widget(SmallLabel("TCP health check", color=TEXT, font_size=sp(13)))
        row3.add_widget(Widget())
        controls.add_widget(row3)

        btn_row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(50))
        self.start_btn = GhostButton(text="Start Scan", background_color=ACCENT)
        self.stop_btn = GhostButton(text="Stop", background_color=DANGER, disabled=True)
        self.copy_btn = GhostButton(text="Copy", background_color=SURFACE_2, disabled=True)
        self.save_btn = GhostButton(text="Save", background_color=SURFACE_2, disabled=True)
        self.start_btn.bind(on_release=lambda *_: self.start_scan())
        self.stop_btn.bind(on_release=lambda *_: self.stop_scan())
        self.copy_btn.bind(on_release=lambda *_: self.copy_results())
        self.save_btn.bind(on_release=lambda *_: self.save_results())
        btn_row.add_widget(self.start_btn)
        btn_row.add_widget(self.stop_btn)
        btn_row.add_widget(self.copy_btn)
        btn_row.add_widget(self.save_btn)
        controls.add_widget(btn_row)
        root.add_widget(controls)

        stats_grid = GridLayout(cols=4, spacing=dp(8), size_hint_y=None, height=dp(78))
        self.stat_fetched = StatCard("Fetched")
        self.stat_unique = StatCard("Unique")
        self.stat_healthy = StatCard("Healthy")
        self.stat_scored = StatCard("Scored")
        for card in (self.stat_fetched, self.stat_unique, self.stat_healthy, self.stat_scored):
            stats_grid.add_widget(card)
        root.add_widget(stats_grid)

        status_card = Card(orientation="vertical", bg_color=(0.055, 0.07, 0.105, 1), size_hint_y=None, height=dp(70))
        self.status_label = SmallLabel("Ready. Start with a low limit first on Android.", color=TEXT, font_size=sp(13))
        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(8))
        status_card.add_widget(self.status_label)
        status_card.add_widget(self.progress)
        root.add_widget(status_card)

        self.results_layout = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.results_layout.bind(minimum_height=self.results_layout.setter("height"))
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.results_layout)
        root.add_widget(scroll)

        return root

    def start_scan(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        self.results_layout.clear_widgets()
        self.latest_configs = []
        self.latest_result = None
        self.set_buttons(running=True)
        self.update_stats({"fetched": 0, "deduped": 0, "healthy": 0, "scored": 0})
        self.progress.value = 0
        self.status_label.text = "Starting pipeline..."

        self.stop_controller = StopController()
        limit = _parse_int(self.limit_input.text, default=200, minimum=1, maximum=5000)
        timeout = _parse_float(self.timeout_input.text, default=5.0, minimum=1.0, maximum=60.0)
        token = self.token_input.text.strip() or None
        check_health = bool(self.health_check.active)

        def progress_callback(stage: str, current: int, total: int, message: str) -> None:
            Clock.schedule_once(lambda _dt: self.on_progress(stage, current, total, message), 0)

        def run_pipeline() -> None:
            try:
                pipeline = Pipeline(
                    check_health=check_health,
                    check_http_probe=False,
                    check_google_204=False,
                    timeout=timeout,
                    limit=limit,
                    github_token=token,
                    fetch_concurrency=4,
                    health_batch_size=50,
                    max_total_configs=limit,
                )
                result = pipeline.run(
                    stop_event=self.stop_controller.event if self.stop_controller else None,
                    progress_callback=progress_callback,
                )
                Clock.schedule_once(lambda _dt: self.on_result(result), 0)
            except Exception as exc:  # noqa: BLE001 - show user-facing error
                Clock.schedule_once(lambda _dt: self.on_error(str(exc)), 0)

        self.worker = threading.Thread(target=run_pipeline, daemon=True)
        self.worker.start()

    def stop_scan(self) -> None:
        if self.stop_controller:
            self.stop_controller.stop()
        self.status_label.text = "Stopping at the next safe checkpoint..."
        self.stop_btn.disabled = True

    def on_progress(self, stage: str, current: int, total: int, message: str) -> None:
        if total > 0:
            self.progress.value = min(100, max(0, current / total * 100))
        self.status_label.text = f"{stage.upper()}: {message}"

    def on_result(self, result) -> None:
        self.latest_result = result
        self.latest_configs = result.top_configs if result.scores else result.configs
        self.update_stats(result.stats)
        self.populate_results(result)
        self.progress.value = 100
        stopped = self.stop_controller.is_set() if self.stop_controller else False
        label = "Stopped with partial results" if stopped else "Done"
        self.status_label.text = f"{label}. {len(self.latest_configs)} configs ready."
        self.set_buttons(running=False)
        has_results = bool(self.latest_configs)
        self.copy_btn.disabled = not has_results
        self.save_btn.disabled = not has_results

    def on_error(self, message: str) -> None:
        self.status_label.text = f"Error: {message}"
        self.set_buttons(running=False)

    def update_stats(self, stats: dict) -> None:
        self.stat_fetched.set_value(stats.get("fetched", 0))
        self.stat_unique.set_value(stats.get("deduped", 0))
        self.stat_healthy.set_value(stats.get("healthy", 0))
        self.stat_scored.set_value(stats.get("scored", 0))

    def populate_results(self, result) -> None:
        self.results_layout.clear_widgets()
        scores = result.scores[:100]
        if not scores:
            empty = Card(orientation="vertical", size_hint_y=None, height=dp(80))
            empty.add_widget(SmallLabel("No scored results. Try disabling health check or increasing the limit.", color=TEXT))
            self.results_layout.add_widget(empty)
            return
        for idx, score in enumerate(scores, 1):
            self.results_layout.add_widget(ResultRow(idx, score))

    def set_buttons(self, running: bool) -> None:
        self.start_btn.disabled = running
        self.stop_btn.disabled = not running
        self.copy_btn.disabled = running or not bool(self.latest_configs)
        self.save_btn.disabled = running or not bool(self.latest_configs)

    def copy_results(self) -> None:
        if not self.latest_configs:
            return
        Clipboard.copy("\n".join(self.latest_configs))
        self.status_label.text = f"Copied {len(self.latest_configs)} configs to clipboard."

    def save_results(self) -> None:
        if not self.latest_configs:
            return
        out_dir = Path(self.user_data_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "v2ray_servers.txt"
        out_file.write_text("\n".join(self.latest_configs) + "\n", encoding="utf-8")
        self.status_label.text = f"Saved {len(self.latest_configs)} configs to {out_file}"


if __name__ == "__main__":
    V2RayFinderMobileApp().run()
