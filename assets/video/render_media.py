"""Render the README video from demo.html in this folder:

    demo.html -> assets/demo.mp4, assets/demo.gif

    uv run --group media python assets/video/render_media.py          # the video + gif
    uv run --group media python assets/video/render_media.py 3.2 7.5  # just stills at those times

Needs Playwright's Chromium (uv run --group media playwright install chromium) and ffmpeg.
"""

import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import sync_playwright


class Media:
    HERE = Path(__file__).parent
    ASSETS = HERE.parent
    FPS = 60
    GIF_FPS = 20
    GIF_WIDTH = 640
    SCALE = 1.5  # 1280x720 page -> 1920x1080 frames

    def render(self):
        if not shutil.which("ffmpeg"):
            raise SystemExit("ffmpeg is needed (brew install ffmpeg)")
        with tempfile.TemporaryDirectory() as tmp:
            frames = Path(tmp)
            self._capture(frames)
            self._encode(frames)

    def stills(self, times: list[float]):
        """Screenshots at the given times, to check the layout without a full render."""
        with self._page() as page:
            for t in times:
                page.evaluate(f"window.render({t})")
                out = Path(tempfile.gettempdir()) / f"teambath-{t:05.2f}.png"
                page.locator("#stage").screenshot(path=str(out))
                print(out)

    @contextmanager
    def _page(self):
        """demo.html loaded in headless Chromium, fonts and images ready."""
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 720},
                                    device_scale_factor=self.SCALE)
            page.goto((self.HERE / "demo.html").as_uri())
            page.evaluate("window.ready")
            yield page
            browser.close()

    def _capture(self, frames: Path):
        with self._page() as page:
            duration = page.evaluate("window.DURATION")
            stage = page.locator("#stage")
            count = round(duration * self.FPS)
            for i in range(count):
                page.evaluate(f"window.render({i / self.FPS})")
                stage.screenshot(path=str(frames / f"{i:04d}.png"))
        print(f"captured {count} frames ({duration:.1f}s)")

    def _encode(self, frames: Path):
        src = ["-framerate", str(self.FPS), "-i", str(frames / "%04d.png")]
        mp4 = self.ASSETS / "demo.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *src, "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow",
                        "-movflags", "+faststart", str(mp4)], check=True)
        # The GIF comes from the MP4. Bayer dithering keeps the moving floodlight from
        # changing every pixel of every frame, which would double the file size.
        gif = self.ASSETS / "demo.gif"
        palette = (f"fps={self.GIF_FPS},scale={self.GIF_WIDTH}:-1:flags=lanczos,split[a][b];"
                   "[a]palettegen=max_colors=200:stats_mode=diff[p];"
                   "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-vf", palette,
                        "-loop", "0", str(gif)], check=True)
        for f in (mp4, gif):
            print(f"{f.name}: {f.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        Media().stills([float(t) for t in sys.argv[1:]])
    else:
        Media().render()
