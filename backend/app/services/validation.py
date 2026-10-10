from __future__ import annotations

from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef
from pyshacl import validate

from app.models.domain import CanonicalTriple, SubOntologyArtifact, ValidationReport

DATA = Namespace("https://example.org/thesis/data/")
SH = Namespace("http://www.w3.org/ns/shacl#")


class GraphValidationService:
    def build_graph(self, triples: list[CanonicalTriple]) -> Graph:
        g = Graph()
        for t in triples:
            s = URIRef(self._entity_uri(t.subject))
            p = URIRef(t.predicate_uri) if t.predicate_uri else URIRef(DATA + self._slug(t.predicate))
            if self._looks_literal(t.object):
                o = Literal(t.object)
            else:
                o = URIRef(self._entity_uri(t.object))
            g.add((s, p, o))
        return g

    def validate(self, triples: list[CanonicalTriple], ontology: SubOntologyArtifact) -> ValidationReport:
        data_graph = self.build_graph(triples)
        ontology_graph = Graph().parse(ontology.turtle_path, format="turtle")
        shapes = self._shapes_from_domains_ranges(ontology_graph)
        try:
            conforms, _, report_text = validate(
                data_graph=data_graph,
                shacl_graph=shapes,
                ont_graph=ontology_graph,
                inference="rdfs",
                abort_on_first=False,
            )
            return ValidationReport(
                rdf_valid=True,
                shacl_conforms=bool(conforms),
                shacl_report=str(report_text),
            )
        except Exception as exc:
            return ValidationReport(rdf_valid=False, shacl_conforms=False, shacl_report=str(exc))

    def _shapes_from_domains_ranges(self, ontology: Graph) -> Graph:
        shapes = Graph()
        for prop, domain in ontology.subject_objects(RDFS.domain):
            shape = URIRef(str(prop) + "Shape")
            pshape = BNode()
            shapes.add((shape, RDF.type, SH.NodeShape))
            shapes.add((shape, SH.targetSubjectsOf, prop))
            shapes.add((shape, SH["class"], domain))
            shapes.add((shape, SH.property, pshape))
            shapes.add((pshape, SH.path, prop))
            range_ = next(iter(ontology.objects(prop, RDFS.range)), None)
            if (prop, RDF.type, OWL.ObjectProperty) in ontology:
                shapes.add((pshape, SH.nodeKind, SH.IRI))
            elif (prop, RDF.type, OWL.DatatypeProperty) in ontology:
                shapes.add((pshape, SH.nodeKind, SH.Literal))
            if range_ and (prop, RDF.type, OWL.ObjectProperty) in ontology:
                shapes.add((pshape, SH["class"], range_))
        return shapes

    @staticmethod
    def _slug(text: str) -> str:
        return "_".join(text.strip().replace("/", " ").split())

    @classmethod
    def _entity_uri(cls, text: str) -> str:
        return str(DATA) + cls._slug(text)

    @staticmethod
    def _looks_literal(text: str) -> bool:
        return text.startswith('"') or text.replace(".", "", 1).isdigit()
