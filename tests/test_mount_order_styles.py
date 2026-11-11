"""Mounting only restyles the siblings whose position pseudo classes changed."""

from __future__ import annotations

import pytest

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.css.stylesheet import Stylesheet
from textual.widgets import Label


class Order(App[None]):
    CSS = """
    Label { color: white; }
    Label:first-child { background: red; }
    Label:last-child { background: blue; }
    Label:first-child:last-child { background: green; }
    .inner:last-child Label { color: yellow; }
    Label.striped:odd { color: red; }
    Label.striped:even { color: blue; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="list"):
            yield Label("a", id="a")
            yield Label("b", id="b")
            yield Label("c", id="c")


async def _settle(pilot) -> None:
    await pilot.pause()
    await pilot.pause()


def _count_applies(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    applied: list[object] = []
    original = Stylesheet.apply

    def apply(self, node, **kwargs):  # type: ignore[no-untyped-def]
        if node.id:
            applied.append(node.id)
        return original(self, node, **kwargs)

    monkeypatch.setattr(Stylesheet, "apply", apply)
    return applied


async def test_appending_leaves_siblings_in_the_same_position_alone(monkeypatch):
    app = Order()
    async with app.run_test() as pilot:
        await _settle(pilot)
        applied = _count_applies(monkeypatch)
        await app.query_one("#list").mount(Label("d", id="d"))
        await _settle(pilot)
        assert "b" not in applied  # Still neither first nor last.
        assert "a" not in applied  # Still first.
        assert "c" in applied  # No longer last.
        assert "d" in applied


async def test_appending_updates_the_styles_that_depend_on_position():
    app = Order()
    async with app.run_test() as pilot:
        await _settle(pilot)
        c = app.query_one("#c")
        assert c.styles.background.rgb == (0, 0, 255)
        new = Label("d", id="d")
        await app.query_one("#list").mount(new)
        await _settle(pilot)
        assert c.styles.background.a == 0
        assert new.styles.background.rgb == (0, 0, 255)
        assert app.query_one("#a").styles.background.rgb == (255, 0, 0)


async def test_inserting_at_the_start_updates_the_old_first_child():
    app = Order()
    async with app.run_test() as pilot:
        await _settle(pilot)
        a = app.query_one("#a")
        new = Label("z", id="z")
        await app.query_one("#list").mount(new, before=0)
        await _settle(pilot)
        assert a.styles.background.a == 0
        assert new.styles.background.rgb == (255, 0, 0)


async def test_inserting_changes_odd_and_even_of_those_after():
    app = Order()
    async with app.run_test() as pilot:
        await _settle(pilot)
        b = app.query_one("#b")
        b.add_class("striped")
        await _settle(pilot)
        was = b.styles.color
        await app.query_one("#list").mount(Label("z", id="z"), before=0)
        await _settle(pilot)
        assert b.styles.color != was


async def test_a_restyle_since_the_last_mount_counts_as_the_starting_point():
    """A child is compared with its styles as applied, not its state at the last mount."""
    app = Order()
    async with app.run_test() as pilot:
        await _settle(pilot)
        c = app.query_one("#c")
        await app.query_one("#list").mount(Label("d", id="d"))
        await _settle(pilot)
        assert c.styles.background.a == 0  # c lost last-child.
        await app.query_one("#d").remove()
        await _settle(pilot)
        c.update_node_styles()  # Something restyles c while it's last again.
        await _settle(pilot)
        assert c.styles.background.rgb == (0, 0, 255)
        await app.query_one("#list").mount(Label("e", id="e"))
        await _settle(pilot)
        assert c.styles.background.a == 0  # And it must notice losing it again.


async def test_a_change_of_position_restyles_what_is_beneath():
    class Nested(App[None]):
        CSS = """
        .inner:last-child { color: yellow; }
        .inner:last-child Label { color: yellow; }
        .inner Label { color: white; }
        """

        def compose(self) -> ComposeResult:
            with Vertical(id="list"):
                with Vertical(classes="inner", id="one"):
                    yield Label("x", id="x")

    app = Nested()
    async with app.run_test() as pilot:
        await _settle(pilot)
        x = app.query_one("#x")
        assert x.styles.color.rgb == (255, 255, 0)
        await app.query_one("#list").mount(Vertical(classes="inner", id="two"))
        await _settle(pilot)
        assert x.styles.color.rgb == (255, 255, 255)
