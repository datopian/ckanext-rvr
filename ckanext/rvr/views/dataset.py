# encoding: utf-8
import logging
from collections import OrderedDict
from functools import partial
from six.moves.urllib.parse import urlencode

from flask import Blueprint
from werkzeug.datastructures import MultiDict
from ckan.common import asbool

import six
from six import string_types

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as plugins
from ckan.common import _, config, g, request
from ckan.lib.plugins import lookup_package_plugin
from ckan.lib.search import SearchError, SearchQueryError


NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

log = logging.getLogger(__name__)

dataset_blueprint = Blueprint(
    'rvr_dataset', __name__,
    url_prefix=u'/dataset',
    url_defaults={u'package_type': u'dataset'}
)

def _setup_template_variables(context, data_dict, package_type=None):
    return lookup_package_plugin(package_type).setup_template_variables(
        context, data_dict
    )


def _get_pkg_template(template_type, package_type=None):
    pkg_plugin = lookup_package_plugin(package_type)
    method = getattr(pkg_plugin, template_type)
    try:
        return method(package_type)
    except TypeError as err:
        if u'takes 1' not in str(err) and u'takes exactly 1' not in str(err):
            raise
        return method()


def _encode_params(params):
    return [(k, v.encode(u'utf-8') if isinstance(v, string_types) else str(v))
            for k, v in params]


def url_with_params(url, params):
    params = _encode_params(params)
    return url + u'?' + urlencode(params)


def search_url(params, package_type=None):
    if not package_type:
        package_type = u'dataset'
    url = h.url_for(u'{0}.search'.format(package_type))
    return url_with_params(url, params)


def drill_down_url(alternative_url=None, **by):
    return h.add_url_param(
        alternative_url=alternative_url,
        controller=u'dataset',
        action=u'search',
        new_params=by
    )


def remove_field(package_type, key, value=None, replace=None):
    if not package_type:
        package_type = u'dataset'
    url = h.url_for(u'{0}.search'.format(package_type))
    return h.remove_url_param(
        key,
        value=value,
        replace=replace,
        alternative_url=url
    )


def _sort_by(params_nosort, package_type, fields):
    """Sort by the given list of fields.

    Each entry in the list is a 2-tuple: (fieldname, sort_order)
    eg - [(u'metadata_modified', u'desc'), (u'name', u'asc')]
    If fields is empty, then the default ordering is used.
    """
    params = params_nosort[:]

    if fields:
        sort_string = u', '.join(u'%s %s' % f for f in fields)
        params.append((u'sort', sort_string))
    return search_url(params, package_type)


def _pager_url(params_nopage, package_type, q=None, page=None):
    params = list(params_nopage)
    params.append((u'page', page))
    return search_url(params, package_type)

def _get_search_details():
    fq = u''

    # fields_grouped will contain a dict of params containing
    # a list of values eg {u'tags':[u'tag1', u'tag2']}

    fields = []
    fields_grouped = {}
    search_extras = MultiDict()

    for (param, value) in request.args.items(multi=True):
        if param not in [u'q', u'page', u'sort'] \
                and len(value) and not param.startswith(u'_'):
            if not param.startswith(u'ext_'):
                fields.append((param, value))
                fq += u' %s:"%s"' % (param, value)
                if param not in fields_grouped:
                    fields_grouped[param] = [value]
                else:
                    fields_grouped[param].append(value)
            else:
                search_extras.update({param: value})

    search_extras = dict([
        (k, v[0]) if len(v) == 1 else (k, v)
        for k, v in search_extras.lists()
    ])
    return {
        u'fields': fields,
        u'fields_grouped': fields_grouped,
        u'fq': fq,
        u'search_extras': search_extras,
    }

