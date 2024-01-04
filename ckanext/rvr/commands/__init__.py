import click

from ckanext.rvr.commands.migrate_spatial_fields import migrate_spatial

short_help = "CLI commands for the ckanext-rvr extension's rvr_spatial_query plugin."
@click.group(name='rvr-spatial', short_help=short_help, add_help_option=True)
def rvr_spatial() -> None:
    pass

rvr_spatial.add_command(migrate_spatial)
