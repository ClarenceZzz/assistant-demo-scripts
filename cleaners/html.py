"""Implementation of the HTML cleaner leveraging BeautifulSoup."""

from __future__ import annotations

import logging
import re
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Union

try:  # pragma: no cover - bs4 is optional at runtime
    from bs4 import BeautifulSoup, Comment, NavigableString, Tag
except ImportError:  # pragma: no cover - fallback to lightweight parser
    BeautifulSoup = None

    class Comment(str):  # type: ignore[override]
        """Fallback representation for HTML comments."""

    NavigableString = str
    Tag = "Tag"  # Placeholder to be replaced by SimpleNode later in the module.

from .base import BaseCleaner

LOGGER = logging.getLogger(__name__)


class SimpleNode:
    """Lightweight fallback representation for HTML nodes."""

    __slots__ = ("name", "attrs", "children", "parent")

    def __init__(
        self,
        name: str,
        attrs: Optional[Dict[str, str]] = None,
        parent: Optional["SimpleNode"] = None,
    ) -> None:
        self.name = name
        self.attrs = attrs or {}
        self.children: List[Union["SimpleNode", str]] = []
        self.parent = parent

    def append_child(self, child: Union["SimpleNode", str]) -> None:
        self.children.append(child)

    def find_all(
        self,
        names: Optional[Union[Set[str], Sequence[str]]] = None,
        recursive: bool = True,
    ) -> List["SimpleNode"]:
        if names is None:
            name_set: Optional[Set[str]] = None
        elif isinstance(names, (set, frozenset)):
            name_set = {name.lower() for name in names}
        else:
            name_set = {name.lower() for name in names}

        matches: List["SimpleNode"] = []
        for child in self.children:
            if isinstance(child, SimpleNode):
                if name_set is None or child.name.lower() in name_set:
                    matches.append(child)
                if recursive:
                    matches.extend(child.find_all(name_set, recursive=True))
        return matches

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.attrs.get(key, default)

    def decompose(self) -> None:
        if self.parent is None:
            return
        self.parent.children = [
            child for child in self.parent.children if child is not self
        ]
        self.parent = None
        self.children = []


class SimpleDocument(SimpleNode):
    """Root node containing reference to the <body> element when available."""

    __slots__ = ("body",)

    def __init__(self) -> None:
        super().__init__("document")
        self.body: Optional[SimpleNode] = None


class _MiniHTMLParser(HTMLParser):
    """Fallback HTML parser creating SimpleNode trees."""

    VOID_ELEMENTS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self) -> None:
        super().__init__()
        self.document = SimpleDocument()
        self._stack: List[SimpleNode] = [self.document]

    def handle_starttag(self, tag: str, attrs: Sequence[tuple[str, Optional[str]]]) -> None:
        attr_dict = {name: value or "" for name, value in attrs}
        node = SimpleNode(tag, attr_dict, parent=self._stack[-1])
        self._stack[-1].append_child(node)
        if tag.lower() == "body":
            self.document.body = node
        if tag.lower() not in self.VOID_ELEMENTS:
            self._stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].name.lower() == tag_lower:
                del self._stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if not data:
            return
        current = self._stack[-1]
        current.append_child(data)

    def handle_comment(self, data: str) -> None:
        # Represent comments as strings to enable removal during normalisation.
        self._stack[-1].append_child(Comment(data))  # type: ignore[operator]


def _fallback_soup(html: str) -> SimpleDocument:
    parser = _MiniHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.document


if BeautifulSoup is None:  # pragma: no cover - exercised when bs4 missing
    Tag = SimpleNode  # type: ignore[assignment]


