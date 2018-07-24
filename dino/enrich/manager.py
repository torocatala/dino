from dino.environ import GNEnvironment
from dino.enrich import IEnrichmentManager


class EnrichmentManager(IEnrichmentManager):
    def __init__(self, env: GNEnvironment):
        self.env = env

    def handle(self, data: dict) -> dict:
        enriched = data.copy()
        for _, enrich in self.env.enrichers:
            enriched = enrich(enriched)
        return enriched
