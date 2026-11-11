from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from docling.document_converter import DocumentConverter
from hierarchical.hierarchy_builder_metadata import HierarchyBuilderMetadata
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class PolicyChunk:
    text: str
    section: str | None = None
    page: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=120,
    separators=[
        "\n\n",
        "\n",
        ". ",
        " ",
        "",
    ],
)


def _clean_text(text: str) -> str:
    return "\n".join(
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ).strip()


def _split_text(
    text: str,
    section: str | None = None,
) -> list[PolicyChunk]:
    text = _clean_text(text)

    if not text:
        return []

    chunks = TEXT_SPLITTER.split_text(text)

    return [
        PolicyChunk(
            text=chunk,
            section=section,
        )
        for chunk in chunks
    ]


def _collect_hierarchy(
    node,
    sections: list[str] | None = None,
) -> list[dict[str, object]]:
    sections = list(sections or [])
    results: list[dict[str, object]] = []

    if node.text:
        current_sections = [*sections, node.text.strip()]

        results.append(
            {
                "section": " > ".join(current_sections),
                "text": node.text.strip(),
                "doc_ref": node.doc_ref,
                "level": node.level_toc,
            }
        )
    else:
        current_sections = sections

    for child in node.children:
        results.extend(
            _collect_hierarchy(
                child,
                current_sections,
            )
        )

    return results


def load_markdown_policy(path: Path) -> list[PolicyChunk]:
    content = _clean_text(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    )

    if not content:
        return []

    chunks: list[PolicyChunk] = []
    current_section: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_lines

        text = _clean_text("\n".join(current_lines))

        if text:
            chunks.extend(
                _split_text(
                    text,
                    current_section,
                )
            )

        current_lines = []

    for line in content.splitlines():
        stripped = line.strip()

        if stripped.startswith("#"):
            flush()
            current_section = stripped.lstrip("#").strip()
        else:
            current_lines.append(stripped)

    flush()

    return chunks


def load_text_policy(path: Path) -> list[PolicyChunk]:
    content = _clean_text(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    )

    return _split_text(content)


def load_pdf_policy(path: Path) -> list[PolicyChunk]:
    converter = DocumentConverter()
    result = converter.convert(str(path))

    hierarchy = HierarchyBuilderMetadata(
        result,
        source=path,
    ).infer()

    hierarchy_items = _collect_hierarchy(hierarchy)

    document_text = _clean_text(
        result.document.export_to_markdown()
    )

    if not document_text:
        return []

    if not hierarchy_items:
        return _split_text(document_text)

    section_names = [
        str(item["section"])
        for item in hierarchy_items
        if item.get("section")
    ]

    section = " > ".join(section_names)

    return _split_text(
        document_text,
        section or None,
    )


def load_policy_file(path: str | Path) -> list[PolicyChunk]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Policy file does not exist: {path}"
        )

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        chunks = load_pdf_policy(path)
    elif suffix in {".md", ".markdown"}:
        chunks = load_markdown_policy(path)
    elif suffix == ".txt":
        chunks = load_text_policy(path)
    else:
        raise ValueError(
            f"Unsupported policy file type: {suffix}"
        )

    for index, chunk in enumerate(chunks):
        chunk.metadata.update(
            {
                "source_file": path.name,
                "file_type": suffix.lstrip("."),
                "chunk_index": index,
            }
        )

    return chunks