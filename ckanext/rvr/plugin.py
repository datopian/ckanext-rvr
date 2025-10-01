import logging
import requests
import json
import ckan.plugins.toolkit as tk
import ckan.plugins as p
from ckan.lib.plugins import DefaultTranslation
from ckanext.rvr import helpers, validators, actions, views
from ckanext.dcat.interfaces import IDCATRDFHarvester
import ckan.logic as logic

# Make scheming import safe
try:
    from ckanext.scheming.helpers import scheming_get_dataset_schema
except ImportError:
    scheming_get_dataset_schema = None

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
    

def _assign_extras_to_top_level(dataset_dict, schema_fields=None):
    def normalize(s):
        return s.strip().lower().replace('-', '_').replace(' ', '_')

    if (
        not schema_fields or "extras" not in dataset_dict or
        not isinstance(dataset_dict["extras"], list)
    ):
        return
    field_map = {normalize(f): f for f in schema_fields}
    for extra in list(dataset_dict["extras"]):
        key = extra.get("key")
        if key is not None and normalize(key) in field_map:
            field_name = field_map[normalize(key)]
            if field_name not in dataset_dict:
                dataset_dict[field_name] = extra.get("value")


def _normalize_dataset_dict(dataset_dict):
    """
    Shared normalization logic for before_create and before_update.
    Handles extras assignment, duplicate removal, spatial/group fix, and
    schema-compliant normalization.
    """
    schema = scheming_get_dataset_schema(dataset_dict.get('type', 'dataset')) if scheming_get_dataset_schema else None
    schema_fields = []
    if schema and 'dataset_fields' in schema:
        schema_fields = [
            f['field_name'] for f in schema['dataset_fields'] if 'field_name' in f
        ]
    _assign_extras_to_top_level(dataset_dict, schema_fields)
    _remove_duplicate_extras(dataset_dict, schema_fields)

    def normalize(s):
        return s.strip().lower().replace('-', '_').replace(' ', '_')

    if 'extras' in dataset_dict and isinstance(dataset_dict['extras'], list):
        top_level_keys = set(
            normalize(k) for k in dataset_dict.keys() if k != 'extras'
        )
        cleaned_extras = [
            e for e in dataset_dict['extras']
            if e.get('key') is not None and normalize(e.get('key')) not in top_level_keys
        ]
        dataset_dict['extras'] = cleaned_extras
    print(f"========================> Normalized dataset_dict: {dataset_dict}")
    _set_license(dataset_dict)
    _fix_spatial(dataset_dict)
    _set_dataset_groups(dataset_dict)

    # --- BEGIN: Schema-compliant normalization for applicable_legislation and hvd_category (AFTER extras assignment) ---
    if 'applicable_legislation' in dataset_dict:
        val = dataset_dict['applicable_legislation']
        if isinstance(val, str) and val.startswith('['):
            try:
                import json
                parsed = json.loads(val)
                if isinstance(parsed, list) and parsed:
                    val = str(parsed[0])
                    dataset_dict['applicable_legislation'] = val
            except Exception:
                pass
        val = dataset_dict['applicable_legislation']
        if not (isinstance(val, str) and val.startswith('http')):
            raise Exception(
                f"Skipping dataset: invalid applicable_legislation: {val}"
            )
        dataset_dict['applicable_legislation'] = str(val)

    try:
        from ckanext.rvr.profiles import HVD_CATEGORY_MAPPING
    except ImportError:
        HVD_CATEGORY_MAPPING = {}

    uri_to_label = {v: k for k, v in HVD_CATEGORY_MAPPING.items()}
    allowed_hvd_labels = set(HVD_CATEGORY_MAPPING.keys())

    if 'hvd_category' in dataset_dict:
        val = dataset_dict['hvd_category']
        if isinstance(val, str) and val.startswith('['):
            try:
                import json
                parsed = json.loads(val)
                if isinstance(parsed, list) and parsed:
                    val = str(parsed[0])
                    dataset_dict['hvd_category'] = val
            except Exception:
                pass
        val = dataset_dict['hvd_category']
        if val in uri_to_label:
            dataset_dict['hvd_category'] = str(uri_to_label[val])
        elif val in allowed_hvd_labels:
            dataset_dict['hvd_category'] = str(val)
        else:
            raise Exception(
                f"Skipping dataset: invalid hvd_category: {val}"
            )
        dataset_dict['hvd_category'] = str(dataset_dict['hvd_category'])
    # --- END: Schema-compliant normalization ---
    return dataset_dict


def _remove_duplicate_extras(dataset_dict, schema_fields=None):
    def normalize(s):
        return s.strip().lower().replace('-', '_').replace(' ', '_')

    if "extras" in dataset_dict and isinstance(dataset_dict["extras"], list):
        field_set = set()
        if schema_fields is not None:
            field_set.update(normalize(f) for f in schema_fields)
        cleaned_extras = [
            e for e in dataset_dict["extras"]
            if e.get("key") is not None and normalize(e.get("key")) not in field_set
        ]
        dataset_dict["extras"] = cleaned_extras


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
        # --- END: Normalize/fix specific fields ---
        return _normalize_dataset_dict(dataset_dict)

    def after_create(self, harvest_object, dataset_dict, temp_dict):
        return None
    
    def before_update(self, harvest_object, dataset_dict, temp_dict):
        # --- END: Normalize/fix specific fields ---
        return _normalize_dataset_dict(dataset_dict)

    def after_update(self, harvest_object, dataset_dict, temp_dict):
        return None
    
    def update_package_schema_for_create(self, package_schema):
        # Ensure this method is properly defined
        return package_schema

    def update_package_schema_for_update(self, package_schema):
        # Ensure this method is properly defined
        return package_schema