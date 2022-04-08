"""

"""

from absl import app
from absl import flags
from absl import logging
from pathlib import Path
import requests
import shutil
import subprocess
from typing import NamedTuple, Optional, Tuple
from urllib.parse import urlparse
import zipfile


class FontSource(NamedTuple):
    url: str
    fonts: Tuple[Path, ...]
    family_dir: str
    git_dir: Optional[str] = None
    maximum_color_args: Tuple[str, ...] = ()

_FONT_SOURCES = (
    FontSource(
        "https://github.com/aliftype/amiri/releases/download/0.114/Amiri-0.114.zip",
        (Path("Amiri-0.114/AmiriQuranColored.ttf"),),
        "ofl/amiriqurancolored",
        maximum_color_args=("--bitmap_resolution", "72")
    ),
    FontSource(
        "https://github.com/aliftype/aref-ruqaa/releases/download/v1.004/ArefRuqaa-1.004.zip",
        (
            Path("ArefRuqaa-1.004/ttf/ArefRuqaaInk-Regular.ttf"),
            Path("ArefRuqaa-1.004/ttf/ArefRuqaaInk-Bold.ttf"),
        ),
        "ofl/arefruqaaink",
    ),
    FontSource(
        "https://github.com/aliftype/reem-kufi/raw/main/ReemKufiFun.ttf",
        (
            Path("ReemKufiFun.ttf"),
        ),
        "ofl/reemkufifun",
    ),
    # This one is private :(
    FontSource(
        "git@github.com:Gue3bara/Blaka.git",
        (
            Path("fonts/BlakaInk-Regular.ttf"),
        ),
        "ofl/blakaink",
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
                    with open(_TEMP_DIR / font.name, 'wb') as f:
                        f.write(zip_file.read(str(font)))
            elif font_source.url.startswith("git@"):
                for font in font_source.fonts:
                    source_file = _TEMP_DIR / font_source.git_dir / font
                    assert source_file.is_file(), f"Missing {source_file}"
                    shutil.copyfile(source_file, _TEMP_DIR / source_file.name)
            else:
                assert (_TEMP_DIR / font).is_file()



def main(_):
    _TEMP_DIR.mkdir(exist_ok=True)

    _fetch_fonts(_FONT_SOURCES)

    fonts = _TEMP_DIR.glob("*.[ot]tf")
    for font_source in _FONT_SOURCES:
        for font in font_source.fonts:
            font = _TEMP_DIR / font.name
            assert font.is_file, f"Missing {font}"
            conversion_dir = _TEMP_DIR / "maximum_color" / font.stem
            conversion_dir.mkdir(parents=True, exist_ok=True)
            cmd = ("maximum_color", font) + font_source.maximum_color_args
            print("Maximizing", font, "in", conversion_dir, " ".join(str(c) for c in cmd))
            subprocess.run(
                cmd,
                cwd=conversion_dir,
                check=True,
            )
            converted_font = conversion_dir / "build" / font.name
            print("Maximum version", converted_font)
            print()


if __name__ == "__main__":
    app.run(main)
