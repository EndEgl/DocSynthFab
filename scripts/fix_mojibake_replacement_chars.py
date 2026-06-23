from pathlib import Path

paths = [
    Path("src/docsynthfab/render/page_renderer.py"),
    Path("test/unit/qc/test_content_contracts.py"),
]

for path in paths:
    text = path.read_text(encoding="utf-8")
    if "\uFFFD" in text:
        text = text.replace("\uFFFD", "\\uFFFD")
        path.write_text(text, encoding="utf-8")
        print("fixed", path)
    else:
        print("no replacement char", path)
