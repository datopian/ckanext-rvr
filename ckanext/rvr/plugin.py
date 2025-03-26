import logging
import requests
import json
import ckan.plugins.toolkit as tk
import ckan.plugins as p
from ckan.lib.plugins import DefaultTranslation
from ckanext.rvr import helpers, validators, actions, views
from ckanext.dcat.interfaces import IDCATRDFHarvester
import ckan.logic as logic

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


def _set_dataset_groups(dataset_dict):
    if dataset_dict.get("groups"):
        for group in dataset_dict["groups"]:
            group_dict = logic.get_action('group_show')(
                {'ignore_auth': True},  # Use ignore_auth to bypass authentication
                {'id': group["id"]}  # Correctly structure the input
            )
            group_id = group_dict.get("id")
            if group_id:
                group["id"] = group_id
    

class RvrPlugin(p.SingletonPlugin, DefaultTranslation):
    p.implements(p.ITranslation)
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IFacets, inherit=True)
    p.implements(p.IBlueprint)
    p.implements(p.IActions)
    p.implements(p.IValidators)
    p.implements(IDCATRDFHarvester)
    p.implements(p.IPackageController, inherit=True)

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
            "get_latest_created_datasets": helpers.get_latest_created_datasets,
            "build_nav_main": helpers.build_pages_nav_main,
            "get_specific_page": helpers.get_specific_page,
            "get_faq_page": helpers.get_faq_page,
            "get_facet_description": helpers.get_facet_description,
            "get_cookie_control_config": helpers.get_cookie_control_config,
            "is_valid_spatial": helpers.is_valid_spatial,
        }

    # IBlueprint
    def get_blueprint(self):
        """Return a Flask blueprint to be registered in the app."""
        return views.get_rvr_blueprint()

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
            "package_search": actions.package_search,
            "package_show": actions.package_show,
            "package_create": actions.package_create,
            "package_update": actions.package_update,
        }

    # IValidators
    def get_validators(self):
        return {
            "spatial_validator": validators.spatial_validator,
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
        _set_dataset_groups(dataset_dict)

    def after_create(self, harvest_object, dataset_dict, temp_dict):
        return None
    
    def before_update(self, harvest_object, dataset_dict, temp_dict):
        _set_license(dataset_dict)
        _fix_spatial(dataset_dict)
        _set_dataset_groups(dataset_dict)

    def after_update(self, harvest_object, dataset_dict, temp_dict):
        return None
    
    def update_package_schema_for_create(self, package_schema):
        # Ensure this method is properly defined
        return package_schema

    def update_package_schema_for_update(self, package_schema):
        # Ensure this method is properly defined
        return package_schema