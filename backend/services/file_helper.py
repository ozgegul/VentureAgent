"""Utilities for uploaded analysis attachments."""

from __future__ import annotations

from typing import Any
from werkzeug.datastructures import FileStorage

TEXT_FILE_EXTENSIONS = (".txt", ".md", ".csv", ".py", ".js", ".html", ".css")
MAX_ATTACHMENT_PREVIEW = 1800


def format_uploaded_file(file: FileStorage) -> dict[str, Any]:
    """Return a prompt-friendly representation of an uploaded file."""
    filename = file.filename or "dosya"
    content_type = file.content_type or "unknown"
    raw_bytes = file.read()
    file.seek(0)
    size_kb = max(1, len(raw_bytes) // 1024)
    display_name = f"{filename} — {content_type}, {size_kb}KB"

    if content_type.startswith("text/") or filename.lower().endswith(TEXT_FILE_EXTENSIONS):
        text = raw_bytes.decode("utf-8", errors="replace").strip()
        if not text:
            prompt_text = f"[Eklenti: {filename}, tür: {content_type}, boyut: {size_kb}KB]"
        else:
            if len(text) > MAX_ATTACHMENT_PREVIEW:
                text = text[:MAX_ATTACHMENT_PREVIEW] + "\n\n... (dosya içeriği kısaltıldı)"
            prompt_text = (
                f"[Eklenti: {filename}, tür: {content_type}, boyut: {size_kb}KB]"
                "\n\n" + text
            )
    else:
        prompt_text = (
            f"[Eklenti: {filename}, tür: {content_type}, boyut: {size_kb}KB]"
            "\n(Not: içerik yalnızca düz metin dosyaları için gösterilir.)"
        )

    return {
        "prompt_text": prompt_text,
        "display_name": display_name,
        "meta": {
            "filename": filename,
            "content_type": content_type,
            "size_kb": size_kb,
        },
    }


def build_attachment_prompt(file: FileStorage | None) -> tuple[str, dict[str, Any] | None]:
    """Build a prompt addition for an uploaded file, or return empty values."""
    if file is None or not file.filename:
        return "", None

    formatted = format_uploaded_file(file)
    prompt = (
        "\n\nAşağıdaki ek dosyayı da değerlendir:\n" + formatted["prompt_text"]
    )
    return prompt, formatted
