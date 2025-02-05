import json
import logging
from six import text_type
from dateutil import parser

from ckan.lib.navl import dictization_functions
import ckan.logic as logic
import ckan.plugins as plugins
from ckan.common import config, asbool
import ckan.authz as authz
import ckan.lib.plugins as lib_plugins
import ckan.lib.search as search
import ckan.model as model

log = logging.getLogger(__name__)
toolkit = plugins.toolkit
_validate = dictization_functions.validate
ValidationError = logic.ValidationError
_check_access = logic.check_access
get_action = logic.get_action


def get_package_field(field, package):
    """
    Check package and package extras and get the value of the field if \
    it exists
    """
    value = None
    if package.get(field, ""):
        value = package[field]
    else:
        for item in package["extras"]:
            if item.get("key", "") == field:
                value = item["value"]
    return value


def filter_daterange(facet, dates, package):
    """
    Checks if the date of a field in a dataset is within a defined date \
    range.
    """

    # Check that there is at least a start or end date
    # No dates specified, packages passes
    if not dates[0] and not dates[1]:
        return True

    # Get start and end date objects
    start_date = None
    end_date = None
    try:
        if dates[0]:
            start_date = parser.parse(dates[0]).date()
        if dates[1]:
            end_date = parser.parse(dates[1]).date()
    except ValueError as e:
        # Incorrect date format from parameter, package passes
        log.error("Date parsing failed with error: {}".format(e))
        return True

    is_in_range = True
    facet_date_str = get_package_field(facet, package)

    if facet_date_str:
        try:
            facet_date = parser.parse(facet_date_str).date()
        except ValueError as e:
            # Package is storing incorrect date type, don't show package
            log.error("Date parsing failed with error: {}".format(e))
            return False

        # Check if datetime object is in range
        if start_date and start_date > facet_date:
            is_in_range = False
        if end_date and facet_date > end_date:
            is_in_range = False
    else:
        # The package doesn't have the field being filtered for at all, don't
        # show
        return False

    return is_in_range


def update_facets(facets, package):
    """
    After filtering, update the facets being sent from solr to reflect the \
    changes.
    """
    for facet in facets:
        if facet in ["tags", "groups", "organization"]:
            pop_items = []
            for facet_item in facets[facet]:
                if facet in ["organization"]:
                    item = package[facet]
                    if item["name"] == facet_item:
                        facets[facet][facet_item] -= 1
                        if facets[facet][facet_item] == 0:
                            pop_items.append(facet_item)
                if facet in ["tags", "groups"]:
                    for item in package[facet]:
                        if item["name"] == facet_item:
                            facets[facet][facet_item] -= 1
                            if facets[facet][facet_item] == 0:
                                pop_items.append(facet_item)
            for i in pop_items:
                facets[facet].pop(i)
        elif facet == "res_format":
            pop_items = []
            for facet_item in facets[facet]:
                for item in package["resources"]:
                    if item["format"] == facet_item:
                        facets[facet][facet_item] -= 1
                        if facets[facet][facet_item] == 0:
                            pop_items.append(facet_item)
            for i in pop_items:
                facets[facet].pop(i)
        else:
            pop_items = []
            value = get_package_field(facet, package)
            if facet in ["metadata_created", "metadata_modified"]:
                value = parser.parse(value).date().strftime("%m-%d-%Y")
            for item in facets[facet]:
                if (
                    value == item
                    or facet in ["metadata_created", "metadata_modified"]
                    and value == parser.parse(item).date().strftime("%m-%d-%Y")
                ):
                    facets[facet][item] -= 1
                    if facets[facet][item] == 0:
                        pop_items.append(item)
            for i in pop_items:
                facets[facet].pop(i)
    return facets


