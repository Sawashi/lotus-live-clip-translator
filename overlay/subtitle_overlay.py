"""Floating subtitle overlay window.

A transparent, always-on-top, frameless window that displays
subtitles over any application. Supports drag and click-through modes.
"""

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizeGrip
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPalette, QPen

logger = logging.getLogger(__name__)

MAX_LINES = 3
FADE_TIMEOUT = 5000  # ms


class SubtitleLabel(QLabel):
    """A single subtitle line with word wrap."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setContentsMargins(10, 2, 10, 2)


class SubtitleOverlay(QWidget):
    """Frameless, transparent overlay window for subtitles."""

    display_mode_changed = pyqtSignal(str)
    position_changed = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_mode = True
        self._dragging = False
        self._drag_pos = QPoint()
        self._subtitle_lines = []
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._fade_out)
        self._font_size = 24
        self._font_color = "#FFFFFF"
        self._bg_opacity = 0.7
        self._line_spacing = 1.2
        self._display_mode = "bilingual"
        self._init_ui()

    def _init_ui(self):
        """Initialize the overlay UI."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, not self._drag_mode)

        # Enable mouse tracking for drag
        self.setMouseTracking(True)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(int(self._line_spacing * 4))

        # Subtitle labels
        self._labels = []
        for i in range(MAX_LINES):
            label = SubtitleLabel(self)
            label.setVisible(False)
            layout.addWidget(label)
            self._labels.append(label)

        self.setLayout(layout)

        # Resize grip
        self._resize_grip = QSizeGrip(self)
        self._resize_grip.setStyleSheet("background: transparent;")

        # Default size
        self.resize(800, 200)

    def paintEvent(self, event):
        """Draw translucent background."""
        if self._bg_opacity > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            color = QColor(0, 0, 0, int(255 * self._bg_opacity))
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)

            if self._drag_mode:
                # Visible border in drag mode
                painter.setPen(QColor(100, 100, 100, 200))
                painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
                painter.setPen(Qt.PenStyle.NoPen)

                # Resize handle indicator (bottom-right corner)
                grip_rect = QRect(
                    self.width() - 20, self.height() - 20, 16, 16
                )
                painter.setPen(QPen(QColor(180, 180, 180, 200), 2))
                for i in range(3):
                    y = grip_rect.y() + 4 + i * 5
                    x = grip_rect.x() + 4 + i * 5
                    painter.drawLine(x, y, grip_rect.right() - 4, y)

            painter.drawRoundedRect(self.rect().adjusted(0, 0, 0, 0), 8, 8)
        super().paintEvent(event)

    def set_subtitles(self, original: str, translated: str):
        """Update displayed subtitles.

        Shows lines according to display mode.
        """
        if self._display_mode == "original":
            self._set_label_text(original, "")
        elif self._display_mode == "translated":
            self._set_label_text(translated, "")
        else:  # bilingual
            self._set_label_text(original, translated)

        # Reset fade timer
        self._fade_timer.start(FADE_TIMEOUT)

    def _set_label_text(self, line1: str, line2: str):
        """Set text on label widgets."""
        # Show line1
        self._labels[0].setText(line1 or "")
        self._labels[0].setVisible(bool(line1))

        if line2 and self._display_mode == "bilingual":
            self._labels[1].setText(line2)
            self._labels[1].setVisible(True)
            self._labels[2].setVisible(False)
        elif line1 and self._display_mode != "bilingual":
            # Use second label for empty line if needed
            self._labels[1].setVisible(False)
            self._labels[2].setVisible(False)
        else:
            # For short bilingual lines, stack both in first two labels
            if line2 and self._display_mode == "bilingual":
                self._labels[0].setText(line1)
                self._labels[1].setText(line2)
                self._labels[1].setVisible(True)
            self._labels[2].setVisible(False)

    def _fade_out(self):
        """Fade out subtitles after timeout."""
        self._fade_timer.stop()
        for label in self._labels:
            label.setText("")
            label.setVisible(False)

    def clear(self):
        """Clear all subtitles."""
        for label in self._labels:
            label.setText("")
            label.setVisible(False)
        self._fade_timer.stop()

    # ---- Display settings ----

    def set_font_size(self, size: int):
        """Update font size for all labels without resizing the window."""
        self._font_size = size
        font = QFont("Segoe UI", size)
        for label in self._labels:
            label.setFont(font)

    def set_font_color(self, color_hex: str):
        """Update text color."""
        self._font_color = color_hex
        color = QColor(color_hex)
        for label in self._labels:
            label.setStyleSheet(f"color: {color_hex};")

    def set_bg_opacity(self, opacity: float):
        """Set background opacity (0.0 to 1.0)."""
        self._bg_opacity = opacity
        self.update()

    def set_line_spacing(self, spacing: float):
        """Set line spacing multiplier."""
        self._line_spacing = spacing
        self.layout().setSpacing(int(spacing * 4))

    def set_display_mode(self, mode: str):
        """Set display mode: original, translated, bilingual."""
        self._display_mode = mode
        self.clear()

    # ---- Drag / Click-through mode ----

    def toggle_mode(self):
        """Toggle between drag mode and click-through mode."""
        self._drag_mode = not self._drag_mode
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            not self._drag_mode
        )
        if not self._drag_mode:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_drag_mode(self, enabled: bool):
        """Set drag mode explicitly."""
        self._drag_mode = enabled
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            not enabled
        )
        self._resize_grip.setVisible(enabled)
        if not enabled:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    @property
    def is_drag_mode(self) -> bool:
        return self._drag_mode

    def mouseDoubleClickEvent(self, event):
        """Double-click toggles drag/click-through mode."""
        self.toggle_mode()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        """Start drag."""
        if self._drag_mode and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Drag the overlay."""
        if self._dragging and self._drag_mode:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        """End drag and save position."""
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.position_changed.emit(self.x(), self.y())
            event.accept()

    def resizeEvent(self, event):
        """Handle resize."""
        super().resizeEvent(event)
        # Position size grip at bottom-right
        self._resize_grip.setGeometry(
            self.width() - 20, self.height() - 20, 20, 20
        )
        self.position_changed.emit(self.x(), self.y())

    # ---- Persistence ----

    def save_position(self) -> dict:
        """Return position and size dict for saving."""
        return {
            "overlay_x": self.x(),
            "overlay_y": self.y(),
            "overlay_width": self.width(),
            "overlay_height": self.height()
        }

    def restore_position(self, settings: dict):
        """Restore position and size from settings."""
        x = settings.get("overlay_x", 100)
        y = settings.get("overlay_y", 100)
        w = settings.get("overlay_width", 800)
        h = settings.get("overlay_height", 200)
        self.move(x, y)
        self.resize(w, h)

    def apply_settings(self, settings: dict):
        """Apply all visual settings from a settings dict.
        
        Only restores position/size on initial load (not on live settings changes).
        """
        if "font_size" in settings:
            self.set_font_size(settings["font_size"])
        if "font_color" in settings:
            self.set_font_color(settings["font_color"])
        if "overlay_opacity" in settings:
            self.set_bg_opacity(settings["overlay_opacity"])
        if "line_spacing" in settings:
            self.set_line_spacing(settings["line_spacing"])
        if "display_mode" in settings:
            self.set_display_mode(settings["display_mode"])
        # Only restore position/size if explicitly provided (initial load)
        if "overlay_x" in settings or "overlay_y" in settings:
            self.restore_position(settings)
