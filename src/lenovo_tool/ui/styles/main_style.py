"""科技感数据监控大屏主题 - 深色科技蓝 + 霓虹青发光效果。

设计语言：
- 深空蓝渐变背景 (#050a14 -> #0a1628)
- 半透明科技面板 (rgba(10, 30, 60, 0.6))
- 霓虹青主色 (#00f0ff) 用于边框发光和标题
- 数据数字使用亮青色 (#00e5ff)
- 状态色：绿/橙/红
- 面板四角装饰线 + 顶部标题条
"""

# ---------------------------------------------------------------------------
# Color palette (used by both QSS and widget code)
# ---------------------------------------------------------------------------

# Backgrounds
BG_PRIMARY = "#050a14"
BG_SECONDARY = "#0a1628"
BG_PANEL = "rgba(8, 22, 48, 0.7)"
BG_PANEL_SOLID = "#0c1a30"
BG_CARD = "#0e1c35"
BG_CARD_HEADER = "#122347"
BG_INPUT = "#142848"
BG_KPI = "rgba(0, 60, 100, 0.3)"

# Borders
BORDER_SUBTLE = "#1a3a60"
BORDER_ACCENT = "#00d4ff"
BORDER_GLOW = "#00f0ff"

# Text
TEXT_PRIMARY = "#e8f4ff"
TEXT_SECONDARY = "#6a90b8"
TEXT_ACCENT = "#00e5ff"
TEXT_VALUE = "#00e5ff"
TEXT_LABEL = "#5a80a8"
TEXT_DIM = "#3a5a80"

# Status
STATUS_GOOD = "#00ff88"
STATUS_WARN = "#ffaa00"
STATUS_BAD = "#ff4455"

# Chart colors
CHART_GRID = "#1a2e50"
CHART_VOLTAGE = "#00e5ff"
CHART_CURRENT = "#ffaa00"
CHART_FCC = "#4488ff"
CHART_RM = "#aa55ff"
CHART_GREEN = "#00ff88"

# Glow / accent colors for dashboard style
GLOW_CYAN = "#00f0ff"
GLOW_BLUE = "#3388ff"
GLOW_GREEN = "#00ff88"
GLOW_PURPLE = "#aa55ff"
GLOW_ORANGE = "#ffaa00"
GLOW_RED = "#ff4455"

# ---------------------------------------------------------------------------
# Font size scale (design tokens)
# ---------------------------------------------------------------------------
FONT_XS = 8       # sub-labels, tick marks
FONT_SM = 9       # labels, small values
FONT_BASE = 11    # body text
FONT_MD = 13      # section titles, buttons
FONT_LG = 16      # card headers, prominent labels
FONT_XL = 22      # large value displays
FONT_HUGE = 32    # hero numbers

# Bar / gauge background colors (reused across widgets)
BAR_BG = "#1a2a3a"
BAR_RADIUS = 3


