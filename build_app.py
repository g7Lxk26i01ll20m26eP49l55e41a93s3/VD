# -*- coding: utf-8 -*-
"""
VD Modular Build & Asset Bundler
Compiles static/css/style.css, static/js/app.js, and templates/index.html.
"""
import os
import sys

from builder_css import GET_CSS
from builder_html import GET_HTML
from builder_js import GET_JS

def assemble():
    print("Compiling VD CSS bundle...")
    css = GET_CSS()
    print("Compiling VD HTML template...")
    html = GET_HTML()
    print("Compiling VD JavaScript Engine...")
    js = GET_JS()

    base_dir = os.path.join("d:", os.sep, "rave")
    static_css_dir = os.path.join(base_dir, "static", "css")
    static_js_dir = os.path.join(base_dir, "static", "js")
    templates_dir = os.path.join(base_dir, "templates")

    os.makedirs(static_css_dir, exist_ok=True)
    os.makedirs(static_js_dir, exist_ok=True)
    os.makedirs(templates_dir, exist_ok=True)

    css_path = os.path.join(static_css_dir, "style.css")
    js_path = os.path.join(static_js_dir, "app.js")
    html_path = os.path.join(templates_dir, "index.html")

    # 1. Write CSS file
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css)
    print(f"[OK] Generated {css_path} ({len(css)} bytes)")

    # 2. Write JS file
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"[OK] Generated {js_path} ({len(js)} bytes)")

    # 3. Write index.html linking to assets
    final_html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover">
  <title>VD — Смотрите видео вместе на расстоянии</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%236366f1'/><text x='16' y='22' font-family='sans-serif' font-size='15' font-weight='900' fill='white' text-anchor='middle'>VD</text></svg>">
  <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.8/dist/hls.min.js"></script>
  <link rel="stylesheet" href="/static/css/style.css?v={{{{ asset_version|default('3.0') }}}}">
</head>
<body>
{html}
  <script src="/static/js/app.js?v={{{{ asset_version|default('3.0') }}}}"></script>
</body>
</html>
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(final_html)
    print(f"[OK] Generated {html_path} ({len(final_html)} bytes, {len(final_html.splitlines())} lines)")
    print("=== VD ASSET COMPILATION COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    assemble()
