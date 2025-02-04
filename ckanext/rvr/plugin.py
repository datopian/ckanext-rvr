import requests
import logging
import json
from ckan.logic import schema as ckan_schema
from ckanext.rvr.helpers import is_valid_spatial

from ckanext.rvr.views.dataset import dataset_blueprint
from ckanext.rvr.views.organization import organization_blueprint
import logging
import ckan.plugins.toolkit as tk
import ckan.plugins as p
from ckan.lib.plugins import DefaultTranslation
from ckanext.rvr import actions as rvrActions
from ckanext.rvr.commands import rvr_spatial
from ckanext.rvr import helpers as rvrHelpers
import ckanext.rvr.views as rvrViews
from ckanext.spatial.plugin import SpatialQuery
from ckanext.dcat.interfaces import IDCATRDFHarvester

log = logging.getLogger(__name__)

config = tk.config
ignore_missing = tk.get_validator("ignore_missing")

licenses_url = tk.config.get("licenses_group_url")

def load_licenses(license_url):
    try:
        if license_url.startswith('file://'):
            with open(license_url.replace('file://', ''), 'r') as f:
                license_data = json.load(f)
            return license_data
        else:
            timeout = config.get('ckan.requests.timeout')
            response = requests.get(license_url, timeout=timeout)
            license_data = response.json()
            return license_data
    except requests.RequestException as e:
        msg = "Couldn't get the licenses file {}: {}".format(license_url, e)
        raise Exception(msg)
    except ValueError as e:
        msg = "Couldn't parse the licenses file {}: {}".format(license_url, e)
        raise Exception(msg)


licenses = load_licenses(licenses_url)
default_license_url = tk.config.get("ckanext.dcatde.harvest.default_license")


def _get_license_id(license_url):
    for license_item in licenses:
        if license_url == license_item["url"]:
            return license_item["id"]
    return None


def _set_license(dataset_dict):
    license_id = None
    resources = dataset_dict.get("resources", [])
    if len(resources) > 0:
        for resource in resources:
            if resource.get("license"):
                license_url = resource.get("license")
                break
            else:
                license_url = default_license_url

        license_id = _get_license_id(license_url)

        if license_id is not None:
            dataset_dict["license_id"] = license_id

        for resource in resources:
            if resource.get("license"):
                del resource["license"]
    else:
        license_url = default_license_url
        license_id = _get_license_id(license_url)
        if license_id is not None:
            dataset_dict["license_id"] = license_id


def _fix_spatial(dataset_dict):
    extras = dataset_dict.get("extras", [])    
    for field in extras:
        if field["key"] == "spatial":
            dataset_dict["spatial"] = field["value"]
            dataset_dict["dataset_spatial"] = field["value"]
            # Remove the spatial field from the extras
            extras.remove(field)
            break


