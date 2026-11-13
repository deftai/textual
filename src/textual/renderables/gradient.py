from __future__ import annotations

from math import cos, pi, sin
from typing import Sequence

from rich.color import Color as RichColor
from rich.console import Console, ConsoleOptions, RenderResult
from rich.segment import Segment
from rich.style import Style

from textual.color import Color, Gradient


_CACHE_SIZE = 16384
_rich_colors: dict[tuple[int, int, int], RichColor] = {}
_styles: dict[tuple[tuple[int, int, int], tuple[int, int, int]], Style] = {}


def _style(color: tuple[int, int, int], bgcolor: tuple[int, int, int]) -> Style:
    """The style of a half block, shared between frames.

    An animated gradient draws every cell anew many times a second, and the same colors come
    round again: one Style for each pair means Rich and Textual's own caches of styles find
    it, rather than each frame making, hashing and combining thousands of new ones.
    """
    key = (color, bgcolor)
    style = _styles.get(key)
    if style is None:
        if len(_styles) >= _CACHE_SIZE:
            _styles.clear()
        style = _styles[key] = Style.from_color(_rich_color(color), _rich_color(bgcolor))
    return style


def _rich_color(rgb: tuple[int, int, int]) -> RichColor:
    rich_color = _rich_colors.get(rgb)
    if rich_color is None:
        if len(_rich_colors) >= _CACHE_SIZE:
            _rich_colors.clear()
        rich_color = _rich_colors[rgb] = Color(*rgb).rich_color
    return rich_color


class VerticalGradient:
    """Draw a vertical gradient."""

    def __init__(self, color1: str, color2: str) -> None:
        self._color1 = Color.parse(color1)
        self._color2 = Color.parse(color2)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        width = options.max_width
        height = options.height or options.max_height
        color1 = self._color1
        color2 = self._color2
        default_color = Color(0, 0, 0).rich_color
        from_color = Style.from_color
        blend = color1.blend
        rich_color1 = color1.rich_color
        for y in range(height):
            line_color = from_color(
                default_color,
                (
                    blend(color2, y / (height - 1)).rich_color
                    if height > 1
                    else rich_color1
                ),
            )
            yield Segment(f"{width * ' '}\n", line_color)


class LinearGradient:
    """Render a linear gradient with a rotation.

    Args:
        angle: Angle of rotation in degrees.
        stops: List of stop consisting of pairs of offset (between 0 and 1) and color.

    """

    def __init__(
        self, angle: float, stops: Sequence[tuple[float, Color | str]]
    ) -> None:
        self.angle = angle
        self._stops = [
            (stop, Color.parse(color) if isinstance(color, str) else color)
            for stop, color in stops
        ]
        self._color_gradient = Gradient(*self._stops)
        self._rgbs = [(color.r, color.g, color.b) for color in self._color_gradient.colors]

    def _color_at(self, position: float) -> tuple[int, int, int]:
        """The gradient's color at a position, as `Gradient.get_color` blends it, in RGB."""
        rgbs = self._rgbs
        if position <= 0:
            return rgbs[0]
        if position >= 1:
            return rgbs[-1]
        color_position = position * (len(rgbs) - 1)
        color_index = int(color_position)
        factor = color_position % 1
        r1, g1, b1 = rgbs[color_index]
        if factor <= 0:
            return r1, g1, b1
        r2, g2, b2 = rgbs[color_index + 1]
        return (
            int(r1 + (r2 - r1) * factor),
            int(g1 + (g2 - g1) * factor),
            int(b1 + (b2 - b1) * factor),
        )

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        width = options.max_width
        height = options.height or options.max_height

        angle_radians = -self.angle * pi / 180.0
        sin_angle = sin(angle_radians)
        cos_angle = cos(angle_radians)

        center_x = width / 2
        center_y = height

        new_line = Segment.line()

        _Segment = Segment
        get_color = self._color_at

        for line_y in range(height):
            point_y = float(line_y) * 2 - center_y
            point_x = 0 - center_x

            x1 = (center_x + (point_x * cos_angle - point_y * sin_angle)) / width
            x2 = (
                center_x + (point_x * cos_angle - (point_y + 1.0) * sin_angle)
            ) / width
            point_x = width - center_x
            end_x1 = (center_x + (point_x * cos_angle - point_y * sin_angle)) / width
            delta_x = (end_x1 - x1) / width

            if abs(delta_x) < 0.0001:
                # Special case for verticals
                yield _Segment("▀" * width, _style(get_color(x1), get_color(x2)))

            else:
                yield from [
                    _Segment(
                        "▀",
                        _style(get_color(x1 + x * delta_x), get_color(x2 + x * delta_x)),
                    )
                    for x in range(width)
                ]

            yield new_line


if __name__ == "__main__":
    from rich import print

    COLORS = [
        "#881177",
        "#aa3355",
        "#cc6666",
        "#ee9944",
        "#eedd00",
        "#99dd55",
        "#44dd88",
        "#22ccbb",
        "#00bbcc",
        "#0099cc",
        "#3366bb",
        "#663399",
    ]

    stops = [(i / (len(COLORS) - 1), Color.parse(c)) for i, c in enumerate(COLORS)]

    print(LinearGradient(25, stops))

    from time import time

    from textual.app import App, ComposeResult
    from textual.widgets import Static

    class GradientApp(App):
        CSS = """
        Screen {
            background: transparent;
            align: center middle;
        }

        Static {
            padding: 2 4;
            background: $panel;
            width: 50;
        }

        """

        def compose(self) -> ComposeResult:
            yield Static("Gradients are fast now :-) ")

        def render(self):
            return LinearGradient(time() * 90, stops)

        def on_mount(self) -> None:
            self.set_interval(1 / 30, self.refresh)

    app = GradientApp()
    app.run()
