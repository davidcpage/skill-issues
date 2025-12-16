"""Issues Board TUI - Kanban board using Textual."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Footer, Header, Static

from . import store


# Priority badges with colors
PRIORITY_BADGES = {
    0: ("[bold red]P0[/]", "critical"),
    1: ("[bold yellow]P1[/]", "high"),
    2: ("[white]P2[/]", "medium"),
    3: ("[dim]P3[/]", "low"),
    4: ("[dim]P4[/]", "backlog"),
}


class IssueCard(Static):
    """A card representing an issue in the Kanban board."""

    def __init__(self, issue: dict, is_selected: bool = False) -> None:
        super().__init__()
        self.issue = issue
        self.is_selected = is_selected

    def compose(self) -> ComposeResult:
        issue = self.issue
        issue_id = issue.get("id", "???")
        title = issue.get("title", "Untitled")
        priority = issue.get("priority", 2)
        issue_type = issue.get("issue_type", issue.get("type", "task"))

        # Truncate title if too long
        if len(title) > 35:
            title = title[:32] + "..."

        # Get priority badge
        badge, _ = PRIORITY_BADGES.get(priority, ("[white]P?[/]", "unknown"))

        # Type indicator
        type_icon = {"bug": "🐛", "feature": "✨", "task": "📋"}.get(issue_type, "📋")

        # Build card content
        content = f"{badge} {type_icon} [bold]{issue_id}[/]\n{title}"

        # Show dependencies if any
        deps = issue.get("depends_on", [])
        if deps and issue.get("status") == "open":
            content += f"\n[dim]depends on: {', '.join(deps[:3])}"
            if len(deps) > 3:
                content += f" +{len(deps) - 3}"
            content += "[/]"

        yield Static(content)

    def update_selection(self, selected: bool) -> None:
        """Update the visual selection state."""
        self.is_selected = selected
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")


class KanbanColumn(Vertical):
    """A column in the Kanban board."""

    def __init__(self, title: str, column_id: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.column_title = title
        self.column_id = column_id
        self.issues: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Static(f"[bold]{self.column_title}[/] ({len(self.issues)})", classes="column-header")
        with ScrollableContainer(classes="column-content"):
            for issue in self.issues:
                yield IssueCard(issue)

    def set_issues(self, issues: list[dict]) -> None:
        """Set the issues for this column."""
        self.issues = issues


class IssueDetail(Static):
    """Widget showing the details of a selected issue."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__("", *args, **kwargs)
        self.issue: dict | None = None

    def show_issue(self, issue: dict) -> None:
        """Update display with the given issue."""
        self.issue = issue
        self.update(self._render_issue(issue))

    def _render_issue(self, issue: dict) -> str:
        """Render an issue as rich text."""
        lines = []

        # Header
        issue_id = issue.get("id", "???")
        title = issue.get("title", "Untitled")
        status = issue.get("status", "open")
        priority = issue.get("priority", 2)
        issue_type = issue.get("issue_type", issue.get("type", "task"))

        badge, priority_name = PRIORITY_BADGES.get(priority, ("[white]P?[/]", "unknown"))
        status_color = "green" if status == "closed" else "cyan"

        lines.append(f"[bold cyan]{issue_id}[/] - [bold]{title}[/]")
        lines.append(f"{badge} {priority_name} | [{status_color}]{status}[/] | {issue_type}")
        lines.append("")

        # Description
        desc = issue.get("description", "")
        if desc:
            lines.append("[bold]Description[/]")
            lines.append(desc)
            lines.append("")

        # Labels
        labels = issue.get("labels", [])
        if labels:
            label_str = " ".join(f"[magenta]{l}[/]" for l in labels)
            lines.append(f"[bold]Labels[/] {label_str}")
            lines.append("")

        # Dependencies
        deps = issue.get("depends_on", [])
        if deps:
            lines.append(f"[bold yellow]Depends On[/] {', '.join(deps)}")
            lines.append("")

        # Notes
        notes = issue.get("notes", [])
        if notes:
            lines.append("[bold]Notes[/]")
            for note in notes:
                ts = note.get("ts", "")[:10]
                content = note.get("content", "")
                lines.append(f"  [dim]{ts}[/] {content}")
            lines.append("")

        # Closed info
        if status == "closed":
            closed_at = issue.get("closed_at", "")[:10]
            reason = issue.get("closed_reason", "")
            lines.append(f"[bold green]Closed[/] {closed_at}")
            if reason:
                lines.append(f"  {reason}")
            lines.append("")

        # Timestamps
        created = issue.get("created", "")[:10]
        lines.append(f"[dim]Created: {created}[/]")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear the detail view."""
        self.issue = None
        self.update("[dim]Select an issue to view details[/]")


class IssuesBoardApp(App):
    """A TUI Kanban board for issues."""

    CSS = """
    #board-container {
        height: 1fr;
    }

    #columns-container {
        width: 70%;
        height: 100%;
    }

    #detail-panel {
        width: 30%;
        border: solid blue;
        padding: 1 2;
        overflow-y: auto;
    }

    KanbanColumn {
        width: 1fr;
        border: solid $secondary;
        margin: 0 1;
    }

    .column-header {
        text-align: center;
        padding: 1;
        background: $surface;
    }

    .column-content {
        height: 1fr;
        padding: 1;
    }

    IssueCard {
        margin: 1 0;
        padding: 1;
        border: solid $primary;
        background: $surface;
    }

    IssueCard.selected {
        border: double $accent;
        background: $accent 20%;
    }

    #ready-column {
        border: solid green;
    }

    #ready-column .column-header {
        background: green 30%;
    }

    #blocked-column {
        border: solid yellow;
    }

    #blocked-column .column-header {
        background: yellow 30%;
    }

    #closed-column {
        border: solid $secondary;
    }

    #closed-column .column-header {
        background: $secondary 30%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("j", "next_issue", "Down"),
        Binding("k", "prev_issue", "Up"),
        Binding("h", "prev_column", "Left"),
        Binding("l", "next_column", "Right"),
        Binding("g", "go_top", "Top"),
        Binding("G", "go_bottom", "Bottom"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.all_issues: dict[str, dict] = {}
        self.columns: list[str] = ["ready", "blocked", "closed"]
        self.column_issues: dict[str, list[dict]] = {"ready": [], "blocked": [], "closed": []}
        self.current_column = 0
        self.current_index: dict[str, int] = {"ready": 0, "blocked": 0, "closed": 0}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="board-container"):
            with Horizontal(id="columns-container"):
                yield KanbanColumn("Ready", "ready", id="ready-column")
                yield KanbanColumn("Blocked", "blocked", id="blocked-column")
                yield KanbanColumn("Closed", "closed", id="closed-column")
            yield IssueDetail(id="detail-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Load issues and populate columns on start."""
        self._load_issues()
        self._update_columns()
        self._update_selection()

    def _load_issues(self) -> None:
        """Load issues from store and categorize them."""
        self.all_issues = store.load_issues()

        # Categorize issues
        open_issues = store.filter_open(self.all_issues)
        open_ids = set(open_issues.keys())

        ready = []
        blocked = []
        closed = []

        for issue_id, issue in sorted(self.all_issues.items(), key=lambda x: (x[1].get("priority", 2), x[0])):
            if issue["status"] == "closed":
                closed.append(issue)
            else:
                deps = set(issue.get("depends_on", []))
                unsatisfied_deps = deps & open_ids
                if unsatisfied_deps:
                    blocked.append(issue)
                else:
                    ready.append(issue)

        self.column_issues = {"ready": ready, "blocked": blocked, "closed": closed}

        # Reset indices if needed
        for col in self.columns:
            max_idx = len(self.column_issues[col]) - 1
            if self.current_index[col] > max_idx:
                self.current_index[col] = max(0, max_idx)

    def _update_columns(self) -> None:
        """Update the visual column widgets."""
        column_map = {
            "ready": "#ready-column",
            "blocked": "#blocked-column",
            "closed": "#closed-column",
        }

        for col_id, selector in column_map.items():
            column = self.query_one(selector, KanbanColumn)
            issues = self.column_issues[col_id]
            column.set_issues(issues)

            # Update header with count
            header = column.query_one(".column-header", Static)
            title = {"ready": "Ready", "blocked": "Blocked", "closed": "Closed"}[col_id]
            header.update(f"[bold]{title}[/] ({len(issues)})")

            # Rebuild cards
            content = column.query_one(".column-content", ScrollableContainer)
            content.remove_children()
            for i, issue in enumerate(issues):
                card = IssueCard(issue)
                content.mount(card)

    def _update_selection(self) -> None:
        """Update visual selection across all columns."""
        column_map = {
            "ready": "#ready-column",
            "blocked": "#blocked-column",
            "closed": "#closed-column",
        }

        for col_idx, col_id in enumerate(self.columns):
            column = self.query_one(column_map[col_id], KanbanColumn)
            cards = list(column.query(IssueCard))
            current_idx = self.current_index[col_id]

            for i, card in enumerate(cards):
                is_selected = (col_idx == self.current_column) and (i == current_idx)
                card.update_selection(is_selected)

        # Update detail panel
        self._update_detail()

    def _update_detail(self) -> None:
        """Update the detail panel with current selection."""
        detail = self.query_one("#detail-panel", IssueDetail)
        col_id = self.columns[self.current_column]
        issues = self.column_issues[col_id]
        idx = self.current_index[col_id]

        if issues and 0 <= idx < len(issues):
            detail.show_issue(issues[idx])
        else:
            detail.clear()

    def _get_current_column_issues(self) -> list[dict]:
        """Get issues in the current column."""
        col_id = self.columns[self.current_column]
        return self.column_issues[col_id]

    def action_next_issue(self) -> None:
        """Move to next issue in current column (vim j)."""
        col_id = self.columns[self.current_column]
        issues = self.column_issues[col_id]
        if issues:
            self.current_index[col_id] = min(self.current_index[col_id] + 1, len(issues) - 1)
            self._update_selection()

    def action_prev_issue(self) -> None:
        """Move to previous issue in current column (vim k)."""
        col_id = self.columns[self.current_column]
        issues = self.column_issues[col_id]
        if issues:
            self.current_index[col_id] = max(self.current_index[col_id] - 1, 0)
            self._update_selection()

    def action_next_column(self) -> None:
        """Move to next column (vim l)."""
        self.current_column = min(self.current_column + 1, len(self.columns) - 1)
        self._update_selection()

    def action_prev_column(self) -> None:
        """Move to previous column (vim h)."""
        self.current_column = max(self.current_column - 1, 0)
        self._update_selection()

    def action_go_top(self) -> None:
        """Go to first issue in current column (vim g)."""
        col_id = self.columns[self.current_column]
        self.current_index[col_id] = 0
        self._update_selection()

    def action_go_bottom(self) -> None:
        """Go to last issue in current column (vim G)."""
        col_id = self.columns[self.current_column]
        issues = self.column_issues[col_id]
        if issues:
            self.current_index[col_id] = len(issues) - 1
            self._update_selection()

    def action_refresh(self) -> None:
        """Reload issues from disk."""
        self._load_issues()
        self._update_columns()
        self._update_selection()


def run_app() -> None:
    """Run the issues board TUI app."""
    app = IssuesBoardApp()
    app.run()


if __name__ == "__main__":
    run_app()
