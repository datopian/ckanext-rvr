from ckanext.rvr.views.dataset import dataset_blueprint
from ckanext.rvr.views.faq import faq_blueprint

def get_rvr_blueprint():
    return [dataset_blueprint, faq_blueprint]