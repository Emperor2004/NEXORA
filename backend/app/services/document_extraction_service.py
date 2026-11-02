from __future__ import annotations

import ipaddress
import socket
from io import BytesIO
from urllib.parse import urljoin, urlparse

import pymupdf
import httpx
from bs4 import BeautifulSoup


MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARACTERS = 100_000
MAX_REDIRECTS = 4

HEADERS = {
    "User-Agent": (
        "NEXORA-ResearchBot/0.1 "
        "(educational internship discovery; contact: local application)"
    ),
    "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.5",
}


def validate_public_url(url: str) -> None:
    """Reject non-HTTP URLs and hostnames resolving to non-public IP addresses."""
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported.")

    if not parsed.hostname:
        raise ValueError("URL has no hostname.")

    if parsed.username or parsed.password:
        raise ValueError("URLs containing embedded credentials are not allowed.")

    hostname = parsed.hostname.lower()

    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("Localhost URLs are not allowed.")

    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve hostname: {hostname}") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])

        if not ip.is_global:
            raise ValueError(f"Non-public destination rejected: {ip}")


def fetch_document(url: str) -> dict:
    """Fetch a public HTML or PDF document, with bounded size and redirects."""
    current_url = url

    try:
        with httpx.Client(
            timeout=httpx.Timeout(20.0, connect=10.0),
            follow_redirects=False,
            headers=HEADERS,
        ) as client:

            for redirect_number in range(MAX_REDIRECTS + 1):
                validate_public_url(current_url)

                with client.stream("GET", current_url) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if redirect_number == MAX_REDIRECTS:
                            raise ValueError("Maximum redirect count exceeded.")

                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("Redirect response has no Location header.")

                        current_url = urljoin(current_url, location)
                        continue

                    response.raise_for_status()

                    content_type = response.headers.get(
                        "content-type", ""
                    ).split(";")[0].strip().lower()

                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
                        raise ValueError("Document exceeds the 8 MB download limit.")

                    chunks = []
                    total_bytes = 0

                    for chunk in response.iter_bytes():
                        total_bytes += len(chunk)

                        if total_bytes > MAX_DOWNLOAD_BYTES:
                            raise ValueError(
                                "Document exceeded the 8 MB download limit."
                            )

                        chunks.append(chunk)

                    content = b"".join(chunks)
                    final_url = str(response.url)

                validate_public_url(final_url)

                if content_type == "application/pdf" or content.startswith(b"%PDF"):
                    return {
                        "fetch_status": "fetched",
                        "document_type": "pdf",
                        "content_type": content_type or "application/pdf",
                        "final_url": final_url,
                        "http_status": response.status_code,
                        "content": content,
                    }

                if (
                    content_type in {"text/html", "application/xhtml+xml"}
                    or b"<html" in content[:1000].lower()
                    or b"<!doctype html" in content[:1000].lower()
                ):
                    return {
                        "fetch_status": "fetched",
                        "document_type": "html",
                        "content_type": content_type or "text/html",
                        "final_url": final_url,
                        "http_status": response.status_code,
                        "content": content,
                    }

                return {
                    "fetch_status": "unsupported_content_type",
                    "document_type": None,
                    "content_type": content_type or "unknown",
                    "final_url": final_url,
                    "http_status": response.status_code,
                    "error": "The URL did not return an HTML or PDF document.",
                }

        raise ValueError("Unable to complete document fetch.")

    except Exception as exc:
        return {
            "fetch_status": "fetch_error",
            "document_type": None,
            "content_type": None,
            "final_url": current_url,
            "http_status": None,
            "error": f"{type(exc).__name__}: {str(exc)[:500]}",
        }


def extract_html(content: bytes) -> tuple[str, list[dict]]:
    """Extract readable HTML text and retain heading-based evidence sections."""
    soup = BeautifulSoup(content, "html.parser")

    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    for element in soup.select(
        "script, style, noscript, svg, nav, footer, header, form, iframe"
    ):
        element.decompose()

    main = soup.find("main") or soup.find("article") or soup.body or soup

    sections = []
    current_heading = title or "Page content"
    current_parts = []

    for element in main.find_all(
        ["h1", "h2", "h3", "h4", "p", "li", "td", "th"],
        recursive=True,
    ):
        text = element.get_text(" ", strip=True)

        if not text:
            continue

        if element.name in {"h1", "h2", "h3", "h4"}:
            if current_parts:
                sections.append({
                    "reference": current_heading,
                    "text": " ".join(current_parts),
                })

            current_heading = text
            current_parts = []
        else:
            current_parts.append(text)

    if current_parts:
        sections.append({
            "reference": current_heading,
            "text": " ".join(current_parts),
        })

    full_text = "\n\n".join(
        f"{section['reference']}\n{section['text']}"
        for section in sections
    )

    if not full_text.strip():
        full_text = main.get_text(" ", strip=True)

    full_text = full_text[:MAX_TEXT_CHARACTERS]

    evidence = []
    for section in sections:
        if section["text"].strip():
            evidence.append({
                "source_location": section["reference"],
                "text": section["text"][:3000],
            })

    return full_text, evidence


def extract_pdf(content: bytes) -> tuple[str, list[dict]]:
    """Extract PDF text while retaining page numbers."""
    document = pymupdf.open(stream=BytesIO(content), filetype="pdf")

    page_texts = []
    evidence = []

    try:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            if not text:
                continue

            page_texts.append(f"[Page {page_number}]\n{text}")

            evidence.append({
                "source_location": f"PDF page {page_number}",
                "text": text[:3000],
            })

            if sum(len(item) for item in page_texts) >= MAX_TEXT_CHARACTERS:
                break
    finally:
        document.close()

    full_text = "\n\n".join(page_texts)[:MAX_TEXT_CHARACTERS]

    return full_text, evidence


def extract_document(url: str) -> dict:
    """Fetch a source and return extracted text with evidence locations."""
    fetched = fetch_document(url)

    result = {
        "requested_url": url,
        "final_url": fetched.get("final_url"),
        "fetch_status": fetched["fetch_status"],
        "document_type": fetched.get("document_type"),
        "content_type": fetched.get("content_type"),
        "http_status": fetched.get("http_status"),
        "extraction_status": "not_attempted",
        "extracted_text": "",
        "evidence": [],
        "error": fetched.get("error"),
    }

    if fetched["fetch_status"] != "fetched":
        return result

    try:
        if fetched["document_type"] == "pdf":
            text, evidence = extract_pdf(fetched["content"])
        else:
            text, evidence = extract_html(fetched["content"])

        result["extracted_text"] = text
        result["evidence"] = evidence
        result["extraction_status"] = (
            "extracted" if text.strip() else "empty_document"
        )

        if not text.strip():
            result["error"] = "No readable text was extracted."

    except Exception as exc:
        result["extraction_status"] = "extraction_error"
        result["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"

    return result

