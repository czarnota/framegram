from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont #type: ignore
from typing import Type, Sequence, Optional, Dict, Any, IO, Tuple, List
from pathlib import PurePath
from math import ceil

import argparse
import io
import json
import pkg_resources


DEFAULT_W=800
DEFAULT_H=600
SUPERSAMPLING=1


class Struct:
    def __init__(self,
                 name: str,
                 bits: Optional[int] = None,
                 children: Sequence['Struct'] = [],
                 value: Optional[List[Any]] = None,
                 important: Optional[bool]=False):
        self.children = children
        self.bits = bits
        self.name = name
        self.value = value
        self.important = important

    def num_bits(self) -> int:
        if self.bits is not None:
            return self.bits
        return sum(child.num_bits() for child in self.children)

    def child_shares(self) -> List[float]:
        total = self.num_bits()
        return [ float(child.num_bits() / total) for child in self.children ]

    def leafshares(self) -> List[float]:
        if not self.children:
            return [1.0]
        
        l: List[float] = []
        total = self.num_bits()
        for child in self.children:
            l.extend(share * child.num_bits() / total for share in child.leafshares())
        return l

    def leafvals(self) -> List[List[Any]]:
        if not self.children:
            return [self.value] if self.value else [[]]
        
        l = []
        for child in self.children:
            l.extend(child.leafvals())
        return l

    def leaforders(self, i: List[int] = None) -> List[int]:
        if i is None:
            i = [-1]
        else:
            i[0] += 1

        if not self.children:
            return [i[0]]
        
        l = []
        for child in self.children:
            numbers = child.leaforders(i)
            l.extend(numbers)

        return l

    @classmethod
    def from_dict(cls: Type['Struct'],
                  dic: Dict[str, Any]) -> 'Struct':
        value = dic["val"] if "val" in dic else None
        important = dic.get("important", None)

        if isinstance(dic["_"], int):
            return Struct(dic["name"], dic["_"], value=value, important=important)

        if not isinstance(dic["_"], list):
            raise ValueError('"_" must be either and int() or a list()')

        return Struct(dic["name"],
                      children=[ Struct.from_dict(x) for x in dic["_"] ],
                      value=value, important=important)

    @classmethod
    def from_sequence(cls, sequence: Sequence[Dict[str, Any]]) -> 'Struct':
        structs = [ Struct.from_dict(x) for x in sequence ] # type: ignore
        return Struct(name="root", children=structs)


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("-w", "--width", help="Output width", type=int,
                        default=DEFAULT_W)
    parser.add_argument("-h", "--height", help="Output image height", type=int,
                        default=DEFAULT_H)
    parser.add_argument("--wrap", help="Wrap", type=int)
    parser.add_argument("file", help="The file to render diagram from")
    return parser.parse_args()


def read_struct_from_file_path(path: str) -> Tuple[dict, Struct]:
    with open(path, "r") as file:
        js = json.load(file)
        if isinstance(js, list):
            return {}, Struct.from_sequence(js)
        return js.get("opts", {}), Struct.from_sequence(js.get("structs", []))


def output_filename(path: str) -> str:
    return str(PurePath(path).with_suffix('.png'))


def rect_size(rect: Tuple[float, float, float, float]):
    return rect[2] - rect[0], rect[3] - rect[1]


def rect_center(rect: Tuple[float, float, float, float]):
    w, h = rect_size(rect)
    return rect[0] + w/2, rect[1] + h/2


