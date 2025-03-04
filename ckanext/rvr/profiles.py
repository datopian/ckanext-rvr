import json
import rdflib
import ckan.plugins.toolkit as tk
from rdflib.namespace import Namespace
from rdflib import URIRef, BNode, Literal
from rdflib.namespace import Namespace, RDF, RDFS
from ckanext.dcat.profiles import EuropeanDCATAP2Profile, URIRefOrLiteral, CleanedURIRef
from ckanext.dcat.utils import resource_uri, dataset_uri
from ckanext.dcatde.profiles import DCATdeProfile

DCT = Namespace("http://purl.org/dc/terms/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCATAP = Namespace("http://data.europa.eu/r5r/")
DCATDE = Namespace("http://dcat-ap.de/def/dcatde/")

DCAT_THEME_PREFIX = "http://publications.europa.eu/resource/authority/data-theme/"


HVD_CATEGORY_MAPPING = {
    "meteorological": "http://data.europa.eu/bna/c_164e0bf5",
    "Meteorologie": "http://data.europa.eu/bna/c_164e0bf5",
    "companies-and-company-ownership": "http://data.europa.eu/bna/c_a9135398",
    "unternehmen-und-unternehmenseigentum": "http://data.europa.eu/bna/c_a9135398",
    "geospatial": "http://data.europa.eu/bna/c_ac64a52d",
    "Georaum": "http://data.europa.eu/bna/c_ac64a52d",
    "mobility": "http://data.europa.eu/bna/c_b79e35eb",
    "mobilität": "http://data.europa.eu/bna/c_b79e35eb",
    "earth-observation-and-environment": "http://data.europa.eu/bna/c_dd313021",
    "erdbeobachtung-und-umwelt": "http://data.europa.eu/bna/c_dd313021",
    "statistical": "http://data.europa.eu/bna/c_e1da4e07",
    "statistik": "http://data.europa.eu/bna/c_e1da4e07",
}


class DCATdeHVDProfile(DCATdeProfile):
    """
    An RDF profile for the Dublin Core Terms with custom metadata mappings.
    """

    def parse_dataset(self, dataset_dict, dataset_ref):
        # call super method

        super(DCATdeProfile, self).parse_dataset(dataset_dict, dataset_ref)

        return dataset_dict

    def graph_from_dataset(self, dataset_dict: dict, dataset_ref: URIRef) -> None:
        """
        Add RDF triples to the graph from the dataset.

        Args:
            dataset_dict (dict): The dataset dictionary.
            dataset_ref (URIRef): The dataset reference.
        """
        super(DCATdeProfile, self).graph_from_dataset(dataset_dict, dataset_ref)

        g = self.g
        hvd_category = dataset_dict.get("hvd_category", "")
        applicable_legislation = dataset_dict.get("applicable_legislation", "")
        if applicable_legislation:
            g.add(
                (
                    dataset_ref,
                    DCATAP.applicableLegislation,
                    URIRef(dataset_dict.get("applicable_legislation", "")),
                )
            )
        if hvd_category in HVD_CATEGORY_MAPPING:
            g.add(
                (
                    dataset_ref,
                    DCATAP.hvdCategory,
                    URIRef(HVD_CATEGORY_MAPPING[hvd_category]),
                )
            )

    def graph_from_catalog(self, catalog_dict):
        super(DCATdeProfile, self).graph_from_catalog(catalog_dict)
