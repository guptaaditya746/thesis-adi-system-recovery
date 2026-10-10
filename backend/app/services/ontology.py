from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef

from app.config import Settings
from app.models.domain import (
    OntologyChange,
    OntologyChangeOp,
    OntologyElement,
    OntologyProposal,
    SubOntologyArtifact,
)

GEN = Namespace("https://example.org/thesis/generated/")


class OntologyService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.seed = Graph()
        self.seed.parse(settings.seed_ontology_path, format="turtle")

    def inventory(self, limit: int = 500) -> list[OntologyElement]:
        out: list[OntologyElement] = []
        for uri in set(self.seed.subjects(RDF.type, OWL.Class)) | set(self.seed.subjects(RDF.type, RDFS.Class)):
            out.append(self._element(uri, "class"))
        props = set(self.seed.subjects(RDF.type, RDF.Property)) | set(self.seed.subjects(RDF.type, OWL.ObjectProperty)) | set(self.seed.subjects(RDF.type, OWL.DatatypeProperty))
        for uri in props:
            out.append(self._element(uri, "property"))
        return out[:limit]

    def search(self, terms: list[str], limit: int = 40) -> list[OntologyElement]:
        inventory = self.inventory(limit=2000)
        lowered = [t.lower() for t in terms if t]
        scored = []
        for item in inventory:
            hay = f"{item.label} {item.description or ''} {item.uri}".lower()
            score = sum(1 for term in lowered if term in hay)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda x: (-x[0], x[1].label))
        return [i for _, i in scored[:limit]]

    def build_subontology(self, proposal: OntologyProposal, path: Path) -> SubOntologyArtifact:
        graph = Graph()
        selected: list[OntologyElement] = []
        for uri_s in proposal.selected_uris:
            uri = URIRef(uri_s)
            for triple in self.seed.triples((uri, None, None)):
                graph.add(triple)
            for triple in self.seed.triples((None, None, uri)):
                if triple[1] in {RDFS.domain, RDFS.range, RDFS.subClassOf}:
                    graph.add(triple)
            kind = "property" if any(any(self.seed.triples((uri, RDF.type, t))) for t in [RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty]) else "class"
            selected.append(self._element(uri, kind))

        warnings: list[str] = []
        applied: list[OntologyChange] = []
        for change in proposal.changes:
            try:
                self._apply_change(graph, change)
                applied.append(change)
            except ValueError as exc:
                warnings.append(str(exc))

        path.parent.mkdir(parents=True, exist_ok=True)
        graph.serialize(path, format="turtle")
        return SubOntologyArtifact(
            turtle_path=str(path), selected_elements=selected,
            applied_changes=applied, validation_warnings=warnings,
        )

    def graph_from_artifact(self, artifact: SubOntologyArtifact) -> Graph:
        g = Graph()
        g.parse(artifact.turtle_path, format="turtle")
        return g

    def relation_catalog(self, artifact: SubOntologyArtifact) -> list[OntologyElement]:
        g = self.graph_from_artifact(artifact)
        out: list[OntologyElement] = []
        props = set(g.subjects(RDF.type, RDF.Property)) | set(g.subjects(RDF.type, OWL.ObjectProperty)) | set(g.subjects(RDF.type, OWL.DatatypeProperty))
        for uri in props:
            out.append(self._element_from_graph(g, uri, "property", source="generated" if str(uri).startswith(str(GEN)) else "seed"))
        return out

    def _element(self, uri: URIRef, kind: str) -> OntologyElement:
        return self._element_from_graph(self.seed, uri, kind, "seed")

    @staticmethod
    def _element_from_graph(g: Graph, uri: URIRef, kind: str, source: str) -> OntologyElement:
        label = next(iter(g.objects(uri, RDFS.label)), Literal(str(uri).rsplit("/", 1)[-1].rsplit("#", 1)[-1]))
        comment = next(iter(g.objects(uri, RDFS.comment)), None)
        domain = next(iter(g.objects(uri, RDFS.domain)), None)
        range_ = next(iter(g.objects(uri, RDFS.range)), None)
        return OntologyElement(
            uri=str(uri), label=str(label), kind=kind, description=str(comment) if comment else None,
            domain=str(domain) if domain else None, range=str(range_) if range_ else None,
            source=source,
        )

    def _apply_change(self, g: Graph, change: OntologyChange) -> None:
        if not self.settings.allow_ontology_extensions:
            raise ValueError(f"Ontology extensions disabled; rejected {change.op}")
        s = URIRef(change.subject_uri or f"{GEN}{quote(change.label or 'concept')}")
        o = URIRef(change.object_uri) if change.object_uri else None
        if change.op == OntologyChangeOp.ADD_CLASS:
            g.add((s, RDF.type, OWL.Class))
        elif change.op == OntologyChangeOp.ADD_PROPERTY:
            g.add((s, RDF.type, RDF.Property))
        elif change.op == OntologyChangeOp.ADD_SUBCLASS and o:
            g.add((s, RDFS.subClassOf, o))
        elif change.op == OntologyChangeOp.ADD_DOMAIN and o:
            g.add((s, RDFS.domain, o))
        elif change.op == OntologyChangeOp.ADD_RANGE and o:
            g.add((s, RDFS.range, o))
        else:
            raise ValueError(f"Invalid/incomplete ontology change: {change.model_dump()}")
        if change.label:
            g.add((s, RDFS.label, Literal(change.label)))
        if change.description:
            g.add((s, RDFS.comment, Literal(change.description)))
