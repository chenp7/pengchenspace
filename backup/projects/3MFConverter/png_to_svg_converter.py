from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class SvgColorLayer:
    hex_color: str
    pixel_count: int
    region_count: int


@dataclass(frozen=True)
class SvgConversionResult:
    width: int
    height: int
    colors_requested: int
    colors_used: int
    layers: tuple[SvgColorLayer, ...]


def _hex_color(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _quantize_image(image: Image.Image, color_count: int) -> tuple[np.ndarray, dict[int, tuple[int, int, int]], np.ndarray]:
    rgba = image.convert("RGBA")
    alpha = np.array(rgba.getchannel("A"))
    rgb = rgba.convert("RGB")
    quantized = rgb.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

    indexed = np.array(quantized)
    raw_palette = quantized.getpalette()
    palette = {
        index: (
            raw_palette[index * 3],
            raw_palette[index * 3 + 1],
            raw_palette[index * 3 + 2],
        )
        for index in set(indexed.flatten().tolist())
    }
    return indexed, palette, alpha


def _connected_components(mask: np.ndarray) -> Iterable[tuple[np.ndarray, int, int]]:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)

    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue

            queue = deque([(x, y)])
            visited[y, x] = True
            pixels: list[tuple[int, int]] = []
            min_x = max_x = x
            min_y = max_y = y

            while queue:
                px, py = queue.popleft()
                pixels.append((px, py))
                min_x = min(min_x, px)
                max_x = max(max_x, px)
                min_y = min(min_y, py)
                max_y = max(max_y, py)

                for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                    if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((nx, ny))

            component = np.zeros((max_y - min_y + 1, max_x - min_x + 1), dtype=bool)
            for px, py in pixels:
                component[py - min_y, px - min_x] = True
            yield component, min_x, min_y


def _build_boundary_edges(mask: np.ndarray) -> dict[tuple[int, int], list[tuple[int, int]]]:
    height, width = mask.shape
    outgoing: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)

    def add_edge(start: tuple[int, int], end: tuple[int, int]) -> None:
        outgoing[start].append(end)

    for y in range(height):
        for x in range(width):
            if not mask[y, x]:
                continue
            if y == 0 or not mask[y - 1, x]:
                add_edge((x, y), (x + 1, y))
            if x == width - 1 or not mask[y, x + 1]:
                add_edge((x + 1, y), (x + 1, y + 1))
            if y == height - 1 or not mask[y + 1, x]:
                add_edge((x + 1, y + 1), (x, y + 1))
            if x == 0 or not mask[y, x - 1]:
                add_edge((x, y + 1), (x, y))

    return outgoing


def _simplify_loop(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if len(points) <= 2:
        return points

    simplified: list[tuple[int, int]] = []
    total = len(points)
    for index, point in enumerate(points):
        prev_point = points[index - 1]
        next_point = points[(index + 1) % total]
        dx1 = point[0] - prev_point[0]
        dy1 = point[1] - prev_point[1]
        dx2 = next_point[0] - point[0]
        dy2 = next_point[1] - point[1]
        if dx1 * dy2 == dy1 * dx2:
            continue
        simplified.append(point)
    return simplified or points


def _trace_loops(mask: np.ndarray, offset_x: int, offset_y: int) -> list[list[tuple[int, int]]]:
    outgoing = _build_boundary_edges(mask)
    used: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    loops: list[list[tuple[int, int]]] = []

    for start, ends in outgoing.items():
        for end in ends:
            edge = (start, end)
            if edge in used:
                continue

            loop = [start]
            current_start = start
            current_end = end

            while True:
                used.add((current_start, current_end))
                loop.append(current_end)

                if current_end == start:
                    break

                next_candidates = outgoing[current_end]
                next_end = next(edge_end for edge_end in next_candidates if (current_end, edge_end) not in used)
                current_start, current_end = current_end, next_end

            absolute_loop = [(x + offset_x, y + offset_y) for x, y in loop[:-1]]
            loops.append(_simplify_loop(absolute_loop))

    return loops


def _path_from_loops(loops: list[list[tuple[int, int]]]) -> str:
    commands: list[str] = []
    for loop in loops:
        if len(loop) < 3:
            continue
        commands.append(f"M {loop[0][0]} {loop[0][1]}")
        for point in loop[1:]:
            commands.append(f"L {point[0]} {point[1]}")
        commands.append("Z")
    return " ".join(commands)


def convert_png_to_layered_svg(
    input_path: str | Path,
    output_path: str | Path,
    *,
    color_count: int = 4,
    alpha_threshold: int = 16,
    min_region_pixels: int = 8,
) -> SvgConversionResult:
    if color_count < 2 or color_count > 16:
        raise ValueError("Color count must be between 2 and 16.")
    if min_region_pixels < 1:
        raise ValueError("Minimum region size must be at least 1 pixel.")

    source_image = Image.open(input_path)
    indexed, palette, alpha = _quantize_image(source_image, color_count)
    active_mask = alpha >= alpha_threshold
    height, width = indexed.shape

    root = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "version": "1.1",
            "viewBox": f"0 0 {width} {height}",
            "width": str(width),
            "height": str(height),
        },
    )
    ET.SubElement(
        root,
        "desc",
    ).text = "Quantized PNG converted into color-separated vector regions for CAD sketch import."

    layer_summary: list[SvgColorLayer] = []
    pixel_counts = Counter(indexed[active_mask].tolist())

    for palette_index, pixel_count in pixel_counts.most_common():
        color_mask = (indexed == palette_index) & active_mask
        loops: list[list[tuple[int, int]]] = []
        region_count = 0

        for component, offset_x, offset_y in _connected_components(color_mask):
            area = int(component.sum())
            if area < min_region_pixels:
                continue
            loops.extend(_trace_loops(component, offset_x, offset_y))
            region_count += 1

        if not loops:
            continue

        rgb = palette[palette_index]
        hex_color = _hex_color(rgb)
        group = ET.SubElement(
            root,
            "g",
            {
                "id": f"layer-{len(layer_summary) + 1}",
                "data-color": hex_color,
                "data-pixels": str(pixel_count),
                "data-regions": str(region_count),
            },
        )
        ET.SubElement(
            group,
            "path",
            {
                "d": _path_from_loops(loops),
                "fill": hex_color,
                "fill-rule": "evenodd",
                "stroke": hex_color,
                "stroke-width": "0.25",
                "vector-effect": "non-scaling-stroke",
            },
        )
        layer_summary.append(
            SvgColorLayer(
                hex_color=hex_color,
                pixel_count=int(pixel_count),
                region_count=region_count,
            )
        )

    if not layer_summary:
        raise ValueError("No visible color regions found. Check transparency or source image content.")

    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    return SvgConversionResult(
        width=width,
        height=height,
        colors_requested=color_count,
        colors_used=len(layer_summary),
        layers=tuple(layer_summary),
    )
