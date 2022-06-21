import click
from pprint import pformat

import ckan.model as model
from ckan.logic import get_action

from ckanext.rvr.helpers import is_valid_spatial, all_package_list

echo = click.echo
context = {
    'model': model,
    'session': model.Session,
    'ignore_auth': True
}

short_help = "Migrates spatial fields for datasets, to prepare them for the spatial inheritance feature of the ckanext-rvr extension"
help = """Migrate spatial fields for datasets and organizations\n

Gets datasets that have data in their `spatial` fields, but NO data in their \
`dataset_spatial` fields and the data in their `spatial` field IS DIFFERENT \
from that in the organization's `org_spatial` field, indicating that the \
dataset has not been prepared to use the spatial inheritance feature of the \
ckanext-rvr extension. For these datasets, the `spatial` data would be copied \
into the `dataset_spatial` field to prevent it from being overwritten by the \
organization spatial.
"""
epilog = """****WHY IS THIS COMMAND NEEDED?****\n
For the ckanext-spatial extension to run spatial queries against datasets, \
they are required to have the `spatial` field. This extension allows setting \
the spatial fields from the organization and the datasets can inherit that if \
they don't have their own spatial defined.\n
To achieve that, a `dataset_spatial` field has been added for datasets and an \
`org_spatial` field has been added for organizations. The `spatial` field \
still tracks the dataset spatial data, but now if a spatial is assigned to the \
dataset, it is stored in the `dataset_spatial` field instead and then copied \
into the `spatial` field before indexing. If no spatial is assigned, the \
spatial defaults to the organization spatial defined in the `org_spatial` \
field.\n
If this feature is just being implemented for the first time, some datasets \
might already have data in their `spatial` fields but their `dataset_spatial` \
fields would be empty, this would mean that the data would get overriden by \
the organization default and would be lost. To prevent that the command was \
created.\n
**********************************\n\n
"""
dry_run_help = """
This displays the title and ids of the datasets grouped by their organizations \
that would be affected by the migrate command when run without actually \
migrating them.
"""

@click.command(
    name='migrate',
    # There's a bug with ckan 2.9.4 that has been fixed in 2.9.5 where the
    # --help flag doesn't work as expected: https://github.com/ckan/ckan/issues/5755
    # For now the short_help will display the full help
    short_help=help,
    help=help,
    epilog=epilog,
    add_help_option=True
)
@click.option('--dry-run', 'dry_run', is_flag=True, help=dry_run_help)
def migrate_spatial(dry_run) -> None:
    echo("Sit tight, this might take a few minutes...")
    echo("Getting datasets to migrate...")
    mig_dict = get_datasets_to_migrate()

    if mig_dict['pkg_count'] < 1:
        echo('There are no datasets that need to be migrated.')
        return

    found_message = "Found {} datasets across {} organizations whose spatial fields need to be migrated.".format(
        mig_dict['pkg_count'], mig_dict['org_count'])
    if dry_run:
        message = """DATASETS TO BE MIGRATED BY ORGANIZATION\n\n"""
        for org_id in mig_dict['migration_dict']:
            title = mig_dict['migration_dict'][org_id]['title']
            name = mig_dict['migration_dict'][org_id]['name']
            message += '<ORGANIZATION title="{}" name={}>\n'.format(title, name)
            for data in mig_dict['migration_dict'][org_id]['datasets']:
                echo('DATASETS DATA')
                echo(data)
                title = data['title']
                name = data['name']
                message += '\t<DATASET title="{}" name={}>\n'.format(title, name)
        echo(message)

        echo(found_message)
        return

    echo(found_message)
    ctx = context.copy()
    ctx['allow_partial_update'] = True
    ctx['user'] = get_action('get_site_user')(context, {})['name']
    for org_id in mig_dict['migration_dict']:
        for data in mig_dict['migration_dict'][org_id]['datasets']:
            try:
                echo('\n\nATTEMPTING TO MIGRATE: <DATASET title="{}" name={}>'.format(
                    data['title'], data['name']))
                migrate_dataset(data, ctx)
            except Exception as e:
                echo(e)
                echo("UNABLE TO MIGRATE: <DATASET title={} name={}>".format(
                    data['title'], data['name']))
            break
    return

def get_org_spatials() -> dict:
    # Get all organizations
    org_ids = get_action('organization_list')(context, {})
    org_spatials = {}

    # For each organization, get the org spatial from that organization.
    for org_id in org_ids:
        org_dict = get_action('organization_show')(context, {
            "id": org_id,
            "include_datasets": False,
            "include_users": False,
            "include_groups": False,
            "include_tags": False,
            "include_followers": False
        })
        org_spatial = ''
        for extra in org_dict.get('extras', []):
            if extra['key'] == 'org_spatial':
                org_spatial = extra['value']
        org_spatials[org_dict['id']] = {
            'title': org_dict['title'],
            'name': org_dict['name'],
            'org_spatial': org_spatial
        }
        del org_dict
    
    return org_spatials

def needs_migration(pkg_dict: dict, org_spatials: dict):
    """
    Summary line.
  
    Extended description of function.
  
    Parameters:
    arg1 (int): Description of arg1
  
    Returns:
    int: Description of return value
  
    """
    dataset_spatial = pkg_dict['dataset_spatial']
    spatial = pkg_dict['spatial']
    # for extra in pkg_dict.get('extras', []):
    #     if extra['key'] == 'dataset_spatial':
    #         dataset_spatial = extra['value']
    #     if extra['key'] == 'spatial':
    #         spatial = extra['value']
    
    if is_valid_spatial(dataset_spatial):
        return False
    elif is_valid_spatial(spatial) and spatial != org_spatials[pkg_dict['owner_org']]['org_spatial']:
        return spatial

    return False

def get_datasets_to_migrate() -> dict:
    migration_dict = {}
    pkg_count = 0
    org_count = 0
    org_spatials = get_org_spatials()
    
    pkg_ids = all_package_list()
    for pkg_id in pkg_ids:
        data = get_action('package_show')(context, {
            "id": pkg_id
        })
        echo('PACKAGE_SHOW')
        echo(pformat(data))
        dataset_spatial = needs_migration(data, org_spatials)
        if dataset_spatial:
            data['dataset_spatial'] = dataset_spatial
            if migration_dict.get(data['owner_org'], None):
                migration_dict[data['owner_org']]['datasets'].append(data)
                migration_dict[data['owner_org']]['count'] += 1
                pkg_count += 1
            else:
                migration_dict[data['owner_org']] = org_spatials[data['owner_org']]
                migration_dict[data['owner_org']]['datasets'] = [data]
                migration_dict[data['owner_org']]['count'] = 1
                org_count += 1
                pkg_count += 1
    del org_spatials
    return {
        'migration_dict': migration_dict,
        'org_count': org_count,
        'pkg_count': pkg_count
    }

def migrate_dataset(data: dict, context: dict = context):
    """Updates the dataset_spatial field of a dataset

    Args:
        data (dict): object with `dataset_spatial` and `id` fields and any other required fields as per the schema
        context (dict, optional): context object. Defaults to script context.
    """
    updated = get_action('package_update')(context, data)
    echo('UPDATED DATASET')
    echo(pformat(updated))