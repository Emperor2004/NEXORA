from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from ddgs import DDGS


TRACKING_PARAMETERS = {"gclid", "fbclid", "ref", "source"}


def normalize_url(url: str) -> str:
    try:
        parsed = urlsplit(url)

        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return ""

        hostname = parsed.hostname.lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        parameters = [
            (key, value)
            for key, value in parse_qsl(parsed.query)
            if not key.lower().startswith("utm_")
            and key.lower() not in TRACKING_PARAMETERS
        ]

        return urlunsplit((
            parsed.scheme.lower(),
            hostname,
            parsed.path.rstrip("/") or "/",
            urlencode(parameters),
            ""
        ))

    except Exception:
        return ""


def classify_domain(domain: str) -> dict:
    domain = domain.lower().strip(".")

    if domain.endswith((".gov.in", ".nic.in")):
        return {
            "source_type": "government_domain",
            "official_domain": True,
            "priority": 1
        }

    if domain.endswith((".ac.in", ".edu.in")):
        return {
            "source_type": "academic_domain",
            "official_domain": True,
            "priority": 2
        }

    return {
        "source_type": "other_domain",
        "official_domain": False,
        "priority": 3
    }


def search_internships(
    queries: list[str],
    max_results_per_query: int = 5
) -> dict:

    if not queries:
        raise ValueError("At least one search query is required")

    if not 1 <= max_results_per_query <= 10:
        raise ValueError("max_results_per_query must be between 1 and 10")

    collected_at = datetime.now(timezone.utc).isoformat()

    results_by_url = {}
    query_reports = []
    errors = []

    search_client = DDGS(timeout=15)

    for query in queries:

        try:
            search_results = list(search_client.text(
                query=query,
                region="in-en",
                safesearch="moderate",
                max_results=max_results_per_query,
                backend="auto"
            ))

            if not search_results:
                query_reports.append({
                    "query": query,
                    "status": "no_results",
                    "result_count": 0
                })
                continue

            query_reports.append({
                "query": query,
                "status": "success",
                "result_count": len(search_results)
            })

            for item in search_results:

                normalized_url = normalize_url(item.get("href", ""))

                if not normalized_url:
                    continue

                domain = urlsplit(normalized_url).hostname or ""
                classification = classify_domain(domain)

                if normalized_url in results_by_url:
                    existing = results_by_url[normalized_url]

                    if query not in existing["matched_queries"]:
                        existing["matched_queries"].append(query)

                    continue

                results_by_url[normalized_url] = {
                    "title": item.get("title", "").strip(),
                    "url": normalized_url,
                    "snippet": item.get("body", "").strip(),
                    "domain": domain,
                    "source_type": classification["source_type"],
                    "official_domain": classification["official_domain"],
                    "source_priority": classification["priority"],
                    "matched_queries": [query],
                    "collected_at": collected_at,
                    "evidence_status": "unverified_search_result"
                }

        except Exception as error:

            message = str(error)

            if "no results found" in message.lower():
                query_reports.append({
                    "query": query,
                    "status": "no_results",
                    "result_count": 0
                })
                continue

            query_reports.append({
                "query": query,
                "status": "error",
                "result_count": 0
            })

            errors.append({
                "query": query,
                "error": message
            })

    results = list(results_by_url.values())

    results.sort(
        key=lambda item: (
            item["source_priority"],
            item["domain"],
            item["title"].lower()
        )
    )

    return {
        "provider": "DDGS",
        "region": "in-en",
        "collected_at": collected_at,
        "queries_executed": len(queries),
        "successful_queries": sum(
            q["status"] == "success" for q in query_reports
        ),
        "empty_queries": sum(
            q["status"] == "no_results" for q in query_reports
        ),
        "failed_queries": sum(
            q["status"] == "error" for q in query_reports
        ),
        "total_unique_results": len(results),
        "query_reports": query_reports,
        "results": results,
        "errors": errors
    }
