from pathlib import Path

path = Path("app/agents/opportunity_extraction_agent.py")
source = path.read_text(encoding="utf-8")

old = '''    # Job-board search pages and pages listing multiple vacancies.
    if (
        "linkedin.com/jobs/" in url
        or "glassdoor." in url
        or re.search(r"\\d+\\s+(open\\s+)?(roles|jobs)\\b", title)
    ):
        return "listing_page", "job_board_or_multiple_job_results"
'''

new = '''    # An individual LinkedIn vacancy detail page is not a search-results page.
    if "linkedin.com/jobs/view/" in url:
        return "individual_announcement", "individual_linkedin_job_detail_page"

    # Job-board search pages and pages listing multiple vacancies.
    if (
        ("linkedin.com/jobs/" in url and "/jobs/view/" not in url)
        or "glassdoor." in url
        or re.search(r"\\d+\\s+(open\\s+)?(roles|jobs)\\b", title)
    ):
        return "listing_page", "job_board_or_multiple_job_results"
'''

if source.count(old) != 1:
    raise RuntimeError(
        "Expected classifier block was not found exactly once. "
        "No changes were made."
    )

source = source.replace(old, new)

old_limit = "    text_limit = 10_000"
new_limit = "    text_limit = 20_000"

if source.count(old_limit) != 1:
    raise RuntimeError(
        "Expected text limit was not found exactly once. "
        "No changes were made."
    )

source = source.replace(old_limit, new_limit)

path.write_text(source, encoding="utf-8")

print("Classifier updated successfully.")
print("Individual LinkedIn job pages now classify as individual_announcement.")
print("LLM extraction text limit increased from 10,000 to 20,000 characters.")