def global_stylesheet() -> str:
    """Return the application-wide QSS stylesheet (data dashboard style)."""
    return f"""
    /* ---- Base ---- */
    QMainWindow, QDialog {{
        background-color: {BG_PRIMARY};
    }}
    QWidget {{
        color: {TEXT_PRIMARY};
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-size: 13px;
    }}

    /* ---- Cards (QFrame with objectName="Card") ---- */
    QFrame#Card {{
        background-color: {BG_PANEL_SOLID};
        border: 1px solid {BORDER_ACCENT};
        border-radius: 4px;
    }}
    QFrame#CardHeader {{
        background-color: {BG_CARD_HEADER};
        border: none;
        border-bottom: 1px solid {BORDER_ACCENT};
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }}

    /* ---- Labels ---- */
    QLabel {{
        color: {TEXT_PRIMARY};
        background: transparent;
        border: none;
    }}
    QLabel#SectionTitle {{
        font-size: 15px;
        font-weight: bold;
        color: {TEXT_ACCENT};
        padding: 0px;
        letter-spacing: 2px;
    }}
    QLabel#ValueLabel {{
        font-size: 24px;
        font-weight: bold;
        color: {TEXT_VALUE};
        font-family: "Consolas", "Courier New", monospace;
        text-shadow: 0 0 8px rgba(0, 229, 255, 0.4);
    }}
    QLabel#UnitLabel {{
        font-size: 12px;
        color: {TEXT_SECONDARY};
    }}
    QLabel#FieldLabel {{
        font-size: 12px;
        color: {TEXT_LABEL};
    }}

    /* ---- Buttons ---- */
    QPushButton {{
        font-size: 13px;
        font-weight: 600;
        color: {TEXT_PRIMARY};
        background-color: {BG_INPUT};
        border: 1px solid {BORDER_ACCENT};
        border-radius: 4px;
        padding: 6px 16px;
        min-height: 28px;
    }}
    QPushButton:hover {{
        background-color: #1a3a5c;
        border-color: {BORDER_GLOW};
        color: {BORDER_GLOW};
    }}
    QPushButton:pressed {{
        background-color: #0a1a2e;
    }}
    QPushButton:disabled {{
        color: {TEXT_DIM};
        background-color: #0a1525;
        border-color: {BORDER_SUBTLE};
    }}
    QPushButton#PrimaryBtn {{
        background-color: {BORDER_ACCENT};
        color: {BG_PRIMARY};
        border: none;
        font-weight: bold;
    }}
    QPushButton#PrimaryBtn:hover {{
        background-color: {GLOW_CYAN};
    }}
    QPushButton#PrimaryBtn:disabled {{
        background-color: #0a2a3a;
        color: {TEXT_DIM};
    }}
    QPushButton#DangerBtn {{
        background-color: #8b1a24;
        color: white;
        border: 1px solid {STATUS_BAD};
    }}
    QPushButton#DangerBtn:hover {{
        background-color: #b02030;
    }}
    QPushButton:checked {{
        background-color: {BORDER_ACCENT};
        color: {BG_PRIMARY};
        border-color: {BORDER_GLOW};
    }}

    /* ---- LCD Number ---- */
    QLCDNumber {{
        color: {TEXT_VALUE};
        background: transparent;
        border: none;
    }}

    /* ---- Line Edit (read-only) ---- */
    QLineEdit {{
        background-color: {BG_INPUT};
        color: {TEXT_VALUE};
        border: 1px solid {BORDER_ACCENT};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 14px;
        font-weight: bold;
        font-family: "Consolas", "Courier New", monospace;
    }}
    QLineEdit:read-only {{
        background-color: {BG_INPUT};
    }}

    /* ---- Progress Bar ---- */
    QProgressBar {{
        background-color: {BG_INPUT};
        border: 1px solid {BORDER_ACCENT};
        border-radius: 2px;
        text-align: center;
        color: {TEXT_PRIMARY};
        font-size: 11px;
        min-height: 14px;
        max-height: 14px;
    }}
    QProgressBar::chunk {{
        border-radius: 2px;
    }}

    /* ---- Status Bar ---- */
    QStatusBar {{
        background-color: #030810;
        color: {TEXT_SECONDARY};
        font-size: 11px;
        border-top: 1px solid {BORDER_SUBTLE};
    }}

    /* ---- Combo Box ---- */
    QComboBox {{
        background-color: {BG_INPUT};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_ACCENT};
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 28px;
    }}
    QComboBox:hover {{
        border-color: {BORDER_GLOW};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_CARD};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_ACCENT};
        selection-background-color: {BORDER_ACCENT};
        selection-color: {BG_PRIMARY};
    }}

    /* ---- Table ---- */
    QTableWidget {{
        background-color: {BG_INPUT};
        alternate-background-color: {BG_CARD};
        color: {TEXT_PRIMARY};
        gridline-color: {BORDER_SUBTLE};
        border: 1px solid {BORDER_ACCENT};
        border-radius: 4px;
        selection-background-color: {BORDER_ACCENT};
        selection-color: {BG_PRIMARY};
    }}
    QHeaderView::section {{
        background-color: {BG_CARD_HEADER};
        color: {TEXT_ACCENT};
        font-weight: bold;
        font-size: 11px;
        padding: 4px 8px;
        border: none;
        border-right: 1px solid {BORDER_SUBTLE};
        border-bottom: 1px solid {BORDER_ACCENT};
    }}

    /* ---- ScrollBar ---- */
    QScrollBar:vertical {{
        background: {BG_PRIMARY};
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER_ACCENT};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {BORDER_GLOW};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: {BG_PRIMARY};
        height: 8px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {BORDER_ACCENT};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {BORDER_GLOW};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    """