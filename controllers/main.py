# -*- coding: utf-8 -*-
# ----------------------------
# From Odoo --> Other
# ----------------------------
import json
from odoo import http
from odoo.http import request, route, Response
from odoo.exceptions import ValidationError,AccessError
from .utils import *

class OdooApi(http.Controller):

    @route("/api/v1/login",**route_options('post'))
    def _authentication(self):
        data, error = get_json_body()
        if error:
            return invalid_response(message=error)
        username = data.get('username')
        password = data.get('password')
        # -------------------------------------------------------------------------
        # O18
        # --------------------------------------------------------------------------
        # credentials = {'login': username, 'password': password,'type':'password'}
        # request.session.authenticate(request.db,credentials)
        # --------------------------------------------------------------------------
        try:
            user_info = request.session.authenticate(request.db, username, password)
        except Exception as e:
            return handel_odoo_api_errors(str(e))

        current_user = request.env.user
        token = request.env['odoo.restful.user.tokens'].sudo()._create_new_jwt_token(current_user)
        body = {
            "user_id":current_user.id,
            "username":username,
            "token":token,
        }
        return Response(
            json.dumps({"code":200,"message":"User Loging Successfully","result":body}),
            status=200,
            content_type='application/json'
        )

    @route("/api/v1/chanage_password",**route_options('post'))
    def _chanage_password(self):
        data, error = get_json_body()
        if error:
            return invalid_response(message=error)
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password and not new_password:
            return invalid_response(message="Old password or new password is required")

        if old_password == new_password:
            return invalid_response(message="Old password and new password are equal")

        current_user = request.env.user
        try:
            user_info = request.session.authenticate(request.db, current_user.login, old_password)
        except Exception as e:
            return handel_odoo_api_errors(str(e))

        current_user.sudo().write({'password': new_password})
        return valid_response(message="Password Changed Successfully")

    @route('/api/v1/<string:model_name>/create',**route_options('post'))
    def _create_new_records(self,model_name,**kwargs):
        data, error = get_json_body()
        if error:
            return invalid_response(message=error)
        display_fields = data.pop('list_of_fields',None)
        resposnse = request.env[model_name].sudo()._create_new_record(data,list_of_fields=display_fields)
        return valid_response(message="New record created successfully",body=resposnse)

    @route('/api/v1/<string:model_name>/update', **route_options('put'))
    def _update_existing_records(self,model_name,**kwargs):
        data, error = get_json_body()
        if error:
            return invalid_response(message=error)
        display_fields = data.pop('list_of_fields', None)
        resposnse = request.env[model_name].sudo()._update_existing_record(data,list_of_fields=display_fields)
        return valid_response(message="Existing record updated successfully", body=resposnse)

    @route('/api/v1/<string:model_name>/delete/<int:record_id>', **route_options('delete'))
    def _delete_existing_records(self,model_name,record_id,**kwargs):
        if not record_id:
            return invalid_response(message="Record id is required")
        resposnse = request.env[model_name].sudo()._api_delete_one(record_id)
        return valid_response(message="Record deleted successfully", body=resposnse)

    @route('/api/v1/<string:model_name>/search/all', **route_options('get'))
    def _get_all_records(self,model_name,**kwargs):
        data, error = get_json_body()
        if error:
            return invalid_response(message=error)
        resposnse = request.env[model_name].sudo()._api_search_all(
            data.get('domain',[]),
            data.get('limit',100),
            data.get('offset',0),
            data.get('list_of_fields')
        )
        return valid_response(message="All records retrieved successfully",body=resposnse)

    @route('/api/v1/<string:model_name>/search/one/<int:record_id>', **route_options('get'))
    def _get_one_record(self,model_name,record_id,**kwargs):
        data, error = get_json_body()
        if error:
            return invalid_response(message=error)
        if not record_id:
            return invalid_response(message="Record id is required")
        resposnse = request.env[model_name].sudo()._api_search_one(record_id,data.get('list_of_fields'))
        return valid_response(message="Record found successfully",body=resposnse)

    @route('/api/v1/<string:model_name>/filter', **route_options('get'))
    def _get_records_filters(self,model_name,**kwargs):
        data, error = get_json_body()
        if error:
            return invalid_response(message=error)
        key = kwargs.get('query')
        domain = data.get('domain')
        resposnse = request.env[model_name].sudo()._api_filter_with_keywords(domain,key,data.get('list_of_fields'))
        return valid_response(message="Record filtered successfully",body=resposnse)

    @route('/api/v1/<string:model_name>/action/<int:record_id>', **route_options('post'))
    def run_action_on_record(self, model_name, record_id):
        try:
            data, error = get_json_body()
            if error:
                return invalid_response(message=error)
            action_name = data.get('action_name')

            if not action_name:
                return invalid_response("Missing action_name")

            # Validate model existence
            if model_name not in request.env:
                return invalid_response("Invalid model")

            record = request.env[model_name].sudo().browse(record_id)

            if not record.exists():
                return invalid_response("Record not found")

            # Validate action exists
            if not hasattr(record, action_name):
                return invalid_response("Invalid action")

            method = getattr(record, action_name)

            if not callable(method):
                return invalid_response("Action is not callable")

            result = method()
            response = {
                'error': False,
                'record_id': record.id,
                'action': action_name,
                'message': f"Action '{action_name}' executed successfully"
            }
            if result:
                response.update({"action_result": result})

            return valid_response(
                message="Action executed successfully",
                body=response
            )

        except AccessError:
            return invalid_response("Access denied")
        except Exception:
            return invalid_response("Unexpected server error")