@toolkit.side_effect_free
def package_search(context, data_dict):
    """
    RVR implementation for ckan's package_search
    Searches for packages satisfying a given search criteria.

    This action accepts solr search query parameters (details below), and
    returns a dictionary of results, including dictized datasets that match
    the search criteria, a search count and also facet information.

    **Solr Parameters:**

    For more in depth treatment of each paramter, please read the
    `Solr Documentation
    <https://lucene.apache.org/solr/guide/6_6/common-query-parameters.html>`_.

    This action accepts a *subset* of solr's search query parameters:


    :param q: the solr query.  Optional.  Default: ``"*:*"``
    :type q: string
    :param fq: any filter queries to apply.  Note: ``+site_id:{ckan_site_id}``
        is added to this string prior to the query being executed.
    :type fq: string
    :param fq_list: additional filter queries to apply.
    :type fq_list: list of strings
    :param sort: sorting of the search results.  Optional.  Default:
        ``'score desc, metadata_modified desc'``.  As per the solr
        documentation, this is a comma-separated string of field names and
        sort-orderings.
    :type sort: string
    :param rows: the maximum number of matching rows (datasets) to return.
        (optional, default: ``10``, upper limit: ``1000`` unless set in
        site's configuration ``ckan.search.rows_max``)
    :type rows: int
    :param start: the offset in the complete result for where the set of
        returned datasets should begin.
    :type start: int
    :param facet: whether to enable faceted results.  Default: ``True``.
    :type facet: string
    :param facet.mincount: the minimum counts for facet fields should be
        included in the results.
    :type facet.mincount: int
    :param facet.limit: the maximum number of values the facet fields return.
        A negative value means unlimited. This can be set instance-wide with
        the :ref:`search.facets.limit` config option. Default is 50.
    :type facet.limit: int
    :param facet.field: the fields to facet upon.  Default empty.  If empty,
        then the returned facet information is empty.
    :type facet.field: list of strings
    :param include_drafts: if ``True``, draft datasets will be included in the
        results. A user will only be returned their own draft datasets, and a
        sysadmin will be returned all draft datasets. Optional, the default is
        ``False``.
    :type include_drafts: bool
    :param include_private: if ``True``, private datasets will be included in
        the results. Only private datasets from the user's organizations will
        be returned and sysadmins will be returned all private datasets.
        Optional, the default is ``False``.
    :type include_private: bool
    :param use_default_schema: use default package schema instead of
        a custom schema defined with an IDatasetForm plugin (default: ``False``)
    :type use_default_schema: bool


    The following advanced Solr parameters are supported as well. Note that
    some of these are only available on particular Solr versions. See Solr's
    `dismax`_ and `edismax`_ documentation for further details on them:

    ``qf``, ``wt``, ``bf``, ``boost``, ``tie``, ``defType``, ``mm``


    .. _dismax: http://wiki.apache.org/solr/DisMaxQParserPlugin
    .. _edismax: http://wiki.apache.org/solr/ExtendedDisMax


    **Examples:**

    ``q=flood`` datasets containing the word `flood`, `floods` or `flooding`
    ``fq=tags:economy`` datasets with the tag `economy`
    ``facet.field=["tags"] facet.limit=10 rows=0`` top 10 tags

    **Results:**

    The result of this action is a dict with the following keys:

    :rtype: A dictionary with the following keys
    :param count: the number of results found.  Note, this is the total number
        of results found, not the total number of results returned (which is
        affected by limit and row parameters used in the input).
    :type count: int
    :param results: ordered list of datasets matching the query, where the
        ordering defined by the sort parameter used in the query.
    :type results: list of dictized datasets.
    :param facets: DEPRECATED.  Aggregated information about facet counts.
    :type facets: DEPRECATED dict
    :param search_facets: aggregated information about facet counts.  The outer
        dict is keyed by the facet field name (as used in the search query).
        Each entry of the outer dict is itself a dict, with a "title" key, and
        an "items" key.  The "items" key's value is a list of dicts, each with
        "count", "display_name" and "name" entries.  The display_name is a
        form of the name that can be used in titles.
    :type search_facets: nested dict of dicts.

    An example result: ::

     {'count': 2,
      'results': [ { <snip> }, { <snip> }],
      'search_facets': {u'tags': {'items': [{'count': 1,
                                             'display_name': u'tolstoy',
                                             'name': u'tolstoy'},
                                            {'count': 2,
                                             'display_name': u'russian',
                                             'name': u'russian'}
                                           ]
                                 }
                       }
     }

    **Limitations:**

    The full solr query language is not exposed, including.

    fl
        The parameter that controls which fields are returned in the solr
        query.
        fl can be  None or a list of result fields, such as ['id', 'extras_custom_field'].
        if fl = None, datasets are returned as a list of full dictionary.
    """
    # Get dateranges
    dateranges = data_dict.pop("dateranges", {})
    data_dict.pop("date_filters", {})
    items_per_page = int(data_dict.pop("rows", 20))
    start = int(data_dict.pop("start", 0))
    data_dict["rows"] = 1000
    data_dict["start"] = 0

    # sometimes context['schema'] is None
    schema = context.get("schema") or logic.schema.default_package_search_schema()
    data_dict, errors = _validate(data_dict, schema, context)
    # put the extras back into the data_dict so that the search can
    # report needless parameters
    data_dict.update(data_dict.get("__extras", {}))
    data_dict.pop("__extras", None)
    if errors:
        raise ValidationError(errors)

    model = context["model"]
    session = context["session"]
    user = context.get("user")

    _check_access("package_search", context, data_dict)

    # Move ext_ params to extras and remove them from the root of the search
    # params, so they don't cause and error
    data_dict["extras"] = data_dict.get("extras", {})
    for key in [key for key in data_dict.keys() if key.startswith("ext_")]:
        data_dict["extras"][key] = data_dict.pop(key)

    # set default search field
    data_dict["df"] = "text"

    # check if some extension needs to modify the search params
    for item in plugins.PluginImplementations(plugins.IPackageController):
        data_dict = item.before_dataset_search(data_dict)

    # the extension may have decided that it is not necessary to perform
    # the query
    abort = data_dict.get("abort_search", False)

    if data_dict.get("sort") in (None, "rank"):
        data_dict["sort"] = (
            config.get("ckan.search.default_package_sort")
            or "score desc, metadata_modified desc"
        )

    results = []
    if not abort:
        if asbool(data_dict.get("use_default_schema")):
            data_source = "data_dict"
        else:
            data_source = "validated_data_dict"
        data_dict.pop("use_default_schema", None)

        result_fl = data_dict.get("fl")
        if not result_fl:
            data_dict["fl"] = "id {0}".format(data_source)
        else:
            data_dict["fl"] = " ".join(result_fl)

        # Remove before these hit solr FIXME: whitelist instead
        include_private = asbool(data_dict.pop("include_private", False))
        include_drafts = asbool(data_dict.pop("include_drafts", False))
        data_dict.setdefault("fq", "")
        if not include_private:
            data_dict["fq"] = "+capacity:public " + data_dict["fq"]
        if include_drafts:
            data_dict["fq"] += " +state:(active OR draft)"

        # Pop these ones as Solr does not need them
        extras = data_dict.pop("extras", None)

        # enforce permission filter based on user
        if context.get("ignore_auth") or (user and authz.is_sysadmin(user)):
            labels = None
        else:
            labels = lib_plugins.get_permission_labels().get_user_dataset_labels(
                context["auth_user_obj"]
            )

        query = search.query_for(model.Package)
        # Save a copy of the original data_dict
        permanent_data_dict = data_dict.copy()

        def get_filtered_packages(
            scanned_package_count=0, removed_packages_count=0, facets={}, extras=extras
        ):
            """
            Make query to solr and also filter results by dateranges if available
            """
            # Pass the original data_dict as it changes after each iteration
            data_dict = permanent_data_dict.copy()
            if scanned_package_count:
                data_dict["start"] = scanned_package_count
            query.run(data_dict, permission_labels=labels)
            if not facets:
                current_facets = query.facets
            else:
                current_facets = facets

            # Add them back so extensions can use them on after_search
            data_dict["extras"] = extras

            if result_fl:
                for package in query.results:
                    scanned_package_count += 1
                    if isinstance(package, text_type):
                        package = {result_fl[0]: package}
                    extras = package.pop("extras", {})
                    package.update(extras)

                    # Check daterange
                    is_in_range = True
                    for k in dateranges:
                        if not filter_daterange(k, dateranges[k]["params"], package):
                            is_in_range = False
                            break
                    if not is_in_range:
                        removed_packages_count += 1
                        # Remove facet representations
                        current_facets = update_facets(current_facets, package)
                        continue
                    results.append(package)
            else:
                for package in query.results:
                    scanned_package_count += 1
                    # get the package object
                    package_dict = package.get(data_source)
                    ## use data in search index if there
                    if package_dict:
                        # the package_dict still needs translating when being viewed
                        package_dict = json.loads(package_dict)
                        if context.get("for_view"):
                            for item in plugins.PluginImplementations(
                                plugins.IPackageController
                            ):
                                package_dict = item.before_dataset_view(package_dict)
                        # Check daterange
                        is_in_range = True
                        for k in dateranges:
                            if not filter_daterange(
                                k, dateranges[k]["params"], package_dict
                            ):
                                is_in_range = False
                                break
                        if not is_in_range:
                            removed_packages_count += 1
                            # Remove facet representations
                            current_facets = update_facets(current_facets, package_dict)
                            continue
                        results.append(package_dict)
                    else:
                        log.error(
                            "No package_dict is coming from solr for package " "id %s",
                            package["id"],
                        )
            return scanned_package_count, removed_packages_count, current_facets

        scanned_packages_count = 0
        removed_packages_count = 0
        facets = {}
        # A 'do-while' loop implementation to run at least one solr search
        # and keep running searches till all the packages from the original
        # search have been filtered
        while True:
            scanned_packages_count, removed_packages_count, facets = (
                get_filtered_packages(
                    scanned_package_count=scanned_packages_count,
                    removed_packages_count=removed_packages_count,
                    facets=facets,
                )
            )
            # Break loop once all query results have been searched through
            if int(query.count) <= scanned_packages_count:
                break
        count = int(query.count) - removed_packages_count
    else:
        count = 0
        facets = {}
        results = []

    paginated_results = results[start : start + items_per_page]

    search_results = {
        "count": count,
        "facets": facets,
        "results": paginated_results,
        "sort": data_dict["sort"],
    }

    # create a lookup table of group name to title for all the groups and
    # organizations in the current search's facets.
    group_names = []
    for field_name in ("groups", "organization"):
        group_names.extend(facets.get(field_name, {}).keys())

    groups = (
        session.query(model.Group.name, model.Group.title)
        .filter(model.Group.name.in_(group_names))
        .all()
        if group_names
        else []
    )
    group_titles_by_name = dict(groups)

    # Transform facets into a more useful data structure.
    restructured_facets = {}
    for key, value in facets.items():
        restructured_facets[key] = {"title": key, "items": []}
        for key_, value_ in value.items():
            new_facet_dict = {}
            new_facet_dict["name"] = key_
            if key in ("groups", "organization"):
                display_name = group_titles_by_name.get(key_, key_)
                display_name = (
                    display_name if display_name and display_name.strip() else key_
                )
                new_facet_dict["display_name"] = display_name
            elif key == "license_id":
                license = model.Package.get_license_register().get(key_)
                if license:
                    new_facet_dict["display_name"] = license.title
                else:
                    new_facet_dict["display_name"] = key_
            else:
                new_facet_dict["display_name"] = key_
            new_facet_dict["count"] = value_
            restructured_facets[key]["items"].append(new_facet_dict)
    search_results["search_facets"] = restructured_facets

    # check if some extension needs to modify the search results
    for item in plugins.PluginImplementations(plugins.IPackageController):
        search_results = item.after_dataset_search(search_results, data_dict)

    # After extensions have had a chance to modify the facets, sort them by
    # display name.
    for facet in search_results["search_facets"]:
        search_results["search_facets"][facet]["items"] = sorted(
            search_results["search_facets"][facet]["items"],
            key=lambda facet: facet["display_name"],
            reverse=True,
        )

    return search_results


