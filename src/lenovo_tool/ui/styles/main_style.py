"""Global dark theme QSS and color constants for the application.

Design language:
- Dark blue-grey background (#0f1923)
- Card containers with subtle borders (#1b2838)
- Cyan/teal accent (#00d4aa) for primary actions
- Soft white text (#c8d6e5) for readability
- Green/yellow/red for status indicators
"""

# ---------------------------------------------------------------------------
# Color palette (used by both QSS and widget code)
# ---------------------------------------------------------------------------

BG_PRIMARY = "#0f1923"
BG_CARD = "#162230"
BG_CARD_HEADER = "#1b2d42"
BG_INPUT = "#1a2a3a"
BORDER_SUBTLE = "#2a3f55"
BORDER_ACCENT = "#00d4aa"

TEXT_PRIMARY = "#e0e8f0"
TEXT_SECONDARY = "#8899aa"
TEXT_ACCENT = "#00d4aa"
TEXT_VALUE = "#00e5c8"
TEXT_LABEL = "#7a8fa3"

STATUS_GOOD = "#00e676"
STATUS_WARN = "#ffab40"
STATUS_BAD = "#ff5252"

CHART_GRID = "#1a2a3a"
CHART_VOLTAGE = "#00e5c8"
CHART_CURRENT = "#ffab40"
CHART_FCC = "#448aff"
CHART_RM = "#e040fb"


def global_stylesheet() -> str:
    """Return the application-wide QSS stylesheet."""
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
        background-color: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 8px;
    }}
    QFrame#CardHeader {{
        background-color: {BG_CARD_HEADER};
        border: none;
        border-bottom: 1px solid {BORDER_SUBTLE};
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}

    /* ---- Labels ---- */
    QLabel {{
        color: {TEXT_PRIMARY};
        background: transparent;
        border: none;
    }}
    QLabel#SectionTitle {{
        font-size: 14px;
        font-weight: bold;
        color: {TEXT_ACCENT};
        padding: 0px;
    }}
    QLabel#ValueLabel {{
        font-size: 22px;
        font-weight: bold;
        color: {TEXT_VALUE};
        font-family: "Consolas", "Courier New", monospace;
    }}
    QLabel#UnitLabel {{
        font-size: 11px;
        color: {TEXT_SECONDARY};
    }}
    QLabel#FieldLabel {{
        font-size: 11px;
        color: {TEXT_LABEL};
    }}

    /* ---- Buttons ---- */
    QPushButton {{
        font-size: 13px;
        font-weight: 600;
        color: {TEXT_PRIMARY};
        background-color: {BG_INPUT};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 6px;
        padding: 6px 16px;
        min-height: 28px;
    }}
    QPushButton:hover {{
        background-color: #1e3348;
        border-color: {TEXT_ACCENT};
        color: {TEXT_ACCENT};
    }}
    QPushButton:pressed {{
        background-color: #0d1a26;
    }}
    QPushButton:disabled {{
        color: #4a5a6a;
        background-color: #0d1520;
        border-color: #1a2535;
    }}
    QPushButton#PrimaryBtn {{
        background-color: {TEXT_ACCENT};
        color: {BG_PRIMARY};
        border: none;
        font-weight: bold;
    }}
    QPushButton#PrimaryBtn:hover {{
        background-color: #00f0c0;
    }}
    QPushButton#PrimaryBtn:disabled {{
        background-color: #1a3a40;
        color: #4a6a6a;
    }}
    QPushButton#DangerBtn {{
        background-color: #c62828;
        color: white;
        border: none;
    }}
    QPushButton#DangerBtn:hover {{
        background-color: #e53935;
    }}
    QPushButton:checked {{
        background-color: {TEXT_ACCENT};
        color: {BG_PRIMARY};
        border-color: {TEXT_ACCENT};
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
        border: 1px solid {BORDER_SUBTLE};
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
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 4px;
        text-align: center;
        color: {TEXT_PRIMARY};
        font-size: 11px;
        min-height: 18px;
        max-height: 18px;
    }}
    QProgressBar::chunk {{
        border-radius: 3px;
    }}

    /* ---- Status Bar ---- */
    QStatusBar {{
        background-color: #0a1018;
        color: {TEXT_SECONDARY};
        font-size: 11px;
        border-top: 1px solid {BORDER_SUBTLE};
    }}

    /* ---- Combo Box ---- */
    QComboBox {{
        background-color: {BG_INPUT};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 28px;
    }}
    QComboBox:hover {{
        border-color: {TEXT_ACCENT};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_CARD};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        selection-background-color: {TEXT_ACCENT};
        selection-color: {BG_PRIMARY};
    }}

    /* ---- Table ---- */
    QTableWidget {{
        background-color: {BG_INPUT};
        alternate-background-color: {BG_CARD};
        color: {TEXT_PRIMARY};
        gridline-color: {BORDER_SUBTLE};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 4px;
        selection-background-color: {TEXT_ACCENT};
        selection-color: {BG_PRIMARY};
    }}
    QHeaderView::section {{
        background-color: {BG_CARD_HEADER};
        color: {TEXT_SECONDARY};
        font-weight: bold;
        font-size: 11px;
        padding: 4px 8px;
        border: none;
        border-right: 1px solid {BORDER_SUBTLE};
        border-bottom: 1px solid {BORDER_SUBTLE};
    }}

    /* ---- ScrollBar ---- */
    QScrollBar:vertical {{
        background: {BG_PRIMARY};
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER_SUBTLE};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {TEXT_ACCENT};
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
        background: {BORDER_SUBTLE};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {TEXT_ACCENT};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    """