from ckanext.rvr.views.dataset import dataset_blueprint
from ckanext.rvr.views.faq import page_blueprint

def get_rvr_blueprint():
    return [dataset_blueprint, page_blueprint]