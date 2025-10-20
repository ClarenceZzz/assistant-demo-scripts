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


def test_html_cleaner_preserves_line_breaks_and_paragraphs(tmp_path: Path) -> None:
    cleaner = HtmlCleaner()
    html = """
    <html>
      <body>
        <p>第一行<br>第二行</p>
        <p>第三行段落</p>
        <ul>
          <li>项1</li>
          <li>项2<br>换行</li>
        </ul>
      </body>
    </html>
    """
    html_path = _write_html(tmp_path, "line_breaks.html", html)

    result = cleaner.clean(str(html_path))
    lines = result.splitlines()

    assert lines[0] == "第一行"
    assert lines[1] == "第二行"
    assert lines[2] == ""
    assert lines[3] == "第三行段落"
    assert lines[4] == ""
    assert lines[5] == "- 项1"
    assert lines[6] == "- 项2"
    assert lines[7].startswith("  换行")


def test_html_cleaner_outputs_markdown_shape(tmp_path: Path) -> None:
    cleaner = HtmlCleaner()
    html = """
    <html>
      <body>
        <article>
          <h1>Title</h1>
          <section>
            <h2>Subsection</h2>
            <p>内容一。</p>
            <p>内容二。</p>
          </section>
          <table>
            <tr><th>ColA</th><th>ColB</th></tr>
            <tr><td>A</td><td>B</td></tr>
          </table>
        </article>
      </body>
    </html>
    """
    html_path = _write_html(tmp_path, "shape.html", html)

    result = cleaner.clean(str(html_path))
    lines = [line for line in result.splitlines() if line]

    headings = [line for line in lines if line.startswith("#")]
    assert headings == ["# Title", "## Subsection"]
    table_lines = [line for line in lines if line.startswith("|")]
    assert len(table_lines) == 3
    assert all(line.count("|") >= 3 for line in table_lines)
    paragraphs = [line for line in lines if not line.startswith("#") and not line.startswith("|")]
    assert paragraphs[:2] == ["内容一。", "内容二。"]
