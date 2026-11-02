from typing import TypedDict


class DiscoveryState(TypedDict, total=False):

    user_request: str
    plan: dict
    error: str
