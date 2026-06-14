"""QSS stylesheet for the log window.

Ported from legacy Logstyle.py QSSstyle().
"""


def log_window_style() -> str:
    return """
    #Log {
        background-color: qradialgradient(spread:reflect, cx:0.5, cy:0.5, radius:0.5,
            fx:0.653, fy:0.426136,
            stop:0.548023 rgba(30, 45, 89, 255),
            stop:1 rgba(0, 85, 149, 255));
    }

    QPushButton, QPushButton:enabled, QComboBox {
        font-family: "Gill Sans Extrabold", sans-serif;
        font-size: 16px;
        color: #BDC8E2;
        font-weight: bold;
        text-align: left center;
        padding-left: 25px;
        padding-top: 0px;
        border-style: solid;
        border-width: 2px;
        border-color: aqua;
        border-radius: 20px;
        background-color: #1E2D59;
        background-repeat: no-repeat;
        background-position: left center;
    }

    QComboBox::drop-down {
        border: none;
    }

    QPushButton:hover, QComboBox:hover {
        color: black;
        border-color: green;
        background-color: aqua;
    }

    QPushButton:disabled, QComboBox:disabled {
        color: black;
        border-color: green;
        background-color: aqua;
    }

    QPushButton:pressed, QPushButton:checked {
        color: black;
        border-color: green;
        background-color: aqua;
    }

    QTableView {
        color: rgb(0, 0, 0);
        border: 3px solid #C07010;
        gridline-color: #1E2D59;
        background-color: rgb(77, 176, 215);
        background-color: qlineargradient(spread:repeat, x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(4, 250, 246, 255),
            stop:1 rgba(255, 255, 255, 255));
        alternate-background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(221, 241, 252, 255),
            stop:1 rgba(255, 255, 255, 255));
        selection-background-color: rgb(130, 190, 100);
    }

    QHeaderView::section {
        background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(80, 80, 80, 255),
            stop:1 rgba(30, 30, 30, 255));
        color: rgb(240, 240, 240);
        padding-left: 4px;
        border: 1px solid #C07010;
        min-height: 30px;
    }

    QScrollBar:vertical {
        margin: 16px 0px 16px 0px;
        background-color: rgb(11, 54, 117);
        border: 0px;
        width: 14px;
    }

    QScrollBar::handle:vertical {
        background-color: rgba(59, 103, 168, 190);
        border-radius: 7px;
        width: 13px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: rgba(59, 103, 168, 220);
    }

    QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical {
        subcontrol-position: top;
        subcontrol-origin: margin;
        background-color: rgb(11, 54, 117);
        border: 1px solid rgb(11, 54, 117);
        height: 16px;
    }

    QScrollBar:horizontal {
        margin: 0px 16px 0px 16px;
        background-color: rgb(11, 54, 117);
        border: none;
        height: 14px;
    }

    QScrollBar::handle:horizontal {
        background-color: rgba(59, 103, 168, 190);
        border-radius: 7px;
        height: 14px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: rgba(59, 103, 168, 220);
    }

    QScrollBar::sub-line:horizontal, QScrollBar::add-line:horizontal {
        subcontrol-position: right;
        subcontrol-origin: margin;
        background-color: rgb(11, 54, 117);
        border: 1px solid rgb(11, 54, 117);
        height: 12px;
        width: 6px;
    }
    """
