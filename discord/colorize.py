"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from typing import Optional, Type, Union

__all__ = ("Colors",)

class Colors:
    r"""Represents the class used for converting bbcode style strings to Discord ANSI Codeblocks that support colors.

    Usage
    ----------------

    from discord.colorize import Colors
    colors = Colors()
    message = colors.colorize('Hello World!', fg='green', 'bg'='red', 'bold'=True)


    All Colors
    ----------------

    Foreground -
    gray - 30
    red - 31
    green - 32
    yellow - 33
    blue - 34
    pink - 35
    cyan - 36
    white - 37

    Background -
    darkBlue - 40
    orange - 41
    gray - 46
    lightGray - 43
    lighterGray - 44
    indigo - 45
    white - 47

    Formatting -
    bold - 1
    underline - 4

    default - 0
    """

    class unknownColor(Exception):
        """The unknown color class, raised when the color that was given was not found.

        Args:
            Exception ([type]): [description]
        """

        def __init__(self, unknownColor: Union[int, str]):
            """Initializes the unknown color exception."""
            self.color = unknownColor

        def __str__(self):
            """Returns the string representation of the exception."""

            return f"Unknown color: {self.color}"

    def __init__(self):
        """Initializes the Colors class."""
        self.foregroundColors = {
            "gray": "30",
            "red": "31",
            "green": "32",
            "yellow": "33",
            "blue": "34",
            "pink": "35",
            "cyan": "36",
            "white": "37",
            "default": "0",
        }
        self.backgroundColors = {
            "darkBlue": "40",
            "orange": "41",
            "gray": "46",
            "lightGray": "43",
            "lighterGray": "44",
            "indigo": "45",
            "white": "47",
            "default": "0",
        }
        self.formatCodes = {"bold": "1", "underline": "4", "default": "0"}
        self.allFormatCodes = [1, 4]

    def returnColor(self, color: str, kind: str) -> int:
        """Returns the color code for the given color.

        Args:
            color (str): The color to return the code for.
            kind (str): The kind of color to return.

        Raises:
            self.unknownColor: Raised when the color is not found.

        Returns:
            int: The color code.
        """
        if type(color) is not str:
            return None
        if kind == "fg":
            try:
                return self.foregroundColors[color]
            except KeyError:
                raise self.unknownColor(color)
        elif kind == "bg":
            try:
                return self.backgroundColors[color]
            except KeyError:
                raise self.unknownColor(color)

    def colorize(
        self,
        text: str,
        bg: Union[str, int] = 0,
        fg: Union[str, int] = 0,
        bold: bool = 0,
        underline: bool = 0,
    ) -> str:
        """Returns a string with the ANSI color codes for the given parameters.

        Args:
            text (str): The text to colorize.
            bg (Union[str, int], optional): The background color to use. Defaults to no background.
            fg (Union[str, int], optional): The foreground color to use. Defaults to no foreground.
            bold (bool, optional): Whether or not to use bold. Defaults to no bold.
            underline (bool, optional): Whether or not to use underline. Defaults to no underline.

        Returns:
            str: The colorized string.
        """

        if bg is not None:
            if type(bg) is str:
                bg = self.returnColor(bg, "bg")
            elif type(bg) is int:
                if str(bg) not in self.backgroundColors.values():
                    raise self.unknownColor(bg)
            else:
                return TypeError("bg must be a string or an integer.")
        if fg is not None:
            if type(fg) is str:
                fg = self.returnColor(fg, "fg")
            elif type(fg) is int:
                if str(fg) not in self.foregroundColors.values():
                    raise self.unknownColor(fg)
            else:
                raise TypeError("fg must be a string or an integer.")
        if bold:
            bold = self.formatCodes["bold"]
        if underline:
            underline = self.formatCodes["underline"]
        return (
            f"[{bg};{fg};{bold};{underline}m{text}".replace("0;", "")
            .replace("0m", "m")
            .replace(";m", "m")
            + "[0m"
        )
