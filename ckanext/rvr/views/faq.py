from flask import Blueprint
import ckan.plugins.toolkit as toolkit

faq_blueprint = Blueprint('faq', __name__)

def faq_controller():
    return toolkit.render('home/faq.html')

faq_blueprint.add_url_rule('/faq', 'faq', faq_controller)
