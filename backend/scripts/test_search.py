import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.search_service import search_internships


queries = [
    "paid AI research internship India January 2027 4 to 6 months site:gov.in",
    "computer vision research internship India January 2027 site:ac.in",
    "paid AI research internship India January 2027 private research organization"
]

print("Starting NEXORA live search...")

report = search_internships(
    queries=queries,
    max_results_per_query=3
)

project_root = Path(__file__).resolve().parents[2]

output_directory = project_root / "data" / "discovery_runs"
output_directory.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

output_file = output_directory / f"search_{timestamp}.json"

output_file.write_text(
    json.dumps(report, indent=4, ensure_ascii=False),
    encoding="utf-8"
)

print("\nSEARCH SUMMARY")
print("------------------------------")
print("Provider:", report["provider"])
print("Queries executed:", report["queries_executed"])
print("Successful queries:", report["successful_queries"])
print("Failed queries:", report["failed_queries"])
print("Unique results:", report["total_unique_results"])
print("Saved file:", output_file)

print("\nDISCOVERED RESULTS")
print("------------------------------")

for index, item in enumerate(report["results"], start=1):

    print(f"\n{index}. {item['title']}")
    print("   Domain:", item["domain"])
    print("   Source type:", item["source_type"])
    print("   URL:", item["url"])
    print("   Evidence:", item["evidence_status"])

if report["errors"]:
    print("\nSEARCH ERRORS")

    for error in report["errors"]:
        print(error)
