import json

from sqlalchemy.sql import select
from sqlalchemy import and_
from ckan.logic import get_action
import ckan.model as model

import logging
from lxml import html
import cgi
import urllib
import ckan.plugins.toolkit as tk
import ckan.lib.helpers as h

log = logging.getLogger(__name__)
config = tk.config
ignore_missing = tk.get_validator("ignore_missing")

context = {"model": model, "session": model.Session, "ignore_auth": True}


def is_valid_spatial(spatial: str) -> bool:
    """Checks is a spatial string is a valid GeoJSON spatial

    Args:
        spatial (str): the string to check

    Returns:
        bool: True if it is a valid GeoJSON polygon, false if otherwise
    """
    try:
        spatial_dict = json.loads(spatial)
        if spatial_dict["type"].lower() != "polygon":
            return False
        if type(spatial_dict["coordinates"]) != type([]):
            return False
        del spatial_dict
        return True
    except:
        return False


def get_org_spatial(org_id: str, context: dict = context) -> str:
    """Get the spatial data for the organization

    Args:
        org_id (str): the organization id
        context (dict, optional): Defaults to the script context.

    Returns:
        str: The organization spatial string
    """
    org_dict = get_action("organization_show")(
        context, {"id": org_id, "include_datasets": False}
    )
    org_spatial = ""
    for extra in org_dict.get("extras", []):
        if extra.get("key") == "org_spatial":
            org_spatial = extra.get("value")
    return org_spatial


def all_package_list(include_private: bool = True):
    """
    Like ckan's package_list but returns only private packages which are \
    dataset types.

    Only compatible with ckan 2.9.x

    Args:
        include_private (bool, optional): include private datasets. Defaults to True.
    """
    package_table = model.package_table
    col = package_table.c.name
    query = select([col])
    if include_private:
        query = query.where(
            and_(package_table.c.state == "active", package_table.c.type == "dataset")
        )
    else:
        return get_action("package_list")(context, {})
    query = query.order_by(col)

    ## Returns the first field in each result record
    return [r[0] for r in query.execute()]


def get_latest_created_datasets():
    results = tk.get_action("package_search")(
        context,
        {"rows": 5, "sort": "metadata_created desc", "fq": "type:dataset", "q": ""},
    )
    return results['results']


def get_nav_transport():
    link = h.literal('<a href="/{}">{}</a>'.format("verkehrsdaten", "Verkehrsdaten"))
    return h.literal("<li>") + link + h.literal("</li>")


def get_specific_page(name=""):
    page_list = tk.get_action("ckanext_pages_list")(None, {"page_type": "page"})

    new_list = []
    for page in page_list:
        if page["name"] == name:
            new_list.append(page)
    return new_list


def get_faq_page():
    page_list = tk.get_action("ckanext_pages_list")(
        None,
        {
            "ignore_auth": True,
            "user": "ckan_admin",
            "page_type": "page",
            "private": True,
        },
    )
    for page in page_list:
        if page["name"] == "faq":
            faq_page = page["content"]
            if isinstance(faq_page, str):
                faq_page = faq_page.replace("\r\n", "")
            else:
                log.warning("Page content is not a string type: {}".format(faq_page))
    doc = html.fromstring(faq_page)
    faq_page_dict = []

    tag_is_p = False
    idx = 0
    for element in doc.xpath("//h1 | //h2 | //p"):
        tag = element.tag
        if tag != "p":
            tag = element.tag
            value = [element.text]
            if value:
                faq_page_dict.append({"tag": tag, "value": value})
                idx += 1
            tag_is_p = False
        elif tag == "p":
            if not tag_is_p:
                value = [html.tostring(element).decode("utf-8")]
                print(value)
                tag = "div"
                faq_page_dict.append({"tag": tag, "value": value})
                idx += 1
                tag_is_p = True
            else:
                last_el = faq_page_dict[idx - 1]
                last_el["value"].append(html.tostring(element).decode("utf-8"))
                faq_page_dict[idx - 1] = last_el
                tag_is_p = True
    return faq_page_dict


def faq():
    return tk.render("home/faq.html")


def build_pages_nav_main(*args):

    about_menu = tk.asbool(config.get("ckanext.pages.about_menu", True))
    group_menu = tk.asbool(config.get("ckanext.pages.group_menu", True))
    org_menu = tk.asbool(config.get("ckanext.pages.organization_menu", True))

    # Different CKAN versions use different route names - gotta catch em all!
    about_menu_routes = ["about", "home.about"]
    group_menu_routes = ["group_index", "home.group_index"]
    org_menu_routes = ["organizations.index", "home.organizations.index"]

    new_args = []
    for arg in args:
        if arg[0] in about_menu_routes and not about_menu:
            continue
        if arg[0] in org_menu_routes and not org_menu:
            continue
        if arg[0] in group_menu_routes and not group_menu:
            continue
        new_args.append(arg)

    output = h.build_nav_main(*new_args)
    # do not display any private datasets in menu even for sysadmins
    pages_list = tk.get_action("ckanext_pages_list")(
        None, {"order": True, "private": False}
    )

    page_name = ""
    if tk.get_endpoint() in (("pages", "pages_show"), ("pages", "blog_show")):
        page_name = tk.request.path.split("/")[-1]
    # output = output + get_nav_transport()
    for page in pages_list:
        type_ = "blog" if page["page_type"] == "blog" else "pages"
        name = urllib.parse.quote(page["name"].encode("utf-8"))  # .decode('utf-8')
        title = cgi.escape(page["title"])
        link = h.literal('<a href="/{}/{}">{}</a>'.format(type_, name, title))
        if page["name"] == page_name:
            li = h.literal('<li class="active">') + link + h.literal("</li>")
        else:
            li = h.literal("<li>") + link + h.literal("</li>")
        output = output + li

    return output


def get_facet_description(facet_name):
    facet_description = {
        "organization": tk._("Datenbereitstellende Institutionen"),
        "groups": tk._("Nach CKAN standardisierte Datenkategorien"),
        "tags": tk._("Selbstgewählte Schlagworte"),
        "res_format": tk._("Zur Auswahl stehende Dateiformate"),
        "license_id": tk._("Rechtliche Vorgaben zur Nutzung der Daten"),
        "date_filters": tk._("Filter nach Erstellungsdatum der Daten"),
        "frequency": tk._("Frequenz"),
        "source_type": tk._("Quelle Typ"),
    }
    return facet_description[facet_name]


def get_cookie_control_config():

    cookie_control_config = {}

    api_key = tk.config.get(
        "ckanext.rvr.cc.api_key", "8740495678e47134ca596e8ec7e65d2ca3522b63"
    )
    cookie_control_config["api_key"] = api_key

    license_type = tk.config.get("ckanext.rvr.cc.license_type", "COMMUNITY")
    cookie_control_config["license_type"] = license_type

    popup_position = tk.config.get("ckanext.rvr.cc.popup_position", "LEFT")
    cookie_control_config["popup_position"] = popup_position

    theme_color = tk.config.get("ckanext.rvr.cc.theme_color", "DARK")
    cookie_control_config["theme_color"] = theme_color

    initial_state = tk.config.get("ckanext.rvr.cc.initial_state", "OPEN")
    cookie_control_config["initial_state"] = initial_state

    return cookie_control_config
