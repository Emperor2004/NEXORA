"""Search adapters for public internship sources.

Adapters express source-specific search constraints while leaving retrieval to
the existing bounded HTTP document service. They do not bypass logins, paywalls,
robots policies, or other access controls.
"""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SourceAdapter:
    key: str
    label: str
    query_suffix: str
    source_type: str
    priority: int

    def build_query(self, intent: str) -> str:
        return f"{intent} {self.query_suffix}".strip()


SOURCE_ADAPTERS = (
    SourceAdapter("government", "Government portals", "internship site:gov.in OR site:nic.in", "government_domain", 1),
    SourceAdapter("research", "Research institutions", "internship research laboratory institute India", "research_institution", 1),
    SourceAdapter("universities", "Universities", "internship site:ac.in OR site:edu.in", "academic_domain", 2),
    SourceAdapter("company_careers", "Company career pages", 'internship "careers" official company', "company_careers", 2),
    SourceAdapter("internshala", "Internshala", "site:internshala.com/internship", "job_board", 3),
    SourceAdapter("indeed", "Indeed", "site:in.indeed.com/viewjob OR site:indeed.com/viewjob", "job_board", 3),
    SourceAdapter("naukri", "Naukri", "site:naukri.com/internship-jobs", "job_board", 3),
    SourceAdapter("foundit", "Foundit", "site:foundit.in internship", "job_board", 3),
    SourceAdapter("wellfound", "Wellfound", "site:wellfound.com/jobs internship", "job_board", 3),
    SourceAdapter("linkedin", "LinkedIn", "site:linkedin.com/jobs/view", "job_board", 4),
)

_SOURCE_HOSTS = {
    "internshala.com": "internshala",
    "indeed.com": "indeed",
    "naukri.com": "naukri",
    "foundit.in": "foundit",
    "wellfound.com": "wellfound",
    "linkedin.com": "linkedin",
}


def source_for_url(url: str) -> dict:
    from urllib.parse import urlsplit

    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    for suffix, adapter in _SOURCE_HOSTS.items():
        if host == suffix or host.endswith("." + suffix):
            return {"adapter": adapter, "source_type": "job_board", "priority": 3}
    if host.endswith((".gov.in", ".nic.in")):
        return {"adapter": "government", "source_type": "government_domain", "priority": 1}
    if host.endswith((".ac.in", ".edu.in")):
        return {"adapter": "universities", "source_type": "academic_domain", "priority": 2}
    path = urlsplit(url).path.casefold()
    if any(token in path for token in ("/careers", "/career", "/work-with-us", "/jobs/", "/job/")):
        return {"adapter": "company_careers", "source_type": "company_careers", "priority": 2}
    return {"adapter": "web", "source_type": "other_domain", "priority": 3}


def build_source_queries(intent: str, adapters=None) -> list[dict]:
    selected = tuple(adapters or SOURCE_ADAPTERS)
    base = re.sub(r"\s+", " ", (intent or "internship").strip())
    return [
        {"adapter": item.key, "label": item.label, "query": item.build_query(base),
         "source_type": item.source_type, "priority": item.priority}
        for item in selected
    ]
