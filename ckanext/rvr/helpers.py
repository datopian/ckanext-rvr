import logging
from lxml import html
import cgi
import urllib
import ckan.plugins.toolkit as tk
import ckan.lib.helpers as h

log = logging.getLogger(__name__)
config = tk.config
ignore_missing = tk.get_validator('ignore_missing')


def get_newest_datasets():
    results = tk.get_action('current_package_list_with_resources')({},{"limit":5})
    return results


def get_nav_transport():
    link = h.literal(u'<a href="/{}">{}</a>'.format("verkehrsdaten", "Verkehrsdaten"))
    return h.literal("<li>")+ link + h.literal("</li>")


def get_specific_page(name=""):
    page_list = tk.get_action('ckanext_pages_list')(
        None, {
               'page_type': 'page'}
    )
    
    new_list = []
    for page in page_list:
        if page['name'] == name:
            new_list.append(page)
    return new_list


def get_faq_page():

    page_list = tk.get_action('ckanext_pages_list')(None, {'ignore_auth': True, 'user': 'ckan_admin', 'page_type': 'page', 'private': True})
    print(f"OVO JE {page_list}")
    for page in page_list:
        if page['name'] == "faq":
            faq_page = page["content"]
            if isinstance(faq_page, str):
                faq_page = faq_page.replace("\r\n", "")
            else:
                log.warning("Page content is not a string type: {}".format(faq_page))
    # print(faq_page)
    doc = html.fromstring(faq_page)
    faq_page_dict = []

    tag_is_p = False
    idx = 0
    for element in doc.xpath('//h1 | //h2 | //p'):
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
                value = [element.text]
                tag = "div"
                faq_page_dict.append({"tag": tag, "value": value})
                idx += 1
                tag_is_p = True
            else:
                last_el = faq_page_dict[idx-1]
                last_el["value"].append(element.text)
                faq_page_dict[idx-1] = last_el
                tag_is_p = True
    return faq_page_dict


def faq():
    return tk.render('home/faq.html')


def build_pages_nav_main(*args):

    about_menu = tk.asbool(config.get('ckanext.pages.about_menu', True))
    group_menu = tk.asbool(config.get('ckanext.pages.group_menu', True))
    org_menu = tk.asbool(config.get('ckanext.pages.organization_menu', True))

    # Different CKAN versions use different route names - gotta catch em all!
    about_menu_routes = ['about', 'home.about']
    group_menu_routes = ['group_index', 'home.group_index']
    org_menu_routes = ['organizations.index', 'home.organizations.index']

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
    pages_list = tk.get_action('ckanext_pages_list')(None, {'order': True, 'private': False})

    page_name = ''
    if tk.get_endpoint() in (('pages', 'pages_show'), ('pages', 'blog_show')):
        page_name = tk.request.path.split('/')[-1]
    #Meiran output = output + get_nav_transport()
    for page in pages_list:
        type_ = 'blog' if page['page_type'] == 'blog' else 'pages'
        name = urllib.parse.quote(page['name'].encode('utf-8')) #.decode('utf-8')
        title = cgi.escape(page['title'])
        link = h.literal(u'<a href="/{}/{}">{}</a>'.format(type_, name, title))
        if page['name'] == page_name:
            li = h.literal('<li class="active">') + link + h.literal('</li>')
        else:
            li = h.literal('<li>') + link + h.literal('</li>')
        output = output + li

    return  output 



def get_facet_description(facet_name):
    facet_description = {
        
        'organization': tk._('Datenbereitstellende Institutionen'),
        'groups': tk._('Nach CKAN standardisierte Datenkategorien'),
        'tags': tk._('Selbstgewählte Schlagworte'),
        'res_format': tk._('Zur Auswahl stehende Dateiformate'),
        'license_id': tk._('Rechtliche Vorgaben zur Nutzung der Daten'), 
        'date_filters': tk._('Filter nach Erstellungsdatum der Daten'),
        'frequency': tk._('Frequenz'),
        'source_type': tk._('Quelle Typ')
        }
    return facet_description[facet_name]

def get_cookie_control_config():

        cookie_control_config = {}

        api_key = tk.config.get(
            'ckanext.rvr.cc.api_key', '8740495678e47134ca596e8ec7e65d2ca3522b63')
        cookie_control_config['api_key'] = api_key 

        license_type = tk.config.get(
            'ckanext.rvr.cc.license_type', 'COMMUNITY')
        cookie_control_config['license_type'] = license_type

        popup_position = tk.config.get(
            'ckanext.rvr.cc.popup_position', 'LEFT')
        cookie_control_config['popup_position'] = popup_position

        theme_color = tk.config.get(
            'ckanext.rvr.cc.theme_color', 'DARK')
        cookie_control_config['theme_color'] = theme_color

        initial_state = tk.config.get(
            'ckanext.rvr.cc.initial_state', 'OPEN')
        cookie_control_config['initial_state'] = initial_state

        return cookie_control_config