"""Tests covering HtmlCleaner behaviours."""

from __future__ import annotations

from pathlib import Path

from cleaners import HtmlCleaner


def _write_html(tmp_path: Path, filename: str, content: str) -> Path:
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")
    return path


def test_html_cleaner_removes_noise_and_keeps_headings(tmp_path: Path) -> None:
    cleaner = HtmlCleaner()
    html = """
    <html>
      <head>
        <title>Sample</title>
        <style>.banner { display: none; }</style>
      </head>
      <body>
        <header>Site Header</header>
        <nav>Navigation</nav>
        <main>
          <h1>Article Title</h1>
          <p>Intro paragraph with <strong>important</strong> text.</p>
          <script>console.log('tracked');</script>
        </main>
        <footer>Site Footer</footer>
      </body>
    </html>
    """
    html_path = _write_html(tmp_path, "sample.html", html)

    result = cleaner.clean(str(html_path))

    assert "# Article Title" in result
    assert "Intro paragraph with important text." in result
    assert "Navigation" not in result
    assert "Site Header" not in result
    assert "console.log" not in result


def test_html_cleaner_renders_lists_and_tables(tmp_path: Path) -> None:
    cleaner = HtmlCleaner()
    html = """
    <html>
      <body>
        <article>
          <h2>Steps</h2>
          <ul>
            <li>Install <a href="https://example.com/guide">guide</a></li>
            <li>Run tests</li>
          </ul>
          <h3>Checklist</h3>
          <ol>
            <li>First</li>
            <li>Second
              <ul>
                <li>Nested item</li>
              </ul>
            </li>
          </ol>
          <table>
            <tr><th>Name</th><th>Value</th></tr>
            <tr><td>Foo</td><td>Bar</td></tr>
            <tr><td>Baz</td><td>Qux</td></tr>
          </table>
        </article>
      </body>
    </html>
    """
    html_path = _write_html(tmp_path, "lists_tables.html", html)

    result = cleaner.clean(str(html_path))
    lines = [line.strip() for line in result.splitlines() if line.strip()]

    assert "## Steps" in lines
    assert "- Install guide (https://example.com/guide)" in result
    assert "- Run tests" in result
    assert "### Checklist" in lines
    assert any(line.startswith("1. First") for line in lines)
    assert any(line.startswith("2. Second") for line in lines)
    assert any(line.startswith("- Nested item") for line in lines)
    assert "| Name" in result
    assert "| Foo" in result
