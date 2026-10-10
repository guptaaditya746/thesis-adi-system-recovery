from dataclasses import dataclass

from app.config import Settings
from app.models.domain import ScientificDocument
from app.services.ontology import OntologyService
from app.services.retrieval import RetrievalService


@dataclass
class AgentDeps:
    settings: Settings
    document: ScientificDocument
    retrieval: RetrievalService
    ontology: OntologyService
