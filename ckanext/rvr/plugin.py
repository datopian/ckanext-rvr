import ckan.plugins as p
from ckan.lib.plugins import DefaultTranslation
from ckanext.rvr import validators
import ckan.logic as logic
from ckanext.scheming.helpers import scheming_get_dataset_schema



class RvrPlugin(p.SingletonPlugin, DefaultTranslation):
    @staticmethod
    def set_license(dataset_dict, licenses, default_license_url=None):
        """
        Set license fields on dataset_dict based on provided licenses mapping and
        default license URL.
        - dataset_dict: dict to update
        - licenses: dict mapping license_id to dict with 'title' and 'url'
        - default_license_url: fallback URL if not found in licenses
        """
        license_id = dataset_dict.get('license_id')
        if not license_id:
            return
        license_info = licenses.get(license_id) if licenses else None
        if license_info:
            dataset_dict['license_title'] = license_info.get('title', '')
            dataset_dict['license_url'] = license_info.get(
                'url', default_license_url or ''
            )
        else:
            dataset_dict['license_title'] = ''
            dataset_dict['license_url'] = default_license_url or ''
        # Remove from extras if present
        if 'extras' in dataset_dict and isinstance(dataset_dict['extras'], list):
            dataset_dict['extras'] = [
                e for e in dataset_dict['extras']
                if e.get('key') not in ['license_title', 'license_url']
            ]

    @staticmethod
    def assign_extras_to_top_level(dataset_dict, schema_fields=None):
        def normalize(s):
            return s.strip().lower().replace('-', '_').replace(' ', '_')

        if (
            not schema_fields or "extras" not in dataset_dict or
            not isinstance(dataset_dict["extras"], list)
        ):
            return
        field_map = {normalize(f): f for f in schema_fields}
        for extra in list(dataset_dict["extras"]):
            key = extra.get("key")
            if key is not None and normalize(key) in field_map:
                field_name = field_map[normalize(key)]
                if field_name not in dataset_dict:
                    dataset_dict[field_name] = extra.get("value")

    @staticmethod
    def remove_duplicate_extras(dataset_dict, schema_fields=None):
        def normalize(s):
            return s.strip().lower().replace('-', '_').replace(' ', '_')

        if "extras" in dataset_dict and isinstance(dataset_dict["extras"], list):
            field_set = set()
            if schema_fields is not None:
                field_set.update(normalize(f) for f in schema_fields)
            cleaned_extras = [
                e for e in dataset_dict["extras"]
                if e.get("key") is not None and normalize(e.get("key")) not in field_set
            ]
            dataset_dict["extras"] = cleaned_extras

    @staticmethod
    def fix_spatial(dataset_dict):
        extras = dataset_dict.get("extras")
        if isinstance(extras, list):
            for field in extras:
                if field["key"] == "spatial":
                    dataset_dict["spatial"] = field["value"]
                    dataset_dict["dataset_spatial"] = field["value"]
                    extras.remove(field)
                    break

    @staticmethod
    def set_dataset_groups(dataset_dict):
        if dataset_dict.get("groups"):
            for group in dataset_dict["groups"]:
                group_dict = logic.get_action('group_show')(
                    {'id': group.get('id') or group.get('name')}
                )
                group['title'] = group_dict.get('title')

    @staticmethod
    def normalize_dataset_dict(dataset_dict):
        """
        Shared normalization logic for before_create and before_update.
    Handles extras assignment, duplicate removal, spatial/group fix, and
    schema-compliant normalization.
        """
        schema = scheming_get_dataset_schema(dataset_dict.get('type', 'dataset'))
        schema_fields = []
        if schema and 'dataset_fields' in schema:
            schema_fields = [
                f['field_name'] for f in schema['dataset_fields'] if 'field_name' in f
            ]
        RvrPlugin.assign_extras_to_top_level(dataset_dict, schema_fields)
        RvrPlugin.remove_duplicate_extras(dataset_dict, schema_fields)

        def normalize(s):
            return s.strip().lower().replace('-', '_').replace(' ', '_')

        if 'extras' in dataset_dict and isinstance(dataset_dict['extras'], list):
            top_level_keys = set(
                normalize(k) for k in dataset_dict.keys() if k != 'extras'
            )
            cleaned_extras = [
                e for e in dataset_dict['extras']
                if e.get('key') is not None and normalize(e.get('key')) not in top_level_keys
            ]
            dataset_dict['extras'] = cleaned_extras

        # RvrPlugin.set_license(dataset_dict, licenses, default_license_url)  # Uncomment and provide args if needed
        RvrPlugin.fix_spatial(dataset_dict)
        RvrPlugin.set_dataset_groups(dataset_dict)

        # --- BEGIN: Schema-compliant normalization for applicable_legislation and hvd_category (AFTER extras assignment) ---
        if 'applicable_legislation' in dataset_dict:
            val = dataset_dict['applicable_legislation']
            if isinstance(val, str) and val.startswith('['):
                try:
                    import json
                    parsed = json.loads(val)
                    if isinstance(parsed, list) and parsed:
                        val = str(parsed[0])
                        dataset_dict['applicable_legislation'] = val
                except Exception:
                    pass
            val = dataset_dict['applicable_legislation']
            if not (isinstance(val, str) and val.startswith('http')):
                raise Exception(
                    f"Skipping dataset: invalid applicable_legislation: {val}"
                )
            dataset_dict['applicable_legislation'] = str(val)

        try:
            from ckanext.rvr.profiles import HVD_CATEGORY_MAPPING
        except ImportError:
            HVD_CATEGORY_MAPPING = {}

        uri_to_label = {v: k for k, v in HVD_CATEGORY_MAPPING.items()}
        allowed_hvd_labels = set(HVD_CATEGORY_MAPPING.keys())
        
        if 'hvd_category' in dataset_dict:
            val = dataset_dict['hvd_category']
            if isinstance(val, str) and val.startswith('['):
                try:
                    import json
                    parsed = json.loads(val)
                    if isinstance(parsed, list) and parsed:
                        val = str(parsed[0])
                        dataset_dict['hvd_category'] = val
                except Exception:
                    pass
            val = dataset_dict['hvd_category']
            if val in uri_to_label:
                dataset_dict['hvd_category'] = str(uri_to_label[val])
            elif val in allowed_hvd_labels:
                dataset_dict['hvd_category'] = str(val)
            else:
                raise Exception(
                    f"Skipping dataset: invalid hvd_category: {val}"
                )
            dataset_dict['hvd_category'] = str(dataset_dict['hvd_category'])
        # --- END: Schema-compliant normalization ---
        return dataset_dict

    # IValidators
    def get_validators(self):
        return {
            "spatial_validator": validators.spatial_validator,
        }

    # IDCATRDFHarvester
    def before_download(self, url, harvest_job):
        return url, []
    
    def update_session(self, session):
        return session

    def after_download(self, content, harvest_job):
        return content, []

    def after_parsing(self, rdf_parser, harvest_job):
        return rdf_parser, []

    def before_create(self, harvest_object, dataset_dict, temp_dict):
        # --- END: Normalize/fix specific fields ---
        return RvrPlugin.normalize_dataset_dict(dataset_dict)

    def after_create(self, harvest_object, dataset_dict, temp_dict):
        return None
    
    def before_update(self, harvest_object, dataset_dict, temp_dict):
        # --- END: Normalize/fix specific fields ---
        return RvrPlugin.normalize_dataset_dict(dataset_dict)

    def after_update(self, harvest_object, dataset_dict, temp_dict):
        return None
    
    def update_package_schema_for_create(self, package_schema):
        # Ensure this method is properly defined
        return package_schema

    def update_package_schema_for_update(self, package_schema):
        # Ensure this method is properly defined
        return package_schema