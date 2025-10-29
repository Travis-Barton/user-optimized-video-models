"""Simple MVP pipeline for personalizing a variable-filled video template.

This script reads a JSON template that describes video layers with
human-readable variables such as ``[VAR_NAME]``. At runtime it resolves those
variables using CLI overrides (or template defaults), generates text overlays,
produces a playful synthesized audio ping derived from the viewer's name, and
renders a short mp4 clip alongside a caption file.

Usage
-----
python scripts/personalize_video.py templates/castle_run_template.json \
    --var VAR_NAME=Jordan --var VAR_LOCATION="the Moon" --var VAR_TEAM=Wolves \
    --output outputs/jordan_castle_run.mp4
"""

from __future__ import annotations

import argparse
import json
import math
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.editor import ColorClip, CompositeAudioClip, CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont

VARIABLE_PATTERN = re.compile(r"\[(VAR_[A-Z0-9_]+)\]")
DEFAULT_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


@dataclass
class TemplateLayer:
    template: str
    start: float
    end: float
    position: str
    font_size: int
    color: str


@dataclass
class CaptionTrack:
    template: str
    start: float
    end: float


@dataclass
class AudioSegment:
    template: str
    start: float
    generator: str


@dataclass
class VideoTemplate:
    name: str
    description: str
    variables: Dict[str, Dict[str, str]]
    resolution: Tuple[int, int]
    duration: float
    background_color: str
    fps: int
    text_layers: List[TemplateLayer]
    captions: List[CaptionTrack]
    audio_segments: List[AudioSegment]


class TemplateParseError(RuntimeError):
    """Raised when required template fields are missing."""


# ---------------------------------------------------------------------------
# Template parsing helpers
# ---------------------------------------------------------------------------

def load_template(path: Path) -> VideoTemplate:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    try:
        video_meta = payload["video"]
    except KeyError as exc:  # pragma: no cover - guardrail
        raise TemplateParseError("Template missing 'video' block") from exc

    layers = [
        TemplateLayer(
            template=layer["template"],
            start=float(layer["start"]),
            end=float(layer["end"]),
            position=layer.get("position", "center"),
            font_size=int(layer.get("font_size", 56)),
            color=layer.get("color", "#FFFFFF"),
        )
        for layer in payload.get("text_layers", [])
    ]

    captions = [
        CaptionTrack(
            template=cap["template"],
            start=float(cap["start"]),
            end=float(cap["end"]),
        )
        for cap in payload.get("caption_tracks", [])
    ]

    audio_segments = [
        AudioSegment(
            template=seg["template"],
            start=float(seg["start"]),
            generator=seg.get("generator", "tone_from_text"),
        )
        for seg in payload.get("audio_segments", [])
    ]

    resolution = tuple(video_meta.get("resolution", [1280, 720]))
    duration = float(video_meta.get("duration", 6.0))
    fps = int(video_meta.get("fps", 24))

    return VideoTemplate(
        name=payload.get("template_name", path.stem),
        description=payload.get("description", ""),
        variables=payload.get("variables", {}),
        resolution=(int(resolution[0]), int(resolution[1])),
        duration=duration,
        background_color=video_meta.get("background_color", "#000000"),
        fps=fps,
        text_layers=layers,
        captions=captions,
        audio_segments=audio_segments,
    )


# ---------------------------------------------------------------------------
# Variable handling
# ---------------------------------------------------------------------------

def parse_var_args(var_overrides: List[str]) -> Dict[str, str]:
    resolved = {}
    for override in var_overrides:
        if "=" not in override:
            raise ValueError(f"Invalid --var argument '{override}'. Use KEY=VALUE format.")
        key, value = override.split("=", 1)
        resolved[key.strip()] = value.strip()
    return resolved


def resolve_variables(template: VideoTemplate, overrides: Dict[str, str]) -> Dict[str, str]:
    resolved = {}
    for key, meta in template.variables.items():
        if key in overrides:
            resolved[key] = overrides[key]
        elif "default" in meta:
            resolved[key] = meta["default"]
        elif "example" in meta:
            resolved[key] = meta["example"]
        else:
            raise ValueError(
                f"No value supplied for {key}. Provide --var {key}=VALUE or set a default in the template."
            )
    # Pass through any extra overrides for experimentation
    for key, value in overrides.items():
        resolved.setdefault(key, value)
    return resolved


def substitute_variables(text: str, variables: Dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))

    return VARIABLE_PATTERN.sub(repl, text)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def pick_font_path() -> str | None:
    for candidate in DEFAULT_FONT_PATHS:
        if Path(candidate).exists():
            return candidate
    return None