class BoundingBox:
    def __init__(self, bb: Tuple[float, float, float, float]):
        self.bb = bb

    def l(self):
        return self.bb[0]

    def t(self):
        return self.bb[1]

    def r(self):
        return self.bb[2]

    def b(self):
        return self.bb[3]

    def move(self, x: Optional[float] = None,
             y: Optional[float] = None):
        x = x if x is not None else 0
        y = y if y is not None else 0
        l, t, r, b = self.bb
        self.bb = (l + x, t + y, r + x, b + y)

    def resize(self, w: Optional[float] = None, h: Optional[float] = None):
        l, t, r, b = self.bb

        w = r - l if w is None else w
        h = b - t if h is None else h

        self.bb = (l, t, l + w, t + h)

    def height(self):
        return self.bb[3] - self.bb[1]

    def width(self):
        return self.r() - self.l()

    def advance_down(self):
        self.move(y = self.height())

    def stretch(self,
                l: Optional[float] = None,
                t: Optional[float] = None,
                r: Optional[float] = None,
                b: Optional[float] = None):
        l = 0 if l is None else l
        t = 0 if t is None else t
        r = 0 if r is None else r
        b = 0 if b is None else b
        ll, tt, rr, bb = self.bb
        self.bb = (ll + l, tt + t, rr + r, bb + b)

    def set(self,
            l: Optional[float] = None,
            t: Optional[float] = None,
            r: Optional[float] = None,
            b: Optional[float] = None):
        ll, tt, rr, bb = self.bb
        l = ll if l is None else l
        t = tt if t is None else t
        r = rr if r is None else r
        b = bb if b is None else b
        self.bb = (l, t, r, b)

    def cut_x(self, x):
        if not self.l() < x < self.r():
            return None

        return BoundingBox((self.l(), self.t(), x, self.b())), BoundingBox((x, self.t(), self.r(), self.b()))

    def partition_x(self, w, h) -> Sequence[BoundingBox]:
        box = BoundingBox(self.bb)

        while box.l() < 0:
            box.stretch(w, -h, w, -h)

        while box.l() >= w:
            box.stretch(-w, h, -w, h)

        parts = []

        while True:
            pairs = box.cut_x(w)
            if not pairs:
                parts.append(box)
                break
            parts.append(pairs[0])
            box = pairs[1]

            while box.l() >= w:
                box.stretch(-w, h, -w, h)

        return parts

