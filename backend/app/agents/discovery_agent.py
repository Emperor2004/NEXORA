import re

from pydantic import BaseModel, Field

from app.services.llm_service import generate_structured_output


class DiscoveryPlan(BaseModel):
    search_queries: list[str] = Field(
        description="Specific search queries for discovering internship opportunities"
    )
    target_domains: list[str] = Field(
        description="Technical subject areas only, such as AI, machine learning, computer vision, NLP, robotics"
    )
    hard_constraints: list[str] = Field(
        description="Mandatory requirements every opportunity must satisfy"
    )
    preferences: list[str] = Field(
        description="Ranking preferences, not rejection criteria"
    )
    keywords: list[str] = Field(
        description="Relevant search and classification keywords"
    )
    exclusions: list[str] = Field(
        description="Only categories explicitly rejected by the user"
    )
    reasoning: str = Field(
        description="Explanation of the discovery strategy"
    )


class DiscoveryAgent:

    DOMAIN_TAXONOMY = {
        "Artificial Intelligence": [
            r"\bAI\b",
            r"artificial intelligence"
        ],
        "Computer Vision": [
            r"computer vision"
        ],
        "Machine Learning": [
            r"\bML\b",
            r"machine learning"
        ],
        "Deep Learning": [
            r"deep learning"
        ],
        "Natural Language Processing": [
            r"\bNLP\b",
            r"natural language processing"
        ],
        "Robotics": [
            r"robotics"
        ],
        "Data Science": [
            r"data science"
        ],
        "Reinforcement Learning": [
            r"reinforcement learning"
        ]
    }

    def extract_domains(self, user_request: str) -> list[str]:
        domains = []

        for domain, patterns in self.DOMAIN_TAXONOMY.items():
            if any(
                re.search(pattern, user_request, re.IGNORECASE)
                for pattern in patterns
            ):
                domains.append(domain)

        return domains

    def extract_explicit_exclusions(
        self, user_request: str
    ) -> list[str]:

        patterns = [
            r"(?:exclude|avoid|do not include|don't include)\s+([^.;\n]+)"
        ]

        exclusions = []

        for pattern in patterns:
            matches = re.findall(
                pattern,
                user_request,
                re.IGNORECASE
            )

            exclusions.extend(
                match.strip(" ,.")
                for match in matches
                if match.strip(" ,.")
            )

        return exclusions

    def execute(self, user_request: str) -> dict:

        system_prompt = """
You are the Discovery Planning Agent of NEXORA AI.

Convert internship requests into structured discovery plans.

RULES:

1. Separate mandatory constraints from ranking preferences.
2. Paid only, location, start date and duration are hard constraints.
3. Prioritize, prefer and focus on indicate preferences.
4. Never convert preferences into exclusions.
5. Exclusions must contain only categories explicitly rejected.
6. Technical domains must contain technical subjects only.
   Examples: Artificial Intelligence, Computer Vision,
   Machine Learning, NLP and Robotics.
7. Government institutes, universities and private companies
   are organization or source categories, not technical domains.
8. Include private organizations when the user requests them.
9. Never invent openings, deadlines, stipends or application links.
10. Generate targeted search queries.
11. Return data matching the requested JSON schema.
"""

        output = generate_structured_output(
            system_prompt=system_prompt,
            user_prompt=user_request,
            output_schema=DiscoveryPlan.model_json_schema()
        )

        plan = DiscoveryPlan.model_validate(output)

        # Deterministic safeguards
        plan.target_domains = self.extract_domains(user_request)

        plan.exclusions = self.extract_explicit_exclusions(
            user_request
        )

        return plan.model_dump()
