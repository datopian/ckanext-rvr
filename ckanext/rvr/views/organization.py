import logging
import json

from flask import Blueprint

import ckan.lib.helpers as h
import ckan.lib.base as base
import ckan.logic as logic
import ckan.lib.navl.dictization_functions as dict_fns
from ckan.common import g, request, _
from ckan.views.group import (
    EditGroupView,
    set_org,
    _action,
    _force_reindex,
    CreateGroupView,
    _setup_template_variables,
    _get_group_template,
)
from ckan.views.home import CACHE_PARAMETERS

from ckanext.rvr.actions import update_dataset_spatial

log = logging.getLogger(__name__)

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params

organization_blueprint = Blueprint(
    "rvr_organization",
    __name__,
    url_prefix="/organization",
    url_defaults={"group_type": "organization", "is_organization": True},
)


class EditOrganizationView(EditGroupView):
    """
    Edit Organization View
    """

    def post(self, group_type, is_organization, id=None):
        set_org(is_organization)
        context = self._prepare(id, is_organization)

        try:
            # Get the old coordinates for the organization to check if the
            # map data for the organization has been updated

            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
            data_dict.update(
                clean_dict(
                    dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
                )
            )
            context["message"] = data_dict.get("log_message", "")
            data_dict["id"] = context["id"]
            context["allow_partial_update"] = True

            # Check if the map data has been updated
            org_spatial = data_dict.get("org_spatial", None)

            old_group_dict = _action("organization_show")(
                context, {"id": id, "include_datasets": False}
            )
            old_org_spatial = ""
            for extra in old_group_dict.get("extras", []):
                if extra.get("key") == "org_spatial":
                    old_org_spatial = extra.get("value")

            group = _action("group_update")(context, data_dict)
            if org_spatial != old_org_spatial:
                update_dataset_spatial(group)
            elif id != group["name"]:
                # if the org_spatial has changed, a reindex would be done already
                _force_reindex(group)

        except (NotFound, NotAuthorized) as e:
            base.abort(404, _("Group not found"))
        except dict_fns.DataError:
            base.abort(400, _("Integrity Error"))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(
                id, group_type, is_organization, data_dict, errors, error_summary
            )
        return h.redirect_to(group["type"] + ".read", id=group["name"])

    def get(
        self,
        id,
        group_type,
        is_organization,
        data=None,
        errors=None,
        error_summary=None,
    ):
        extra_vars = {}
        set_org(is_organization)

        context = self._prepare(id, is_organization)
        data_dict = {"id": id, "include_datasets": False}
        try:
            group_dict = _action("group_show")(context, data_dict)
        except (NotFound, NotAuthorized):
            base.abort(404, _("Group not found"))
        data = data or group_dict
        errors = errors or {}

        # Remove the org_spatial from extra before passing it to the template
        org_spatial = ""
        if data.get("extras", None):
            for extra in data["extras"]:
                if extra.get("key") == "org_spatial":
                    org_spatial = extra.get("value")
                    data["extras"].remove(extra)

        extra_vars = {
            "data": data,
            "group_dict": group_dict,
            "errors": errors,
            "error_summary": error_summary,
            "action": "edit",
            "group_type": group_type,
            "org_spatial": org_spatial,
        }

        _setup_template_variables(context, data, group_type=group_type)
        form = base.render(_get_group_template("group_form", group_type), extra_vars)

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.grouptitle = group_dict.get("title")
        g.groupname = group_dict.get("name")
        g.data = data
        g.group_dict = group_dict

        extra_vars["form"] = form
        return base.render(_get_group_template("edit_template", group_type), extra_vars)


class CreateOrganizationView(CreateGroupView):
    def post(self, group_type, is_organization):
        set_org(is_organization)
        context = self._prepare()
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
            data_dict.update(
                clean_dict(
                    dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
                )
            )
            data_dict["type"] = group_type or "group"
            context["message"] = data_dict.get("log_message", "")
            data_dict["users"] = [{"name": g.user, "capacity": "admin"}]
            group = _action("group_create")(context, data_dict)

        except (NotFound, NotAuthorized) as e:
            base.abort(404, _("Group not found"))
        except dict_fns.DataError:
            base.abort(400, _("Integrity Error"))
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(
                group_type, is_organization, data_dict, errors, error_summary
            )

        return h.redirect_to(group["type"] + ".read", id=group["name"])

    def get(
        self, group_type, is_organization, data=None, errors=None, error_summary=None
    ):
        extra_vars = {}
        set_org(is_organization)
        context = self._prepare()
        data = data or clean_dict(
            dict_fns.unflatten(
                tuplize_dict(parse_params(request.args, ignore_keys=CACHE_PARAMETERS))
            )
        )

        if not data.get("image_url", "").startswith("http"):
            data.pop("image_url", None)
        errors = errors or {}
        error_summary = error_summary or {}

        # Remove the org_spatial from extra before passing it to the template
        org_spatial = ""
        if data.get("extras", None):
            for extra in data["extras"]:
                if extra.get("key") == "org_spatial":
                    org_spatial = extra.get("value")
                    data["extras"].remove(extra)

        extra_vars = {
            "data": data,
            "errors": errors,
            "error_summary": error_summary,
            "action": "new",
            "group_type": group_type,
            "org_spatial": org_spatial,
        }
        _setup_template_variables(context, data, group_type=group_type)
        form = base.render(_get_group_template("group_form", group_type), extra_vars)

        # TODO: Remove
        # ckan 2.9: Adding variables that were removed from c object for
        # compatibility with templates in existing extensions
        g.form = form

        extra_vars["form"] = form
        return base.render(_get_group_template("new_template", group_type), extra_vars)


organization_blueprint.add_url_rule(
    "/edit/<id>", view_func=EditOrganizationView.as_view("edit")
)
organization_blueprint.add_url_rule(
    "/new", methods=["GET", "POST"], view_func=CreateGroupView.as_view(str("new"))
)