class Renderer:
    COLORS = [
        "#ffb5a7",
        "#fcd5ce",
        "#f8edeb",
        "#f9dcc4",
        "#fec89a",
        "#f8edeb",
    ]

    OUTLINE = "#aaaaaa"

    TEXT_COLOR = "#444444"

    def __init__(self, width: float, height: float, wrap: Optional[int]=None,
                 font_size: Optional[float]=None, bits: bool=True):
        self.parent_share = 0.25
        self.i = 0
        self.bottom_bar_size = 10.0 * SUPERSAMPLING
        self.bounding_box = BoundingBox((0, 0, 0, 0))
        self.width = width * SUPERSAMPLING
        self.row_height = height * SUPERSAMPLING
        self.wrap = wrap
        self.font_size = font_size if font_size is not None else 0.05
        self.bits = bits

    def render(self, root: Struct, output_filename: str):
        wrap = root.num_bits()
        if self.wrap:
            wrap = self.wrap

        pages = root.num_bits() / wrap

        height = self.row_height * ceil(pages)

        image = Image.new("RGB", (self.width, height), (255, 255, 255))
        self.image = image

        self.bottom_bar_size = self.row_height * 0.1
        path = pkg_resources.resource_filename("framegram", "ttf/DejaVuSansMono.ttf")
        self.fnt = ImageFont.truetype(path, size=int(self.row_height * self.font_size))

        draw = ImageDraw.Draw(image)
        # draw.line((0, 0) + image.size, fill="red")

        self.bounding_box.resize(w = pages * self.width, h = self.row_height)

        if self.bits:
            bottom = -3 * self.bottom_bar_size
        else:
            bottom = -2 * self.bottom_bar_size

        self.bounding_box.stretch(b = bottom)
        self.bounding_box.stretch(t = -self.parent_share * self.bounding_box.bb[3] / (1 - self.parent_share))
        self._render_struct(draw, root)

        self.bounding_box.advance_down()
        self.bounding_box.resize(h = self.bottom_bar_size)
        self._render_vals(draw, root.leafvals(), root.leafshares(),
                          root.leaforders())

        self.bounding_box.advance_down()
        self._render_bytes(draw, root.num_bits())

        if self.bits:
            self.bounding_box.advance_down()
            self._render_bits(draw, root.num_bits(), modulo=8)

        self.bounding_box = BoundingBox((0, 0, 0, 0))
        self.bounding_box.resize(w = pages * self.width, h = self.row_height)
        self.bounding_box.stretch(b = bottom)
        self.bounding_box.stretch(t = -self.parent_share * self.bounding_box.bb[3] / (1 - self.parent_share))
        self._render_struct(draw, root, only_important=True, y_add=self.bottom_bar_size)

        image.resize((self.width / SUPERSAMPLING, height / SUPERSAMPLING), resample=Image.LANCZOS).save(output_filename)

    def _render_struct(self, draw: ImageDraw, struct: Struct,
                       rect: Optional[Tuple[float, float, float, float]] = None,
                       only_important: bool=False, y_add=0):
        rect = self.bounding_box.bb if rect is None else rect
        l, t, r, b = rect
        w, h = rect_size(rect)

        for percent, child in zip(struct.child_shares(), struct.children):
            r = l
            r += percent * w
            if only_important:
                if child.important:
                    self._render_rect(draw, (l, t + h * self.parent_share, r, b + y_add), fill=None, outline="#f33", width=2)
            else:
                self._render_rect(draw, (l, t + h * self.parent_share, r, b), fill=self.COLORS[self.i], outline="#aaaaaa")
            self.i = (self.i + 1) % len(self.COLORS)

            rect=(l, t + h * self.parent_share, r, b)
            self._render_struct(draw, child, rect, only_important=only_important, y_add=y_add)

            new_t = t + h * self.parent_share

            if len(child.children):
                text_rect = (l, new_t, r, b - (b - new_t) * (1 - self.parent_share))
            else:
                text_rect = rect

            if not only_important:
                self._render_centered_text(draw, text_rect, child.name,
                                           fill=self.TEXT_COLOR,
                                           font=self.fnt, mode="each")
            l = r

    def _render_vals(self, draw: ImageDraw, values: Sequence[Sequence[Any]],
                     shares: Sequence[float], leaforders: Sequence[int],
                     modulo: Optional[int] = None, colors: Sequence[str] = COLORS):
        rect = self.bounding_box.bb
        l, t, r, b = rect
        w, h = r - l, b - t

        for share, value, leaforder in zip(shares, values, leaforders):
            value_w = w * share
            tl = l

            if not value:
                r = l + value_w
                self._render_rect(draw, (l, t, r, b),
                               fill=colors[leaforder % len(colors)], outline="#aaaaaa")

            for val in value:
                r = l
                percent = 1 / len(value)
                r += percent * value_w

                self._render_rect(draw, (l, t, r, b),
                                  fill=colors[leaforder % len(colors)], outline="#aaaaaa")

                if modulo:
                    val = val % modulo
                self._render_centered_text(draw, (l, t, l + percent * value_w, t + h), f"{val}",
                          fill=self.TEXT_COLOR,
                          font=self.fnt, mode="largest")
                l = r
            l = tl + value_w


    def _render_bits(self, draw: ImageDraw, bits: int,
                     modulo: Optional[int] = None):
        return self._render_vals(draw,
                                 values=[range(bits)],
                                 shares=[1],
                                 leaforders=[0],
                                 modulo=modulo,
                                 colors=["#ffffff"])

    def _render_bytes(self, draw: ImageDraw, bytes: int):
        return self._render_bits(draw, int(bytes / 8))

    def _render_centered_text(self, draw: ImageDraw, rect: Tuple[float, float, float, float],
                              text: str, fill: str, font: ImageFont, parent_rect=None,
                              mode="largest"):
        bb = BoundingBox(rect).partition_x(self.width, self.row_height)

        if mode == "largest":
            bb = [max(bb, key=lambda x: x.width())]
        elif mode == "first":
            bb = bb[:1]

        for b in bb:
            pos = rect_center(b.bb)
            rw, rh = rect_size(b.bb)
            w, h = draw.textsize(text, font=font)

            if rw < 1:
                continue

            if w > rw:
                text = "\n".join(list(text))
                w, h = draw.textsize(text, font=font)

            draw.text((pos[0] - w/2, pos[1] - h/2), text, fill=fill, font=font)

    def _render_rect(self, draw: ImageDraw,
                     rect: Tuple[float, float, float, float],
                     fill: Optional[str],
                     outline: str,
                     **kwargs):

        bb = BoundingBox(rect)
        for bb in bb.partition_x(self.width, self.row_height):
            (w, h) = self.image.size
            r = (bb.bb[0], bb.bb[1], min(w - 1, bb.bb[2]), min(h - 1, bb.bb[3]))
            draw.rectangle(r, fill=fill, outline=outline, **kwargs)


def framegram(filename: str, width: int, height: int, wrap: Optional[int]=None,
              output: Optional[str]=None, font_size: Optional[float] = None):
    opts, root = read_struct_from_file_path(filename)

    width = opts.get("width", width)
    height = opts.get("height", height)
    wrap = opts.get("wrap", wrap)
    bits = opts.get("bits", True)

    renderer = Renderer(width, height, wrap=wrap, font_size=font_size, bits=bits)

    if output is None:
        output = output_filename(filename)

    renderer.render(root, output_filename=output)


def main():
    args = parse_args()
    framegram(args.file, args.width, args.height, wrap=args.wrap)


if __name__ == "__main__":
    main()
