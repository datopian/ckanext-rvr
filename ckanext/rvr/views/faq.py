from flask import Blueprint
import ckan.plugins.toolkit as toolkit

page_blueprint = Blueprint("page", __name__)


def faq_controller():
    return toolkit.render("home/faq.html")


page_blueprint.add_url_rule("/faq", "faq", view_func=faq_controller)
