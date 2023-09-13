import logging
import ckan.plugins.toolkit as tk
import ckan.plugins as p
from ckan.lib.plugins import DefaultTranslation
from ckanext.rvr import actions as rvrActions
from ckanext.rvr import helpers as rvrHelpers
import ckanext.rvr.views as rvrViews
from ckanext.spatial.plugin import SpatialQuery

log = logging.getLogger(__name__)

config = tk.config
ignore_missing = tk.get_validator('ignore_missing')

class RvrPlugin(p.SingletonPlugin, tk.DefaultDatasetForm, DefaultTranslation):
    p.implements(p.ITranslation)
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IDatasetForm)
    p.implements(p.IFacets, inherit=True)
    p.implements(p.IBlueprint)
    p.implements(p.IActions)
    
    # IConfigurer
    def update_config(self, config_):
        tk.add_template_directory(config_, 'templates')
        tk.add_public_directory(config_, 'public')
        tk.add_resource('assets', 'rvr')

    # ITemplateHelpers
    def get_helpers(self):
        '''
        Register template helper functions.
        '''
        return {
            'get_newest_datasets': rvrHelpers.get_newest_datasets,
            'build_nav_main': rvrHelpers.build_pages_nav_main,
            'get_specific_page': rvrHelpers.get_specific_page,
            'get_faq_page': rvrHelpers.get_faq_page,
            'get_facet_description': rvrHelpers.get_facet_description,
            'get_cookie_control_config': rvrHelpers.get_cookie_control_config
        }
    
    # IBlueprint
    def get_blueprint(self):
        '''Return a Flask blueprint to be registered in the app.'''
        return rvrViews.get_rvr_blueprint()

    # IDatasetForm
    def create_package_schema(self):
        # let's grab the default schema in our plugin
        schema = super(RvrPlugin, self).create_package_schema()
        # our custom field
        schema.update({
            'notes': [tk.get_validator('not_empty')],
            'owner_org': [tk.get_validator('not_empty')],
        })
        return schema

    def update_package_schema(self):
        # let's grab the default schema in our plugin
        schema = super(RvrPlugin, self).update_package_schema()
        # our custom field
        schema.update({
            'notes': [tk.get_validator('not_empty')],
            'owner_org': [tk.get_validator('not_empty')],
        })
        return schema
        
    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []
    
    #IFacets
    def dataset_facets(self, facets_dict, package_type):
        '''
        Override core search fasets for datasets
        '''
        facets_dict['date_filters'] = "Datumsfilter"
        return facets_dict

    # IActions
    def get_actions(self):
        '''
        Define custom functions (or override existing ones).
        Available via API /api/action/{action-name}
        '''
        return {
            'package_search': rvrActions.package_search
        }

class RvrSpatialQueryPlugin(SpatialQuery):

    def configure(self, config):
        self.search_backend = config.get('ckanext.spatial.search_backend', 'postgis')
        if self.search_backend != 'postgis' and not tk.check_ckan_version('2.0.1'):
            msg = 'The Solr backends for the spatial search require CKAN 2.0.1 or higher. ' + \
                  'Please upgrade CKAN or select the \'postgis\' backend.'
            raise tk.CkanVersionException(msg)