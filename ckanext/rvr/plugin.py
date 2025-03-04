import logging
import ckan.plugins.toolkit as tk
import ckan.plugins as p
from ckan.lib.plugins import DefaultTranslation
from ckanext.rvr import helpers, validators, actions, views

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