def hex_to_rgba(color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    color = color.lstrip("#")
    if len(color) == 6:
        r, g, b = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
        return (r, g, b, alpha)
    raise ValueError(f"Unsupported color format: {color}")


def render_text_frame(
    size: Tuple[int, int],
    text: str,
    font_size: int,
    color: str,
    position: str,
) -> np.ndarray:
    width, height = size
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    font_path = pick_font_path()
    if font_path:
        font = ImageFont.truetype(font_path, font_size)
    else:
        font = ImageFont.load_default()

    wrapped = textwrap.fill(text, width=30)
    text_bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    if position == "top":
        x = (width - text_width) / 2
        y = height * 0.12
    elif position == "bottom":
        x = (width - text_width) / 2
        y = height - text_height - height * 0.12
    else:  # center and fallback
        x = (width - text_width) / 2
        y = (height - text_height) / 2

    draw.multiline_text((x, y), wrapped, font=font, fill=hex_to_rgba(color), align="center")
    return np.array(image)


def build_text_clips(template: VideoTemplate, variables: Dict[str, str]) -> List[ImageClip]:
    clips: List[ImageClip] = []
    for layer in template.text_layers:
        text = substitute_variables(layer.template, variables)
        frame = render_text_frame(template.resolution, text, layer.font_size, layer.color, layer.position)
        clip = ImageClip(frame, duration=max(layer.end - layer.start, 0.1)).set_start(layer.start)
        clips.append(clip)
    return clips


def synthesize_tone_from_text(text: str, fps: int = 44100) -> AudioArrayClip:
    # Map characters to pleasant sine-wave tones to keep dependencies lightweight.
    duration_per_char = 0.18
    segments: List[np.ndarray] = []
    for char in text:
        if char == " ":
            segments.append(np.zeros(int(duration_per_char * fps)))
            continue
        base_freq = 330.0
        offset = (ord(char.lower()) - 97) if char.isalpha() else 5
        freq = base_freq + (offset * 12)
        t = np.linspace(0, duration_per_char, int(duration_per_char * fps), endpoint=False)
        wave = 0.25 * np.sin(2 * math.pi * freq * t)
        envelope = np.linspace(0.1, 1.0, wave.size)
        segments.append(wave * envelope)

    if not segments:
        segments.append(np.zeros(int(duration_per_char * fps)))

    audio = np.concatenate(segments).astype(np.float32)
    return AudioArrayClip(audio.reshape(-1, 1), fps=fps)


def build_audio_clip(template: VideoTemplate, variables: Dict[str, str]) -> CompositeAudioClip:
    audio_clips = []
    for segment in template.audio_segments:
        text = substitute_variables(segment.template, variables)
        if segment.generator == "tone_from_text":
            clip = synthesize_tone_from_text(text)
        else:
            raise ValueError(f"Unsupported audio generator: {segment.generator}")
        audio_clips.append(clip.set_start(segment.start))

    if not audio_clips:
        silent = AudioArrayClip(np.zeros((int(template.duration * 44100), 1)), fps=44100)
        return CompositeAudioClip([silent])

    composite = CompositeAudioClip(audio_clips)
    return composite.set_duration(template.duration)


def write_captions(template: VideoTemplate, variables: Dict[str, str], output_path: Path) -> None:
    lines = []
    for index, caption in enumerate(template.captions, start=1):
        text = substitute_variables(caption.template, variables)
        start_stamp = seconds_to_timestamp(caption.start)
        end_stamp = seconds_to_timestamp(caption.end)
        lines.extend(
            [
                str(index),
                f"{start_stamp} --> {end_stamp}",
                text,
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def seconds_to_timestamp(value: float) -> str:
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = int(value % 60)
    milliseconds = int((value - int(value)) * 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Personalize a variable-filled video template.")
    parser.add_argument("template", type=Path, help="Path to the template JSON definition.")
    parser.add_argument(
        "--var",
        dest="vars",
        action="append",
        default=[],
        help="Override a template variable, e.g. --var VAR_NAME=Jordan",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/personalized_clip.mp4"),
        help="Where to save the rendered video.",
    )
    parser.add_argument(
        "--captions",
        type=Path,
        default=Path("outputs/personalized_clip.srt"),
        help="Where to save the generated caption file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    template = load_template(args.template)

    overrides = parse_var_args(args.vars)
    resolved_vars = resolve_variables(template, overrides)

    output_dir = args.output.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    args.captions.parent.mkdir(parents=True, exist_ok=True)

    background = ColorClip(size=template.resolution, color=hex_to_rgba(template.background_color)[:3])
    background = background.set_duration(template.duration)

    text_clips = build_text_clips(template, resolved_vars)
    audio_clip = build_audio_clip(template, resolved_vars)

    final_clip = CompositeVideoClip([background, *text_clips])
    final_clip = final_clip.set_duration(template.duration).set_audio(audio_clip)

    print("Resolved variables:")
    for key, value in resolved_vars.items():
        print(f"  {key} = {value}")

    print(f"\nRendering video to {args.output} ...")
    final_clip.write_videofile(str(args.output), fps=template.fps, codec="libx264", audio_codec="aac")

    print(f"Generating captions at {args.captions} ...")
    write_captions(template, resolved_vars, args.captions)
    print("Done!")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