@toolkit.chained_action
@toolkit.side_effect_free
def package_show(up_func, context, data_dict):
    """
    Extends the default ckan package_show to move the `spatial` and \
    `dataset_spatial` fields from the extras to the main dict object.

    This is necessary to fix bugs with the package dict getting updated with \
    both fields in the extras and the main package schema.
    """
    result  = up_func(context, data_dict)
    result["spatial"] = result.get("dataset_spatial", "")
    return result


def add_org_spatial_to_dataset_dict(pkg_dict: dict, org_id: str) -> dict:
    """
    Gets the bbox coordinates from the organization if it has one and adds \
    it to the dataset dictionary for indexing.

    Note: This should only be called before indexing, the aim is to index the \
    spatial data with the dataset, if the organization has spatial daata, \
    but not to add the data to the dataset in the database.

    Args:
        pkg_dict (dict): The package dictionary object gotten from the ckan \
        plugin `before_index` method
        org_id (str): The organization id of the dataset's organization
    
    Returns:
        (dict) Updated dictionary with the `extras_spatial` field if the \
        organization had coordinates, if not, just returns back the `pkg_dict`
    """
    context = {"model": model, "session": model.Session}
    data_dict = {"id": org_id, "include_datasets": False}
    try:
        group_dict = get_action("organization_show")(context, data_dict)
        extras = group_dict.get("extras", [])
        org_spatial = None
        for extra in extras:
            if extra["key"] == "org_spatial":
                org_spatial = extra["value"]
        if org_spatial and org_spatial.startswith("[["):
            coordinates = json.loads(org_spatial)
            pkg_geojson = {"type": "Polygon", "coordinates": coordinates}
            spatial = json.dumps(pkg_geojson)
            pkg_dict["extras_spatial"] = spatial

            # Add spatial to data_dict
            if pkg_dict.get("data_dict", None):
                data = json.loads(pkg_dict["data_dict"])
                data["extras"].append({"key": "spatial", "value": spatial})
                pkg_dict["data_dict"] = json.dumps(data)

            # Add spatial to validated_data_dict
            if pkg_dict.get("validated_data_dict", None):
                validated_data = json.loads(pkg_dict["validated_data_dict"])
                validated_data["extras"].append({"key": "spatial", "value": spatial})
                pkg_dict["validated_data_dict"] = json.dumps(validated_data)

            return pkg_dict
        else:
            return pkg_dict
    except (logic.NotFound, logic.NotAuthorized) as e:
        log.error(e)
        return pkg_dict


