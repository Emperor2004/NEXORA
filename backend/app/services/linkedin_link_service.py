from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.services.document_extraction_service import fetch_document


MAX_LINKS_PER_PAGE = 500


def normalize_job_url(url: str) -> str:
    try:
        parsed = urlsplit(url)

        if parsed.scheme not in {"http", "https"}:
            return ""

        hostname = (parsed.hostname or "").lower()

        if hostname not in {"linkedin.com", "www.linkedin.com", "in.linkedin.com"}:
            return ""

        if not parsed.path.startswith("/jobs/view/"):
            return ""

        return urlunsplit((
            "https",
            "www.linkedin.com",
            parsed.path.rstrip("/"),
            "",
            ""
        ))

    except Exception:
        return ""


def extract_linkedin_job_links(html: bytes, source_page_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    links_by_url = {}

    for anchor in soup.find_all("a", href=True):
        absolute_url = urljoin(source_page_url, anchor["href"])
        normalized_url = normalize_job_url(absolute_url)

        if not normalized_url:
            continue

        anchor_text = anchor.get_text(" ", strip=True)

        if normalized_url not in links_by_url:
            links_by_url[normalized_url] = {
                "job_url": normalized_url,
                "anchor_text": anchor_text[:500],
                "source_page_url": source_page_url,
                "link_source": "linkedin_listing_html",
                "resolution_status": "unverified_link"
            }

        if len(links_by_url) >= MAX_LINKS_PER_PAGE:
            break

    return list(links_by_url.values())


def extract_links_from_page(source_page_url: str) -> dict:
    fetched = fetch_document(source_page_url)

    result = {
        "source_page_url": source_page_url,
        "fetch_status": fetched["fetch_status"],
        "final_url": fetched.get("final_url"),
        "link_count": 0,
        "links": [],
        "error": fetched.get("error")
    }

    if fetched["fetch_status"] != "fetched":
        return result

    if fetched.get("document_type") != "html":
        result["error"] = "Source page did not return HTML."
        return result

    links = extract_linkedin_job_links(
        fetched["content"],
        fetched.get("final_url") or source_page_url
    )

    result["links"] = links
    result["link_count"] = len(links)

    return result
