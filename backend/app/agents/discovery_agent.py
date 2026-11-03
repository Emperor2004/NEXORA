import re

from pydantic import BaseModel, Field

from app.services.llm_service import generate_structured_output
from app.agents.registry import get_agent_profile
from app.services.prompt_registry import load_agent_prompt


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

    def execute(
        self,
        user_request: str,
        timeout_seconds: int = 90,
        max_output_tokens: int = 2048,
        allowed_providers: tuple[str, ...] | list[str] | None = None,
    ) -> dict:

        profile = get_agent_profile("discovery_planner")
        prompt = load_agent_prompt("discovery_planner")
        system_prompt = f"{profile.system_instructions}\n\n{prompt['content']}"

        output = generate_structured_output(
            system_prompt=system_prompt,
            user_prompt=user_request,
            output_schema=DiscoveryPlan.model_json_schema(),
            timeout_seconds=timeout_seconds or profile.timeout_seconds,
            max_output_tokens=max_output_tokens or profile.max_output_tokens,
            allowed_providers=allowed_providers or profile.allowed_providers,
        )

        plan = DiscoveryPlan.model_validate(output)

        # Deterministic safeguards
        plan.target_domains = self.extract_domains(user_request)

        plan.exclusions = self.extract_explicit_exclusions(
            user_request
        )

        return plan.model_dump()
