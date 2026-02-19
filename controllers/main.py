# -*- coding: utf-8 -*-
"""
Odoo REST API Controller
=========================

This controller exposes generic RESTful endpoints to allow external systems
to interact with Odoo models.

Main Features:
--------------
- User authentication (JWT based)
- Change password
- Generic CRUD operations
- Generic search/filter
- Execute model actions dynamically

Security Notes:
---------------
- Most model operations are executed using sudo().
- You MUST ensure proper token validation middleware exists in route_options().
- Exposing dynamic model access can be dangerous if not restricted properly.
"""

# ---------------------------------------------------------
# Standard Library
# ---------------------------------------------------------
import json

# ---------------------------------------------------------
# Odoo Imports
# ---------------------------------------------------------
from odoo import http
from odoo.http import request, route, Response
from odoo.exceptions import ValidationError, AccessError

# ---------------------------------------------------------
# Local Utilities (Custom Helpers)
# ---------------------------------------------------------
from .utils import *


class OdooApi(http.Controller):
    """
    Main REST Controller.

    All routes are prefixed with:
        /api/v1/

    All responses are JSON formatted.
    """

    # =====================================================
    # 1) USER AUTHENTICATION
    # =====================================================
    @route("/api/v1/login", **route_options('post'))
    def _authentication(self):
        """
        Authenticate user and generate JWT token.

        Request Body:
        -------------
        {
            "username": "user_login",
            "password": "user_password"
        }

        Response:
        ---------
        {
            "code": 200,
            "message": "User Login Successfully",
            "result": {
                "user_id": int,
                "username": str,
                "token": str
            }
        }
        """

        # Parse JSON body safely
        data, error = get_json_body()
        if error:
            return invalid_response(message=error)

        username = data.get('username')
        password = data.get('password')

        # Attempt authentication
        try:
            request.session.authenticate(request.db, username, password)
        except Exception as e:
            return handel_odoo_api_errors(str(e))

        # Retrieve authenticated user
        current_user = request.env.user

        # Generate JWT token
        token = request.env['odoo.restful.user.tokens'].sudo()._create_new_jwt_token(current_user)

        body = {
            "user_id": current_user.id,
            "username": username,
            "token": token,
        }

        return Response(
            json.dumps({
                "code": 200,
                "message": "User Login Successfully",
                "result": body
            }),
            status=200,
            content_type='application/json'
        )

    # =====================================================
    # 2) CHANGE PASSWORD
    # =====================================================
    @route("/api/v1/chanage_password", **route_options('post'))
    def _chanage_password(self):
        """
        Change current user password.

        Request Body:
        -------------
        {
            "old_password": "old_pass",
            "new_password": "new_pass"
        }
        """

        data, error = get_json_body()
        if error:
            return invalid_response(message=error)

        old_password = data.get('old_password')
        new_password = data.get('new_password')

        # Basic validations
        if not old_password or not new_password:
            return invalid_response(message="Old password and new password are required")

        if old_password == new_password:
            return invalid_response(message="Old password and new password cannot be the same")

        current_user = request.env.user

        # Validate old password by re-authentication
        try:
            request.session.authenticate(request.db, current_user.login, old_password)
        except Exception as e:
            return handel_odoo_api_errors(str(e))

        # Update password securely
        current_user.sudo().write({'password': new_password})

        return valid_response(message="Password Changed Successfully")

    # =====================================================
    # 3) CREATE RECORD
    # =====================================================
    @route('/api/v1/<string:model_name>/create', **route_options('post'))
    def _create_new_records(self, model_name, **kwargs):
        """
        Create new record dynamically.

        Request Body:
        -------------
        {
            "field_1": value,
            "field_2": value,
            "list_of_fields": ["id", "name"]
        }
        """

        data, error = get_json_body()
        if error:
            return invalid_response(message=error)

        display_fields = data.pop('list_of_fields', None)

        response = request.env[model_name].sudo()._create_new_record(
            data,
            list_of_fields=display_fields
        )

        return valid_response(
            message="New record created successfully",
            body=response
        )

    # =====================================================
    # 4) UPDATE RECORD
    # =====================================================
    @route('/api/v1/<string:model_name>/update', **route_options('put'))
    def _update_existing_records(self, model_name, **kwargs):
        """
        Update existing record dynamically.
        """

        data, error = get_json_body()
        if error:
            return invalid_response(message=error)

        display_fields = data.pop('list_of_fields', None)

        response = request.env[model_name].sudo()._update_existing_record(
            data,
            list_of_fields=display_fields
        )

        return valid_response(
            message="Existing record updated successfully",
            body=response
        )

    # =====================================================
    # 5) DELETE RECORD
    # =====================================================
    @route('/api/v1/<string:model_name>/delete/<int:record_id>', **route_options('delete'))
    def _delete_existing_records(self, model_name, record_id, **kwargs):
        """
        Delete record by ID.
        """

        if not record_id:
            return invalid_response(message="Record id is required")

        response = request.env[model_name].sudo()._api_delete_one(record_id)

        return valid_response(
            message="Record deleted successfully",
            body=response
        )

    # =====================================================
    # 6) SEARCH ALL RECORDS
    # =====================================================
    @route('/api/v1/<string:model_name>/search/all', **route_options('get'))
    def _get_all_records(self, model_name, **kwargs):
        """
        Search records with domain, limit and offset.
        """

        data, error = get_json_body()
        if error:
            return invalid_response(message=error)

        response = request.env[model_name].sudo()._api_search_all(
            data.get('domain', []),
            data.get('limit', 100),
            data.get('offset', 0),
            data.get('list_of_fields')
        )

        return valid_response(
            message="All records retrieved successfully",
            body=response
        )

    # =====================================================
    # 7) SEARCH ONE RECORD
    # =====================================================
    @route('/api/v1/<string:model_name>/search/one/<int:record_id>', **route_options('get'))
    def _get_one_record(self, model_name, record_id, **kwargs):
        """
        Retrieve single record by ID.
        """

        data, error = get_json_body()
        if error:
            return invalid_response(message=error)

        if not record_id:
            return invalid_response(message="Record id is required")

        response = request.env[model_name].sudo()._api_search_one(
            record_id,
            data.get('list_of_fields')
        )

        return valid_response(
            message="Record found successfully",
            body=response
        )

    # =====================================================
    # 8) FILTER RECORDS
    # =====================================================
    @route('/api/v1/<string:model_name>/filter', **route_options('get'))
    def _get_records_filters(self, model_name, **kwargs):
        """
        Filter records using domain + keyword search.
        """

        data, error = get_json_body()
        if error:
            return invalid_response(message=error)

        key = kwargs.get('query')
        domain = data.get('domain')

        response = request.env[model_name].sudo()._api_filter_with_keywords(
            domain,
            key,
            data.get('list_of_fields')
        )

        return valid_response(
            message="Record filtered successfully",
            body=response
        )

    # =====================================================
    # 9) EXECUTE ACTION ON RECORD
    # =====================================================
    @route('/api/v1/<string:model_name>/action/<int:record_id>', **route_options('post'))
    def run_action_on_record(self, model_name, record_id):
        """
        Execute dynamic method on a record.

        Request Body:
        -------------
        {
            "action_name": "method_name"
        }

        Security:
        ---------
        - Validates model existence
        - Validates record existence
        - Validates method existence
        - Validates method is callable
        """

        try:
            data, error = get_json_body()
            if error:
                return invalid_response(message=error)

            action_name = data.get('action_name')

            if not action_name:
                return invalid_response("Missing action_name")

            if model_name not in request.env:
                return invalid_response("Invalid model")

            record = request.env[model_name].sudo().browse(record_id)

            if not record.exists():
                return invalid_response("Record not found")

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
