"""

"""

from absl import app
from absl import flags
from absl import logging
from fontTools import ttLib
from pathlib import Path
import requests
import shutil
import subprocess
from typing import NamedTuple, Optional, Tuple
from urllib.parse import urlparse
import zipfile


class FontFile(NamedTuple):
    source: Path
    dest: Path


class FontSource(NamedTuple):
    url: str
    fonts: Tuple[FontFile, ...]
    git_dir: Optional[str] = None

_FONT_SOURCES = (
    FontSource(
        "https://github.com/aliftype/amiri/releases/download/0.114/Amiri-0.114.zip",
        (FontFile(Path("Amiri-0.114/AmiriQuranColored.ttf"), Path("ofl/amiriqurancolored/AmiriQuranColored-Regular.ttf")),),
    ),
    FontSource(
        "https://github.com/aliftype/aref-ruqaa/releases/download/v1.004/ArefRuqaa-1.004.zip",
        (
            FontFile(Path("ArefRuqaa-1.004/ttf/ArefRuqaaInk-Regular.ttf"), Path("ofl/arefruqaaink/ArefRuqaaInk-Regular.ttf")),
            FontFile(Path("ArefRuqaa-1.004/ttf/ArefRuqaaInk-Bold.ttf"), Path("ofl/arefruqaaink/ArefRuqaaInk-Bold.ttf")),
        ),
    ),
    FontSource(
        "https://github.com/aliftype/reem-kufi/raw/main/ReemKufiFun.ttf",
        (
            FontFile(Path("ReemKufiFun.ttf"), Path("ofl/reemkufifun/ReemKufiFun[wght].ttf")),
        ),
    ),
    # This one is private :(
    FontSource(
        "git@github.com:Gue3bara/Blaka.git",
        (
            FontFile(Path("fonts/ink/ttf/BlakaInk-Regular.ttf"), Path("ofl/blakaink/BlakaInk-Regular.ttf")),
        ),
        git_dir="blaka_ink",
    ),
)


_TEMP_DIR = Path("/tmp/color_onboarding")
_GOOGLE_FONTS_DIR = Path.home() / "oss" / "fonts"


def _fetch_fonts(font_sources):
    for font_source in font_sources:
        # download if necessary
        dest = _TEMP_DIR
        if font_source.url.startswith("http"):
            dest = dest / Path(urlparse(font_source.url).path).name
        elif font_source.url.startswith("git@"):
            dest = dest / font_source.git_dir

        if not dest.exists():
            logging.info("Fetch %s => %s", font_source.url, dest)
            if font_source.url.startswith("http"):
                resp = requests.get(font_source.url)
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    f.write(resp.content)
            elif font_source.url.startswith("git@"):
                repo_dir = _TEMP_DIR / font_source.git_dir
                if not repo_dir.is_dir():
                    subprocess.run(
                        ("git", "clone", font_source.url, font_source.git_dir),
                        cwd=_TEMP_DIR,
                        check=True,
                    )
                else:
                    subprocess.run(
                        ("git", "pull"),
                        cwd=repo_dir,
                        check=True,
                    )
            else:
                raise ValueError(font_source.url)

        # extract files if necessary
        for font in font_source.fonts:
            if dest.suffix == '.zip':
                with zipfile.ZipFile(dest, 'r') as zip_file:
                    with open(_TEMP_DIR / font.dest.name, 'wb') as f:
                        f.write(zip_file.read(str(font.source)))
            elif font_source.url.startswith("git@"):
                for font in font_source.fonts:
                    source_file = _TEMP_DIR / font_source.git_dir / font.source
                    assert source_file.is_file(), f"Missing {source_file}"
                    shutil.copyfile(source_file, _TEMP_DIR / font.dest.name)
            else:
                assert (_TEMP_DIR / font.source).is_file()
                shutil.copyfile(_TEMP_DIR / font.source, _TEMP_DIR / font.dest.name)


def _coloring(font_file):
    font = ttLib.TTFont(font_file)
    return [t for t in ["COLR", "SVG ", "sbix", "CBDT"] if t in font]


def main(_):
    _TEMP_DIR.mkdir(exist_ok=True)

    _fetch_fonts(_FONT_SOURCES)

    print("Working in", _TEMP_DIR)
    print("Final dests in", _GOOGLE_FONTS_DIR)

    fonts = _TEMP_DIR.glob("*.[ot]tf")
    for font_source in _FONT_SOURCES:
        for font in font_source.fonts:
            font_file = _TEMP_DIR / font.dest.name
            assert font_file.is_file, f"Missing {font_file}"
            conversion_dir = _TEMP_DIR / "maximum_color" / font_file.stem
            conversion_dir.mkdir(parents=True, exist_ok=True)
            converted_font = conversion_dir / "build" / font_file.name

            if not converted_font.is_file():
                cmd = ("maximum_color", font_file, "--output_file", str(converted_font))
                print()
                print("Maximizing", font, "in", conversion_dir, " ".join(str(c) for c in cmd))
                subprocess.run(
                    cmd,
                    cwd=conversion_dir,
                    check=True,
                )

            assert converted_font.is_file(), converted_font
            final_dest = _GOOGLE_FONTS_DIR / font.dest
            print(f"Working", converted_font.relative_to(_TEMP_DIR), ",".join(t.strip() for t in _coloring(converted_font)))
            print("  ", final_dest.relative_to(_GOOGLE_FONTS_DIR))
            final_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(converted_font, final_dest)


if __name__ == "__main__":
    app.run(main)