class RvrPlugin(p.SingletonPlugin, tk.DefaultDatasetForm, DefaultTranslation):
    p.implements(p.ITranslation)
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IDatasetForm)
    p.implements(p.IFacets, inherit=True)
    p.implements(p.IBlueprint)
    p.implements(p.IActions)
    p.implements(IDCATRDFHarvester)
    p.implements(p.IPackageController, inherit=True)

    schema_options = {
        "default": [
            tk.get_validator("ignore_missing"),
            tk.get_converter("convert_to_extras"),
        ],
        "not_empty": [tk.get_validator("not_empty")],
    }

    # IBlueprint
    def get_blueprint(self):
        return [dataset_blueprint]

    # IConfigurer
    def update_config(self, config_):
        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")
        tk.add_resource("assets", "rvr")

    # ITemplateHelpers
    def get_helpers(self):
        """
        Register template helper functions.
        """
        return {
            "get_latest_created_datasets": rvrHelpers.get_latest_created_datasets,
            "build_nav_main": rvrHelpers.build_pages_nav_main,
            "get_specific_page": rvrHelpers.get_specific_page,
            "get_faq_page": rvrHelpers.get_faq_page,
            "get_facet_description": rvrHelpers.get_facet_description,
            "get_cookie_control_config": rvrHelpers.get_cookie_control_config,
        }

    # IBlueprint
    def get_blueprint(self):
        """Return a Flask blueprint to be registered in the app."""
        return rvrViews.get_rvr_blueprint()

    # IDatasetForm
    def create_package_schema(self):
        # let's grab the default schema in our pluginWS
        schema = super(RvrPlugin, self).create_package_schema()
        # our custom field
        schema.update(
            {
                "notes": self.schema_options["not_empty"],
                "owner_org": self.schema_options["not_empty"],
                "dataset_spatial": self.schema_options["default"],
                "spatial": self.schema_options["default"],
            }
        )
        return schema

    def update_package_schema(self):
        # let's grab the default schema in our plugin
        schema = super(RvrPlugin, self).update_package_schema()
        # our custom field
        schema.update(
            {
                "notes": self.schema_options["not_empty"],
                "owner_org": self.schema_options["not_empty"],
                "dataset_spatial": self.schema_options["default"],
                "spatial": self.schema_options["default"],
            }
        )
        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    # IFacets
    def dataset_facets(self, facets_dict, package_type):
        """
        Override core search fasets for datasets
        """
        facets_dict["date_filters"] = "Datumsfilter"
        return facets_dict

    # IActions
    def get_actions(self):
        """
        Define custom functions (or override existing ones).
        Available via API /api/action/{action-name}
        """
        return {
            "package_search": rvrActions.package_search,
            "package_show": rvrActions.package_show,
        }
    
    # IDCATRDFHarvester
    def before_download(self, url, harvest_job):
        return url, []
    
    def update_session(self, session):
        return session

    def after_download(self, content, harvest_job):
        return content, []

    def after_parsing(self, rdf_parser, harvest_job):
        return rdf_parser, []

    def before_create(self, harvest_object, dataset_dict, temp_dict):
        _set_license(dataset_dict)
        _fix_spatial(dataset_dict)

    def after_create(self, harvest_object, dataset_dict, temp_dict):
        return None
    
    def before_update(self, harvest_object, dataset_dict, temp_dict):
        _set_license(dataset_dict)
        _fix_spatial(dataset_dict)

    def after_update(self, harvest_object, dataset_dict, temp_dict):
        return None
    
    def update_package_schema_for_create(self, package_schema):
        # Ensure this method is properly defined
        return package_schema

    def update_package_schema_for_update(self, package_schema):
        # Ensure this method is properly defined
        return package_schema


class RvrSpatialQueryPlugin(SpatialQuery, tk.DefaultOrganizationForm):
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IClick)
    p.implements(p.ITemplateHelpers)

    # IClick
    def get_commands(self):
        return [rvr_spatial]

    # ITemplateHelpers
    def get_helpers(self):
        return {"is_valid_spatial": is_valid_spatial}

    # IBlueprint
    def get_blueprint(self):
        return [organization_blueprint]

    def is_fallback(self):
        return False

    def group_types(self):
        return ("organization",)

    # IGroupForm
    def form_to_db_schema(self):
        schema = ckan_schema.group_form_schema()
        schema.update(
            {
                "org_spatial": [
                    tk.get_validator("ignore_missing"),
                    tk.get_converter("convert_to_extras"),
                ]
            }
        )
        return schema

    def db_to_form_schema(self):
        schema = ckan_schema.default_show_group_schema()
        schema.update(
            {
                "org_spatial": [
                    tk.get_validator("ignore_missing"),
                    tk.get_converter("convert_to_extras"),
                ]
            }
        )
        return schema

    def group_form(self, group_type="organization"):
        return "organization/snippets/organization_form.html"

    def configure(self, config):
        self.search_backend = config.get("ckanext.spatial.search_backend", "postgis")
        if self.search_backend != "postgis" and not tk.check_ckan_version("2.0.1"):
            msg = (
                "The Solr backends for the spatial search require CKAN 2.0.1 or higher. "
                + "Please upgrade CKAN or select the 'postgis' backend."
            )
            raise tk.CkanVersionException(msg)