def search(package_type):
    extra_vars = {}

    try:
        context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        check_access(u'site_read', context)
    except NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    # unicode format (decoded from utf8)
    extra_vars[u'q'] = q = request.args.get(u'q', u'')

    # Get Active date range filter
    active_range = request.args.get('_active_range')
    # Get Daterange fields
    dateranges = {
        'metadata_created': {
            'title': 'erstellt',
            'params': [
                request.args.get('_metadata_created_start', ''),
                request.args.get('_metadata_created_end', '')
            ]
        },
        'metadata_modified': {
            'title': 'zuletzt aktualisiert',
            'params': [
                request.args.get('_metadata_modified_start', ''),
                request.args.get('_metadata_modified_end', '')
            ]
        },
        'issued': {
            'title': 'veröffentlicht',
            'params': [
                request.args.get('_issued_start', ''),
                request.args.get('_issued_end', '')
            ],
        },
        'modified': {
            'title': 'zuletzt geändert',
            'params': [
                request.args.get('_modified_start', ''),
                request.args.get('_modified_end', '')
            ]
        }
    }
    # Set default if a valid active_range was not sent by the user
    if active_range not in dateranges.keys():
        active_range = 'metadata_created'
    # Generate date range options list to be sent to the client
    daterange_options = []
    for k, v in dateranges.items():
        daterange_options.append({
            'name': k,
            'title': v['title']
        })

    extra_vars['query_error'] = False
    page = h.get_page_number(request.args)

    limit = int(config.get(u'ckan.datasets_per_page', 20))

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.args.items(multi=True)
                     if k != u'page']

    extra_vars[u'drill_down_url'] = drill_down_url
    extra_vars[u'remove_field'] = partial(remove_field, package_type)

    sort_by = request.args.get(u'sort', None)
    params_nosort = [(k, v) for k, v in params_nopage if k != u'sort']

    extra_vars[u'sort_by'] = partial(_sort_by, params_nosort, package_type)

    if not sort_by:
        sort_by_fields = []
    else:
        sort_by_fields = [field.split()[0] for field in sort_by.split(u',')]
    extra_vars[u'sort_by_fields'] = sort_by_fields

    pager_url = partial(_pager_url, params_nopage, package_type)

    search_url_params = urlencode(_encode_params(params_nopage))
    extra_vars[u'search_url_params'] = search_url_params

    details = _get_search_details()
    extra_vars[u'fields'] = details[u'fields']
    extra_vars[u'fields_grouped'] = details[u'fields_grouped']
    fq = details[u'fq']
    search_extras = details[u'search_extras']

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'auth_user_obj': g.userobj
    }

    # Unless changed via config options, don't show other dataset
    # types any search page. Potential alternatives are do show them
    # on the default search page (dataset) or on one other search page
    search_all_type = config.get(u'ckan.search.show_all_types', u'dataset')
    search_all = False

    try:
        # If the "type" is set to True or False, convert to bool
        # and we know that no type was specified, so use traditional
        # behaviour of applying this only to dataset type
        search_all = asbool(search_all_type)
        search_all_type = u'dataset'
    # Otherwise we treat as a string representing a type
    except ValueError:
        search_all = True

    if not search_all or package_type != search_all_type:
        # Only show datasets of this particular type
        fq += u' +dataset_type:{type}'.format(type=package_type)

    facets = OrderedDict()

    default_facet_titles = {
        u'organization': _(u'Organizations'),
        u'groups': _(u'Groups'),
        u'tags': _(u'Tags'),
        u'res_format': _(u'Formats'),
        u'license_id': _(u'Licenses'),
    }

    for facet in h.facets():
        if facet in default_facet_titles:
            facets[facet] = default_facet_titles[facet]
        else:
            facets[facet] = facet

    # Facet titles
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.dataset_facets(facets, package_type)

    extra_vars[u'facet_titles'] = facets
    data_dict = {
        u'q': q,
        u'fq': fq.strip(),
        u'facet.field': list(facets.keys()),
        u'facet.limit': -1,
        u'rows': limit,
        u'start': (page - 1) * limit,
        u'sort': sort_by,
        u'extras': search_extras,
        u'include_private': asbool(
            config.get(u'ckan.search.default_include_private', True)
        ),
        u'dateranges': dateranges
    }
    try:
        query = get_action(u'package_search')(context, data_dict)

        extra_vars[u'sort_by_selected'] = query[u'sort']

        extra_vars[u'page'] = h.Page(
            collection=query[u'results'],
            page=page,
            url=pager_url,
            item_count=query[u'count'],
            items_per_page=limit
        )
        extra_vars[u'search_facets'] = query[u'search_facets']
        extra_vars[u'page'].items = query[u'results']
        extra_vars[u'dateranges'] = dateranges
        extra_vars[u'active_range'] = active_range
        extra_vars[u'daterange_options'] = daterange_options
    except SearchQueryError as se:
        # User's search parameters are invalid, in such a way that is not
        # achievable with the web interface, so return a proper error to
        # discourage spiders which are the main cause of this.
        log.info(u'Dataset search query rejected: %r', se.args)
        base.abort(
            400,
            _(u'Invalid search query: {error_message}')
            .format(error_message=str(se))
        )
    except SearchError as se:
        # May be bad input from the user, but may also be more serious like
        # bad code causing a SOLR syntax error, or a problem connecting to
        # SOLR
        log.error(u'Dataset search error: %r', se.args)
        extra_vars[u'query_error'] = True
        extra_vars[u'search_facets'] = {}
        extra_vars[u'page'] = h.Page(collection=[])

    # FIXME: try to avoid using global variables
    g.search_facets_limits = {}
    for facet in extra_vars[u'search_facets'].keys():
        try:
            limit = 0
        except ValueError:
            base.abort(
                400,
                _(u'Parameter u"{parameter_name}" is not '
                  u'an integer').format(parameter_name=u'_%s_limit' % facet)
            )

        g.search_facets_limits[facet] = 0

    _setup_template_variables(context, {}, package_type=package_type)

    extra_vars[u'dataset_type'] = package_type

    # TODO: remove
    for key, value in six.iteritems(extra_vars):
        setattr(g, key, value)

    return base.render(
        _get_pkg_template(u'search_template', package_type), extra_vars
    )


dataset_blueprint.add_url_rule('/', view_func=search, strict_slashes=False)