class HtmlCleaner(BaseCleaner):
    """Cleaner implementation dedicated to HTML documents."""

    TAGS_TO_REMOVE = {"script", "style", "nav", "footer", "header", "noscript", "aside"}
    HEADING_LEVEL_PREFIX = {level: "#" * level for level in range(1, 7)}

    def __init__(self) -> None:
        self._logger = LOGGER

    def clean(self, file_path: str) -> str:
        """Clean the provided HTML file and return normalized Markdown text."""

        path = Path(file_path)
        if not path.exists():
            msg = f"File not found: {file_path}"
            self._logger.error(msg)
            raise FileNotFoundError(msg)

        html_content = path.read_text(encoding="utf-8", errors="ignore")
        soup = self._parse_html(html_content)

        self._strip_unwanted_nodes(soup)
        root = getattr(soup, "body", None) or soup
        lines: List[str] = []
        self._render_children(root, lines, indent=0)

        compacted = self._compact_lines(lines)
        ensured = self._ensure_heading(soup, compacted)
        normalized = unicodedata.normalize("NFKC", "\n".join(ensured)).strip()
        return self._strip_bom(normalized)

    def _parse_html(self, html_content: str) -> Union[SimpleDocument, BeautifulSoup]:
        """Parse HTML content returning either BeautifulSoup or fallback tree."""

        if BeautifulSoup is not None:
            return BeautifulSoup(html_content, "html.parser")
        return _fallback_soup(html_content)

    def _strip_unwanted_nodes(
        self, soup: Union[SimpleDocument, BeautifulSoup]
    ) -> None:
        """Remove noisy nodes such as scripts, styles and comments."""

        for removable in self._find_all(soup, self.TAGS_TO_REMOVE):
            removable.decompose()
        if BeautifulSoup is not None:
            for comment in soup.find_all(string=lambda item: isinstance(item, Comment)):  # type: ignore[attr-defined]
                comment.extract()  # type: ignore[call-arg]
        else:
            self._strip_comments(soup)

    def _render_children(self, parent: Tag, lines: List[str], indent: int) -> None:
        """Render child nodes of the given parent into Markdown lines."""

        for child in getattr(parent, "children", []):
            if isinstance(child, (NavigableString, str)):
                continue
            if isinstance(child, Tag):
                self._render_tag(child, lines, indent)
            elif isinstance(child, SimpleNode):
                self._render_tag(child, lines, indent)

    def _render_tag(self, tag: Tag, lines: List[str], indent: int) -> None:
        """Render an individual tag into Markdown lines."""

        name = tag.name.lower()
        if name in {f"h{level}" for level in range(1, 7)}:
            level = min(int(name[1]), 6)
            content = self._collect_inline_text(tag)
            if content:
                prefix = self.HEADING_LEVEL_PREFIX.get(level, "##")
                self._emit_block(lines, f"{prefix} {content}")
        elif name in {"p", "pre", "blockquote"}:
            content = self._collect_inline_text(tag)
            if content:
                if name == "pre":
                    self._emit_block(lines, f"```\n{content}\n```")
                elif name == "blockquote":
                    quoted = "\n".join(f"> {line}" for line in content.splitlines() if line.strip())
                    self._emit_block(lines, quoted)
                else:
                    self._emit_block(lines, content)
        elif name in {"ul", "ol"}:
            ordered = name == "ol"
            self._emit_list(tag, lines, indent, ordered=ordered)
        elif name == "table":
            table_lines = self._render_table(tag)
            if table_lines:
                self._emit_block(lines, "\n".join(table_lines))
        elif name in {"br"}:
            self._emit_blank_line(lines)
        elif name == "a":
            content = self._collect_inline_text(tag)
            href = (tag.get("href") or "").strip() if hasattr(tag, "get") else ""
            if content and href:
                self._emit_block(lines, self._format_link(content, href))
            elif content:
                self._emit_block(lines, content)
            elif href:
                self._emit_block(lines, self._format_link(href, href))
        elif name in {"div", "section", "article", "main", "body"} or name.startswith("sr-"):
            self._render_children(tag, lines, indent)
        else:
            # Default behaviour: attempt to render inline content.
            content = self._collect_inline_text(tag)
            if content:
                self._emit_block(lines, content)
            # Also render nested structures such as lists or tables.
            for nested in self._find_all(tag, {"ul", "ol", "table"}, recursive=False):
                self._render_tag(nested, lines, indent)

    def _emit_list(self, tag: Tag, lines: List[str], indent: int, *, ordered: bool) -> None:
        """Render unordered/ordered lists."""

        items = self._find_all(tag, {"li"}, recursive=False)
        if not items:
            return
        if lines and lines[-1] != "":
            lines.append("")
        start = int(tag.get("start", 1)) if ordered else 1
        counter = start
        for item in items:
            content = self._collect_inline_text(item)
            prefix = f"{counter}. " if ordered else "- "
            list_indent = "  " * indent
            line_prefix = f"{list_indent}{prefix}"
            if content:
                content_lines = content.split("\n")
                first = content_lines[0].strip()
                if first:
                    lines.append(f"{line_prefix}{first}")
                else:
                    lines.append(line_prefix.rstrip())
                continuation_indent = f"{list_indent}  "
                for continuation in content_lines[1:]:
                    continuation = continuation.strip()
                    if continuation:
                        lines.append(f"{continuation_indent}{continuation}")
            else:
                lines.append(line_prefix.rstrip())
            nested_lists = self._find_all(item, {"ul", "ol"}, recursive=False)
            for nested in nested_lists:
                self._emit_list(
                    nested,
                    lines,
                    indent=indent + 1,
                    ordered=(nested.name.lower() == "ol"),
                )
            if ordered:
                counter += 1
        lines.append("")

    def _render_table(self, tag: Tag) -> List[str]:
        """Render HTML table into a Markdown table."""

        header_rows: List[List[str]] = []
        body_rows: List[List[str]] = []

        for row in self._find_all(tag, {"tr"}):
            cells: List[str] = []
            is_header = False
            for cell in self._find_all(row, {"th", "td"}, recursive=False):
                content = self._collect_inline_text(cell)
                cells.append(content)
                if cell.name.lower() == "th":
                    is_header = True
            if not cells:
                continue
            if is_header:
                header_rows.append(cells)
            else:
                body_rows.append(cells)

        if not header_rows and not body_rows:
            return []

        if header_rows:
            header = header_rows[0]
        else:
            header = body_rows.pop(0)

        rows = [header] + body_rows
        column_count = max(len(row) for row in rows)
        for row in rows:
            while len(row) < column_count:
                row.append("")

        widths = [
            max(len(row[idx]) for row in rows)
            for idx in range(column_count)
        ]

        def format_row(row: Sequence[str]) -> str:
            padded = [row[idx].ljust(widths[idx]) for idx in range(column_count)]
            return "| " + " | ".join(padded) + " |"

        separator = "| " + " | ".join("-" * max(widths[idx], 3) for idx in range(column_count)) + " |"
        table_lines = [format_row(header), separator]
        for body_row in body_rows:
            table_lines.append(format_row(body_row))
        return table_lines

    def _collect_inline_text(self, node: Tag) -> str:
        """Collect inline text from the given node while skipping block-level structures."""

        parts: List[str] = []
        for child in getattr(node, "children", []):
            if isinstance(child, (NavigableString, str)):
                text = self._normalize_inline_text(str(child))
                if text:
                    parts.append(text)
            elif isinstance(child, Tag):
                name = child.name.lower()
                if name in self.TAGS_TO_REMOVE:
                    continue
                if name == "br":
                    parts.append("\n")
                    continue
                if name in {"ul", "ol", "table"}:
                    continue
                if name == "a":
                    anchor_text = self._collect_inline_text(child)
                    href = child.get("href", "").strip()
                    if anchor_text:
                        if href:
                            parts.append(self._format_link(anchor_text, href))
                        else:
                            parts.append(anchor_text)
                    elif href:
                        parts.append(self._format_link(href, href))
                    continue
                nested = self._collect_inline_text(child)
                if nested:
                    parts.append(nested)
            elif isinstance(child, SimpleNode):
                name = child.name.lower()
                if name in self.TAGS_TO_REMOVE:
                    continue
                if name == "br":
                    parts.append("\n")
                    continue
                if name in {"ul", "ol", "table"}:
                    continue
                if name == "a":
                    anchor_text = self._collect_inline_text(child)
                    href = (child.attrs.get("href") or "").strip()
                    if anchor_text:
                        if href:
                            parts.append(self._format_link(anchor_text, href))
                        else:
                            parts.append(anchor_text)
                    elif href:
                        parts.append(self._format_link(href, href))
                    continue
                nested = self._collect_inline_text(child)
                if nested:
                    parts.append(nested)
        text = "".join(parts)
        if not text:
            return ""
        text = text.replace("\r", "")
        text = re.sub(r"[ \t\f\v]+", " ", text)
        text = re.sub(r" ?\n ?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return self._strip_bom(text).strip()

    def _emit_block(self, lines: List[str], content: str) -> None:
        """Emit a block-level line ensuring separation from surrounding text."""

        content = self._strip_bom(content).strip()
        if not content:
            return
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(content)

    def _emit_blank_line(self, lines: List[str]) -> None:
        """Append a blank line avoiding duplicates."""

        if lines and lines[-1] == "":
            return
        lines.append("")

    def _compact_lines(self, lines: Iterable[str]) -> List[str]:
        """Collapse consecutive blank lines and strip trailing empty entries."""

        result: List[str] = []
        previous_blank = True
        for raw_line in lines:
            line = self._strip_bom(raw_line).rstrip()
            if not line:
                if not previous_blank:
                    result.append("")
                previous_blank = True
            else:
                result.append(line)
                previous_blank = False
        while result and result[-1] == "":
            result.pop()
        return result

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace within inline content."""

        return re.sub(r"\s+", " ", text)

    def _normalize_inline_text(self, text: str) -> str:
        """Normalize inline string segments while preserving explicit newlines."""

        text = self._strip_bom(text.replace("\r", ""))
        text = re.sub(r"[ \t\f\v]+", " ", text)
        return text

    def _find_all(
        self,
        node: Union[SimpleDocument, SimpleNode, BeautifulSoup, Tag],
        names: Union[Set[str], Sequence[str]],
        recursive: bool = True,
    ) -> List[Union[SimpleNode, Tag]]:
        """Helper to support find_all across BeautifulSoup and fallback nodes."""

        if BeautifulSoup is not None and hasattr(node, "find_all"):
            return node.find_all(names, recursive=recursive)  # type: ignore[return-value]
        if isinstance(node, SimpleDocument):
            return node.find_all(names, recursive=recursive)
        if isinstance(node, SimpleNode):
            return node.find_all(names, recursive=recursive)
        return []

    def _strip_comments(self, node: SimpleNode) -> None:
        """Remove comment nodes when using the fallback parser."""

        filtered_children: List[Union[SimpleNode, str]] = []
        for child in node.children:
            if isinstance(child, Comment):
                continue
            if isinstance(child, SimpleNode):
                self._strip_comments(child)
            filtered_children.append(child)
        node.children = filtered_children

    def _strip_bom(self, text: str) -> str:
        """Remove UTF-8 BOM characters from the provided text."""

        return text.replace("\ufeff", "")

    def _format_link(self, text: str, href: str) -> str:
        """Return a Markdown formatted link."""

        label = self._strip_bom(text.strip())
        url = href.strip()
        if not url:
            return label
        if not label:
            return f"<{url}>"
        if label == url:
            return f"<{url}>"
        return f"[{label}]({url})"

    def _ensure_heading(
        self,
        root: Union[SimpleDocument, BeautifulSoup],
        lines: List[str],
    ) -> List[str]:
        """Ensure output begins with a Markdown heading derived from content or title."""

        if not lines:
            return lines

        first_index: Optional[int] = None
        for idx, line in enumerate(lines):
            if line.strip():
                first_index = idx
                break

        if first_index is None:
            return lines

        if lines[first_index].lstrip().startswith("#"):
            return lines

        heading_text = ""
        for candidate in self._find_all(root, {"h1"}):
            heading_text = self._strip_bom(self._collect_inline_text(candidate))
            if heading_text:
                break
        if not heading_text:
            for candidate in self._find_all(root, {"title"}):
                heading_text = self._strip_bom(self._collect_inline_text(candidate))
                if heading_text:
                    break

        if heading_text:
            for delimiter in ("|", "｜"):
                if delimiter in heading_text:
                    parts = [part.strip(" -—") for part in heading_text.split(delimiter) if part.strip()]
                    if parts:
                        heading_text = parts[-1]
        else:
            return lines

        first_line = self._strip_bom(lines[first_index].strip())

        if not heading_text:
            return lines

        if heading_text == first_line:
            lines[first_index] = f"# {heading_text}"
        else:
            lines.insert(0, f"# {heading_text}")
            first_index = 0

        insert_index = first_index + 1
        if insert_index >= len(lines) or lines[insert_index] != "":
            lines.insert(insert_index, "")
        return lines


HTMLCleaner = HtmlCleaner
