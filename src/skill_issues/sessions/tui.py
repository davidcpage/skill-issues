"""Sessions TUI - Interactive session viewer using Textual."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, ListItem, ListView, Static

from skill_issues import get_user_prefix
from . import store


class SessionListItem(ListItem):
    """A list item representing a session."""

    def __init__(self, session: dict) -> None:
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        s = self.session
        # Format: date | topic (counts)
        stats = []
        learnings = len(s.get("learnings", []))
        questions = len(s.get("open_questions", []))
        actions = len(s.get("next_actions", []))
        if learnings:
            stats.append(f"{learnings}L")
        if questions:
            stats.append(f"{questions}Q")
        if actions:
            stats.append(f"{actions}A")
        stat_str = f" ({', '.join(stats)})" if stats else ""

        date = s.get("date", "????-??-??")
        topic = s.get("topic", "untitled")
        # Truncate topic if too long
        if len(topic) > 35:
            topic = topic[:32] + "..."

        yield Static(f"[dim]{date}[/] {topic}{stat_str}")


class SessionDetail(Static):
    """Widget showing the details of a selected session."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__("", *args, **kwargs)
        self.session: dict | None = None

    def show_session(self, session: dict) -> None:
        """Update display with the given session."""
        self.session = session
        self.update(self._render_session(session))

    def _render_session(self, s: dict) -> str:
        """Render a session as rich text."""
        lines = []

        # Header
        sid = s.get("id", "???")
        date = s.get("date", "????-??-??")
        topic = s.get("topic", "untitled")
        lines.append(f"[bold cyan]{sid}[/] - [bold]{topic}[/]")
        lines.append(f"[dim]{date}[/]")
        lines.append("")

        # Learnings
        learnings = s.get("learnings", [])
        if learnings:
            lines.append("[bold green]Learnings[/]")
            for learning in learnings:
                lines.append(f"  - {learning}")
            lines.append("")

        # Open Questions
        questions = s.get("open_questions", [])
        if questions:
            lines.append("[bold yellow]Open Questions[/]")
            for q in questions:
                lines.append(f"  - {q}")
            lines.append("")

        # Next Actions
        actions = s.get("next_actions", [])
        if actions:
            lines.append("[bold magenta]Next Actions[/]")
            for a in actions:
                lines.append(f"  - {a}")
            lines.append("")

        # Issues Worked
        issues = s.get("issues_worked", [])
        if issues:
            lines.append(f"[bold blue]Issues Worked[/] {', '.join(issues)}")
            lines.append("")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear the detail view."""
        self.session = None
        self.update("[dim]Select a session to view details[/]")


class SessionsApp(App):
    """A TUI for browsing session history."""

    CSS = """
    #user-bar {
        height: 1;
        padding: 0 1;
        background: $surface;
    }

    #session-list {
        width: 40%;
        border: solid green;
        padding: 0 1;
    }

    #session-detail {
        width: 60%;
        border: solid blue;
        padding: 1 2;
        overflow-y: auto;
    }

    #main-container {
        height: 1fr;
    }

    #search-box {
        height: auto;
        display: none;
        padding: 0 1;
    }

    #search-box.visible {
        display: block;
    }

    #search-input {
        width: 100%;
    }

    ListView {
        height: 100%;
    }

    ListView > ListItem {
        padding: 0 1;
    }

    ListView > ListItem.--highlight {
        background: $accent;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("j", "cursor_down", "Down"),
        Binding("k", "cursor_up", "Up"),
        Binding("g", "go_top", "Top"),
        Binding("G", "go_bottom", "Bottom"),
        Binding("/", "search", "Search"),
        Binding("escape", "clear_search", "Clear", show=False),
        Binding("h", "prev_tab", "Prev User", show=False),
        Binding("l", "next_tab", "Next User", show=False),
    ]

    def __init__(self, sessions: list[dict] | None = None) -> None:
        super().__init__()
        # Load sessions if not provided (most recent first)
        if sessions is None:
            self.all_sessions = list(reversed(store.load_sessions()))
        else:
            self.all_sessions = list(reversed(sessions))

        # Get current user and build user list
        self.current_user, _ = get_user_prefix()
        self.users = self._get_user_list()
        self.selected_user: str | None = self.current_user  # None means "All"

        # Apply user filter
        self.sessions = self._filter_by_selected_user()
        self.filtered_sessions = self.sessions
        self.search_term = ""
        self._ready_for_tab_changes = False  # Skip tab activations until ready

    def _get_user_list(self) -> list[str]:
        """Get list of users, ordered: current user first, others alphabetically."""
        users_set: set[str] = set()
        for s in self.all_sessions:
            user = s.get("user")
            if user:
                users_set.add(user)
            else:
                # Parse from ID for legacy sessions
                parsed_prefix, _ = store.parse_session_id(s.get("id", ""))
                if parsed_prefix:
                    users_set.add(parsed_prefix)

        # Order: current user first, then others alphabetically
        others = sorted(u for u in users_set if u != self.current_user)
        if self.current_user in users_set:
            return [self.current_user] + others
        return others

    def _filter_by_selected_user(self) -> list[dict]:
        """Filter sessions by currently selected user tab."""
        if self.selected_user is None:  # "All" tab
            return self.all_sessions
        return store.filter_by_user(self.all_sessions, self.selected_user)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(self._render_user_bar(), id="user-bar")
        with Vertical(id="search-box"):
            yield Input(placeholder="Filter by topic...", id="search-input")
        with Horizontal(id="main-container"):
            with Vertical(id="session-list"):
                yield ListView(
                    *[SessionListItem(s) for s in self.filtered_sessions],
                    id="list-view"
                )
            yield SessionDetail(id="session-detail")
        yield Footer()

    def _render_user_bar(self) -> str:
        """Render the user selection bar."""
        parts = []
        for user in self.users:
            if user == self.selected_user:
                parts.append(f"[reverse] {user} [/]")
            else:
                parts.append(f" {user} ")
        # Add "All" option
        if self.selected_user is None:
            parts.append("[reverse] All [/]")
        else:
            parts.append(" All ")
        return " │ ".join(parts) + "  [dim](h/l to switch)[/]"

    def _update_user_bar(self) -> None:
        """Update the user bar display."""
        user_bar = self.query_one("#user-bar", Static)
        user_bar.update(self._render_user_bar())

    def on_mount(self) -> None:
        """Focus the list and show first session when app starts."""
        list_view = self.query_one("#list-view", ListView)
        list_view.focus()
        # Select first item if available
        if self.filtered_sessions:
            list_view.index = 0
            self._show_selected_session()
        # Force refresh to ensure items are rendered
        list_view.refresh()
        # Now ready for user-initiated tab changes
        self._ready_for_tab_changes = True

    def _switch_user(self, new_user: str | None) -> None:
        """Switch to a different user filter."""
        if new_user == self.selected_user:
            return

        self.selected_user = new_user
        self._update_user_bar()

        # Re-filter and update display
        self.sessions = self._filter_by_selected_user()
        self.search_term = ""
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        self._apply_filter()

        # Focus back on list
        list_view = self.query_one("#list-view", ListView)
        list_view.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle session selection."""
        self._show_selected_session()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle highlight changes (cursor movement)."""
        self._show_selected_session()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self.search_term = event.value
            self._apply_filter()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in search input - focus back to list."""
        if event.input.id == "search-input":
            search_box = self.query_one("#search-box")
            search_box.remove_class("visible")
            list_view = self.query_one("#list-view", ListView)
            list_view.focus()

    def _show_selected_session(self) -> None:
        """Update detail view with currently highlighted session."""
        list_view = self.query_one("#list-view", ListView)
        detail = self.query_one("#session-detail", SessionDetail)

        if list_view.highlighted_child is not None:
            item = list_view.highlighted_child
            if isinstance(item, SessionListItem):
                detail.show_session(item.session)
        else:
            detail.clear()

    def _apply_filter(self) -> None:
        """Apply the current search filter to the session list."""
        if self.search_term:
            term = self.search_term.lower()
            self.filtered_sessions = [
                s for s in self.sessions
                if term in s.get("topic", "").lower()
            ]
        else:
            self.filtered_sessions = self.sessions

        # Rebuild the list view
        list_view = self.query_one("#list-view", ListView)
        list_view.remove_children()
        for s in self.filtered_sessions:
            list_view.append(SessionListItem(s))

        # Update detail view
        if self.filtered_sessions:
            list_view.index = 0
            self._show_selected_session()
        else:
            detail = self.query_one("#session-detail", SessionDetail)
            detail.clear()

    def action_cursor_down(self) -> None:
        """Move cursor down (vim j)."""
        list_view = self.query_one("#list-view", ListView)
        list_view.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up (vim k)."""
        list_view = self.query_one("#list-view", ListView)
        list_view.action_cursor_up()

    def action_go_top(self) -> None:
        """Go to first item (vim g)."""
        list_view = self.query_one("#list-view", ListView)
        if self.filtered_sessions:
            list_view.index = 0

    def action_go_bottom(self) -> None:
        """Go to last item (vim G)."""
        list_view = self.query_one("#list-view", ListView)
        if self.filtered_sessions:
            list_view.index = len(self.filtered_sessions) - 1

    def action_search(self) -> None:
        """Open search/filter input."""
        search_box = self.query_one("#search-box")
        search_box.add_class("visible")
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    def action_clear_search(self) -> None:
        """Clear search filter and hide search box."""
        search_box = self.query_one("#search-box")
        search_input = self.query_one("#search-input", Input)

        if search_box.has_class("visible"):
            search_box.remove_class("visible")
            search_input.value = ""
            self.search_term = ""
            self._apply_filter()
            list_view = self.query_one("#list-view", ListView)
            list_view.focus()

    def action_prev_tab(self) -> None:
        """Move to previous user (vim h)."""
        # Build full list: users + None (All)
        options: list[str | None] = list(self.users) + [None]
        if self.selected_user in options:
            idx = options.index(self.selected_user)
            new_idx = (idx - 1) % len(options)
            self._switch_user(options[new_idx])
        elif options:
            self._switch_user(options[0])

    def action_next_tab(self) -> None:
        """Move to next user (vim l)."""
        # Build full list: users + None (All)
        options: list[str | None] = list(self.users) + [None]
        if self.selected_user in options:
            idx = options.index(self.selected_user)
            new_idx = (idx + 1) % len(options)
            self._switch_user(options[new_idx])
        elif options:
            self._switch_user(options[0])


def run_app(sessions: list[dict] | None = None) -> None:
    """Run the sessions TUI app."""
    app = SessionsApp(sessions=sessions)
    app.run()


if __name__ == "__main__":
    run_app()
