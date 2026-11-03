"""Resolve search results and LinkedIn listing pages to vacancy URLs."""

from app.services.document_extraction_service import extract_document
from app.services.linkedin_link_service import extract_links_from_page
from app.services.listing_parser import extract_linkedin_listings
from app.services.search_service import normalize_url
from app.services.workflow_document_processor import WorkflowDocumentProcessor
from app.services.workflow_matching import match_listing_candidates


def resolve_search_results(search_results, processor: WorkflowDocumentProcessor):
    for result in search_results:
        if processor.attempted_documents >= processor.max_results:
            break
        source_url = result.get("url", "")
        normalized_source = normalize_url(source_url)
        if not normalized_source or normalized_source in processor.seen_sources:
            continue
        processor.seen_sources.add(normalized_source)

        is_linkedin_listing = (
            "linkedin.com/jobs/" in source_url.casefold()
            and "/jobs/view/" not in source_url.casefold()
        )
        if is_linkedin_listing:
            _resolve_linkedin_listing(source_url, processor)
            continue

        processor.process(
            source_url,
            result.get("title", "Untitled source"),
            result.get("source_type", "unknown"),
            discovery_result=result,
        )


def _resolve_linkedin_listing(source_url, processor):
    try:
        page = extract_document(source_url)
        processor.retrieved_documents.append({
            "requested_url": source_url,
            "final_url": page.get("final_url"),
            "fetch_status": page.get("fetch_status"),
            "extraction_status": page.get("extraction_status"),
            "characters_extracted": len(page.get("extracted_text", "")),
        })
        if page.get("extraction_status") != "extracted":
            processor.errors.append({
                "stage": "listing_fetch",
                "url": source_url,
                "error": page.get("error") or page.get("fetch_status"),
            })
            return

        candidates = extract_linkedin_listings(page["extracted_text"])
        link_result = extract_links_from_page(source_url)
        if link_result.get("fetch_status") != "fetched":
            processor.errors.append({
                "stage": "listing_link_resolution",
                "url": source_url,
                "error": link_result.get("error") or link_result.get("fetch_status"),
            })
            return

        matched, review = match_listing_candidates(
            candidates, link_result.get("links", [])
        )
        processor.listing_match_review.extend({
            **item,
            "source_page_url": source_url,
        } for item in review)
        for candidate, link in matched:
            if processor.attempted_documents >= processor.max_results:
                break
            processor.process(
                link["job_url"],
                candidate["opportunity_title"],
                "individual_linkedin_job",
                candidate_metadata={
                    "candidate_title": candidate["opportunity_title"],
                    "candidate_organization": candidate["organization"],
                    "candidate_location": candidate["location"],
                },
                discovery_result={
                    "source_adapter": "linkedin",
                    "original_source_url": source_url,
                    "title": candidate["opportunity_title"],
                },
            )
    except Exception as error:
        processor.errors.append({
            "stage": "listing_parse_or_match",
            "url": source_url,
            "error": f"{type(error).__name__}: {str(error)[:500]}",
        })