def generate_spatial_from_bbox(bbox: str) -> str:
    """
    Takes a bbox string and adds it to the spatial polygon
    """
    bbox_json = json.loads(bbox)
    spatial_json = {"type": "Polygon", "coordinates": bbox_json}
    return json.dumps(spatial_json)


def update_dataset_spatial(data: dict) -> None:
    """
    This should be called when the organization bbox string has changed.

    This function updates all the datasets of that organization that don't \
    have a bbox string, and leaves those that do. The datasets are then \
    reindexed.

    Args:
        data (dict): The organization dictionary object
    """
    from ckan.views.group import _force_reindex

    for extra in data.get("extras", []):
        if extra.get("key", None) == "org_spatial":
            org_spatial = extra["value"]

    context = {"model": model, "session": model.Session}

    for pkg in data.get("packages", []):
        dataset = get_action("package_show")(context, {"id": pkg["id"]})
        has_bbox = False

        # Before the addition of the features to allows datasets inherit spatial
        # coordinates from the organization, some fields already had their
        # 'spatial' fields but not the 'dataset_spatial' fields.
        # In the event that the fields are not updated before using the
        # feature, we don't want to lose the coordinates for those datasets,
        # hence we would also not override datasets that have any of these extras
        # TODO: This is temporary and when it is certain that the data has been
        # normalized, this should be set to use only the 'dataset_spatial' field
        required = [
            "bbox-east-long",
            "bbox-north-lat",
            "bbox-south-lat",
            "bbox-west-long",
        ]
        # Check if the dataset has a bbox value
        if dataset.get("dataset_spatial", None):
            has_bbox = True
        else:
            for extra in dataset.get("extras", []):
                if extra["key"] in required and len(extra["value"]) > 0:
                    has_bbox = True
                    break
        if not has_bbox:
            try:
                # Update the package spatial field to the org bbox value
                dataset["spatial"] = org_spatial
                get_action("package_update")(context, dataset)
            except Exception as e:
                log.warn(
                    """Failed to update dataset: {} with spatial data from \
                    organization: {}""".format(
                        dataset["name"], data["name"]
                    )
                )
                log.warn(e)
    _force_reindex(data)
