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
from ckan.lib.search import SearchError, SearchQueryError, SearchIndexError
from ckan.views.dataset import CreateView, EditView, _get_package_type, _tag_string_to_list, _form_save_redirect, text_type, CACHE_PARAMETERS
import ckan.lib.navl.dictization_functions as dict_fns
from ckanext.rvr.helpers import is_valid_spatial, get_org_spatial


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

class RvrCreateView(CreateView):
    def post(self, package_type):
        # The staged add dataset used the new functionality when the dataset is
        # partially created so we need to know if we actually are updating or
        # this is a real new.
        context = self._prepare()
        is_an_update = False
        ckan_phase = request.form.get(u'_ckan_phase')
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
        except dict_fns.DataError:
            return base.abort(400, _(u'Integrity Error'))
        try:
            if ckan_phase:
                # prevent clearing of groups etc
                context[u'allow_partial_update'] = True
                # sort the tags
                if u'tag_string' in data_dict:
                    data_dict[u'tags'] = _tag_string_to_list(
                        data_dict[u'tag_string']
                    )
                if data_dict.get(u'pkg_name'):
                    is_an_update = True
                    # This is actually an update not a save
                    data_dict[u'id'] = data_dict[u'pkg_name']
                    del data_dict[u'pkg_name']
                    # don't change the dataset state
                    data_dict[u'state'] = u'draft'
                    # this is actually an edit not a save
                    pkg_dict = get_action(u'package_update')(
                        context, data_dict
                    )

                    # redirect to add dataset resources
                    url = h.url_for(
                        u'{}_resource.new'.format(package_type),
                        id=pkg_dict[u'name']
                    )
                    return h.redirect_to(url)
                # Make sure we don't index this dataset
                if request.form[u'save'] not in [
                    u'go-resource', u'go-metadata'
                ]:
                    data_dict[u'state'] = u'draft'
                # allow the state to be changed
                context[u'allow_state_change'] = True

            data_dict[u'type'] = package_type
            context[u'message'] = data_dict.get(u'log_message', u'')

            # If the dataset has a spatial and it is valid, make it the default
            spatial = data_dict.get('spatial', '')
            dataset_spatial = data_dict.get('dataset_spatial', '')
            if is_valid_spatial(dataset_spatial) and spatial != dataset_spatial:
                data_dict['spatial'] = dataset_spatial
            else:
                # if the organization has a spatial, use that
                data_dict['spatial'] = ''
                if data_dict.get('owner_org', None):
                    org_spatial = get_org_spatial(data_dict['owner_org'])
                    if org_spatial:
                        data_dict['spatial'] = org_spatial

            pkg_dict = get_action(u'package_create')(context, data_dict)

            if ckan_phase:
                # redirect to add dataset resources
                url = h.url_for(
                    u'{}_resource.new'.format(package_type),
                    id=pkg_dict[u'name']
                )
                return h.redirect_to(url)

            return _form_save_redirect(
                pkg_dict[u'name'], u'new', package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to read package'))
        except NotFound as e:
            return base.abort(404, _(u'Dataset not found'))
        except SearchIndexError as e:
            try:
                exc_str = text_type(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = text_type(str(e))
            return base.abort(
                500,
                _(u'Unable to add package to search index.') + exc_str
            )
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            if is_an_update:
                # we need to get the state of the dataset to show the stage we
                # are on.
                pkg_dict = get_action(u'package_show')(context, data_dict)
                data_dict[u'state'] = pkg_dict[u'state']
                return EditView().get(
                    package_type,
                    data_dict[u'id'],
                    data_dict,
                    errors,
                    error_summary
                )
            data_dict[u'state'] = u'none'
            return self.get(package_type, data_dict, errors, error_summary)

    def get(self, package_type, data=None, errors=None, error_summary=None):
        context = self._prepare(data)
        if data and u'type' in data:
            package_type = data[u'type']

        data = data or clean_dict(
            dict_fns.unflatten(
                tuplize_dict(
                    parse_params(request.args, ignore_keys=CACHE_PARAMETERS)
                )
            )
        )
        resources_json = h.json.dumps(data.get(u'resources', []))
        # convert tags if not supplied in data
        if data and not data.get(u'tag_string'):
            data[u'tag_string'] = u', '.join(
                h.dict_list_reduce(data.get(u'tags', {}), u'name')
            )

        errors = errors or {}
        error_summary = error_summary or {}
        # in the phased add dataset we need to know that
        # we have already completed stage 1
        stage = [u'active']
        if data.get(u'state', u'').startswith(u'draft'):
            stage = [u'active', u'complete']

        # if we are creating from a group then this allows the group to be
        # set automatically
        data[
            u'group_id'
        ] = request.args.get(u'group') or request.args.get(u'groups__0__id')

        form_snippet = _get_pkg_template(
            u'package_form', package_type=package_type
        )

        form_vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'new',
            u'stage': stage,
            u'dataset_type': package_type,
            u'form_style': u'new'
        }
        errors_json = h.json.dumps(errors)

        # TODO: remove
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(context, {}, package_type=package_type)

        new_template = _get_pkg_template(u'new_template', package_type)
        return base.render(
            new_template,
            extra_vars={
                u'form_vars': form_vars,
                u'form_snippet': form_snippet,
                u'dataset_type': package_type,
                u'resources_json': resources_json,
                u'form_snippet': form_snippet,
                u'errors_json': errors_json
            }
        )

class RvrEditView(EditView):
    def post(self, package_type, id):
        context = self._prepare(id)
        package_type = _get_package_type(id) or package_type
        log.debug(u'Package save request name: %s POST: %r', id, request.form)
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
        except dict_fns.DataError:
            return base.abort(400, _(u'Integrity Error'))
        try:
            if u'_ckan_phase' in data_dict:
                # we allow partial updates to not destroy existing resources
                context[u'allow_partial_update'] = True
                if u'tag_string' in data_dict:
                    data_dict[u'tags'] = _tag_string_to_list(
                        data_dict[u'tag_string']
                    )
                del data_dict[u'_ckan_phase']
                del data_dict[u'save']
            context[u'message'] = data_dict.get(u'log_message', u'')
            data_dict['id'] = id

            # If the dataset has a spatial, make it the default
            spatial = data_dict.get('spatial', '')
            dataset_spatial = data_dict.get('dataset_spatial', '')
            if is_valid_spatial(dataset_spatial) and spatial != dataset_spatial:
                data_dict['spatial'] = dataset_spatial

            pkg_dict = get_action(u'package_update')(context, data_dict)

            return _form_save_redirect(
                pkg_dict[u'name'], u'edit', package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to read package %s') % id)
        except NotFound as e:
            return base.abort(404, _(u'Dataset not found'))
        except SearchIndexError as e:
            try:
                exc_str = text_type(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = text_type(str(e))
            return base.abort(
                500,
                _(u'Unable to update search index.') + exc_str
            )
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(package_type, id, data_dict, errors, error_summary)

    def get(
        self, package_type, id, data=None, errors=None, error_summary=None
    ):
        context = self._prepare(id, data)
        package_type = _get_package_type(id) or package_type
        try:
            pkg_dict = get_action(u'package_show')(
                dict(context, for_view=True), {
                    u'id': id
                }
            )
            context[u'for_edit'] = True
            old_data = get_action(u'package_show')(context, {u'id': id})
            # old data is from the database and data is passed from the
            # user if there is a validation error. Use users data if there.
            if data:
                old_data.update(data)
            data = old_data
        except (NotFound, NotAuthorized):
            return base.abort(404, _(u'Dataset not found'))
        # are we doing a multiphase add?
        if data.get(u'state', u'').startswith(u'draft'):
            g.form_action = h.url_for(u'{}.new'.format(package_type))
            g.form_style = u'new'

            return CreateView().get(
                package_type,
                data=data,
                errors=errors,
                error_summary=error_summary
            )

        pkg = context.get(u"package")
        resources_json = h.json.dumps(data.get(u'resources', []))

        try:
            check_access(u'package_update', context)
        except NotAuthorized:
            return base.abort(
                403,
                _(u'User %r not authorized to edit %s') % (g.user, id)
            )
        # convert tags if not supplied in data
        if data and not data.get(u'tag_string'):
            data[u'tag_string'] = u', '.join(
                h.dict_list_reduce(pkg_dict.get(u'tags', {}), u'name')
            )
        errors = errors or {}
        form_snippet = _get_pkg_template(
            u'package_form', package_type=package_type
        )

        # Get the org spatial
        data['org_spatial'] = get_org_spatial(data['organization']['name'])

        form_vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'edit',
            u'dataset_type': package_type,
            u'form_style': u'edit'
        }
        errors_json = h.json.dumps(errors)

        # TODO: remove
        g.pkg = pkg
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(
            context, {u'id': id}, package_type=package_type
        )

        # we have already completed stage 1
        form_vars[u'stage'] = [u'active']
        if data.get(u'state', u'').startswith(u'draft'):
            form_vars[u'stage'] = [u'active', u'complete']

        edit_template = _get_pkg_template(u'edit_template', package_type)
        return base.render(
            edit_template,
            extra_vars={
                u'form_vars': form_vars,
                u'form_snippet': form_snippet,
                u'dataset_type': package_type,
                u'pkg_dict': pkg_dict,
                u'pkg': pkg,
                u'resources_json': resources_json,
                u'form_snippet': form_snippet,
                u'errors_json': errors_json
            }
        )

dataset_blueprint.add_url_rule('/', view_func=search, strict_slashes=False)
dataset_blueprint.add_url_rule(u'/new', view_func=RvrCreateView.as_view(str(u'new')))
dataset_blueprint.add_url_rule(
    u'/edit/<id>', view_func=RvrEditView.as_view(str(u'edit'))
)
