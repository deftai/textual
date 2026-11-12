from __future__ import annotations

from textual._compositor import Compositor
from textual.app import App, ComposeResult
from textual.widgets import Input


class InputApp(App[None]):
    CSS = """
    #fixed { width: 12; }
    #auto { width: auto; }
    """

    def compose(self) -> ComposeResult:
        yield Input(id="fixed")
        yield Input("ab", id="auto")


async def test_typing_does_not_lay_out_the_screen(monkeypatch):
    """Typing into an Input whose size doesn't depend on its value shouldn't
    trigger a layout, which costs more the more widgets a screen has."""
    layouts = 0
    reflow = Compositor.reflow

    def counting_reflow(self, parent, size):
        nonlocal layouts
        layouts += 1
        return reflow(self, parent, size)

    monkeypatch.setattr(Compositor, "reflow", counting_reflow)

    async with InputApp().run_test() as pilot:
        input = pilot.app.query_one("#fixed", Input)
        input.focus()
        await pilot.pause()
        layouts = 0
        await pilot.press(*"abc")
        await pilot.pause()
        assert input.value == "abc"
        assert layouts == 0


async def test_typing_past_the_end_scrolls():
    """Without a layout, the Input still scrolls to keep the cursor in view, and
    back again when the value gets shorter."""
    async with InputApp().run_test() as pilot:
        input = pilot.app.query_one("#fixed", Input)
        input.focus()
        await pilot.press(*"abcdefghijklmnop")
        await pilot.pause()
        assert input.virtual_size.width == 17
        assert input.scroll_x == 17 - input.content_size.width
        await pilot.press(*["backspace"] * 12)
        await pilot.pause()
        assert input.value == "abcd"
        assert input.scroll_x == 0


async def test_typing_into_an_auto_width_input_resizes_it():
    async with InputApp().run_test() as pilot:
        input = pilot.app.query_one("#auto", Input)
        input.focus()
        await pilot.pause()
        width = input.size.width
        await pilot.press(*"cde")
        await pilot.pause()
        assert input.size.width > width
