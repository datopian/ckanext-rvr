import cgi
import urllib
import logging
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
from ckanext.rvr import validators


log = logging.getLogger(__name__)

config = tk.config
ignore_missing = tk.get_validator("ignore_missing")


class RvrPlugin(p.SingletonPlugin, DefaultTranslation):
    p.implements(p.ITranslation)
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IFacets, inherit=True)
    p.implements(p.IBlueprint)
    p.implements(p.IActions)
    p.implements(p.IValidators)

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
            "is_valid_spatial": is_valid_spatial,
        }

    # IBlueprint
    def get_blueprint(self):
        """Return a Flask blueprint to be registered in the app."""
        return rvrViews.get_rvr_blueprint()

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
            "package_create": rvrActions.package_create,
            "package_update": rvrActions.package_update,
        }

    # IValidators
    def get_validators(self):
        return {
            "spatial_validator": validators.spatial_validator,
        }