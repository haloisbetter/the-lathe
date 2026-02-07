"""TUI stylesheet constants."""

APP_CSS = """
Screen {
    background: $surface;
}

#header-bar {
    dock: top;
    height: 3;
    background: $primary-darken-2;
    color: $text;
    content-align: center middle;
    text-style: bold;
}

#status-bar {
    dock: bottom;
    height: 1;
    background: $primary-darken-3;
    color: $text-muted;
    padding: 0 1;
}

#runs-list {
    width: 1fr;
    min-width: 30;
    max-width: 50;
    border-right: solid $primary-darken-1;
}

#run-detail {
    width: 3fr;
    padding: 1 2;
    overflow-y: auto;
}

.run-item {
    padding: 0 1;
    height: 3;
}

.run-item:hover {
    background: $primary-darken-1;
}

.run-item.--highlight {
    background: $accent;
    color: $text;
}

.section-title {
    text-style: bold;
    color: $accent;
    margin-top: 1;
}

.field-label {
    text-style: bold;
    color: $secondary;
}

.violation-text {
    color: $error;
}

.success-text {
    color: $success;
}

.muted-text {
    color: $text-muted;
}

#console-health {
    height: auto;
    max-height: 8;
    border-bottom: solid $primary-darken-1;
    padding: 1;
}

#console-runs {
    height: 1fr;
    border-bottom: solid $primary-darken-1;
}

#console-stats {
    height: auto;
    max-height: 12;
    padding: 1;
}

.error-banner {
    background: $error;
    color: $text;
    text-align: center;
    height: 3;
    content-align: center middle;
    text-style: bold;
}

#replay-container {
    layout: horizontal;
    height: 1fr;
}

TabPane {
    padding: 0;
}
"""
