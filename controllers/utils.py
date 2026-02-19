# -*- coding: utf-8 -*-
"""
Odoo REST API Utilities
=======================

This module provides:
---------------------
- Unified error handling
- Standardized JSON responses
- JWT token validation decorator
- Route configuration helper
- JSON request parsing
- Database constraint error parsing

Design Goals:
-------------
- Centralize all HTTP response formats
- Normalize Odoo exception mapping
- Provide consistent API contract
- Avoid code duplication across controllers

IMPORTANT:
----------
This layer assumes JWT token verification is implemented in:
    model: odoo.restful.user.tokens
"""

# ---------------------------------------------------------
# Standard Library
# ---------------------------------------------------------
import json
import functools
import traceback

# ---------------------------------------------------------
# Odoo Imports
# ---------------------------------------------------------
from odoo import http, tools
from odoo.http import request, route, Response
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    UserError,
    ValidationError,
    MissingError,
)

# ---------------------------------------------------------
# External Libraries
# ---------------------------------------------------------
from psycopg2 import IntegrityError

# ==========================================================
# 🔎 DATABASE ERROR PARSING
# ==========================================================

def _parse_psql_integrity_error(e):
    """
    Extract readable error message from PostgreSQL IntegrityError.

    Handles:
    --------
    - Unique constraint violations
    - Foreign key constraint violations
    - Not-null constraint violations
    - Check constraints

    Priority:
    ---------
    1) message_detail
    2) message_primary
    3) constraint_name
    4) fallback message

    Returns:
        str: User-friendly database constraint error
    """
    message = "Database Constraint Error"

    if hasattr(e, 'diag'):
        if e.diag.message_detail:
            message = e.diag.message_detail
        elif e.diag.message_primary:
            message = e.diag.message_primary
        elif e.diag.constraint_name:
            message = f"Constraint Error: {e.diag.constraint_name}"

    return message

# ==========================================================
# ⚠️ UNEXPECTED ERROR HANDLER
# ==========================================================

def _unexpected_error(e):
    """
    Handle unexpected system errors.

    If dev_mode is enabled in Odoo config,
    include full traceback for debugging.

    Returns:
        dict: error body with optional traceback
    """
    body = {"error": str(e)}

    try:
        if tools.config.get('dev_mode'):
            body['traceback'] = traceback.format_exc()
    except Exception:
        # Fallback if config access fails
        body['traceback'] = traceback.format_exc()

    return body

# ==========================================================
# 🎯 CENTRALIZED ODOO ERROR MAPPER
# ==========================================================

def handel_odoo_api_errors(e):
    """
    Convert Odoo / Database exceptions into unified API responses.

    Mapping Strategy:
    -----------------
    IntegrityError     → 400 (Constraint violation)
    ValidationError    → 402
    AccessDenied       → 401
    AccessError        → 403
    MissingError       → 404
    UserError          → 400
    Others             → 500

    Returns:
        Response: JSON HTTP response
    """

    if isinstance(e, IntegrityError):
        return error_response(
            message=_parse_psql_integrity_error(e),
            code=400,
        )

    if isinstance(e, ValidationError):
        return error_response(
            message=str(e),
            code=402,
        )

    if isinstance(e, AccessDenied):
        return error_response(
            message="Access Denied",
            code=401,
        )

    if isinstance(e, AccessError):
        return error_response(
            message="Access Error",
            code=403,
        )

    if isinstance(e, MissingError):
        return error_response(
            message=str(e),
            code=404,
        )

    if isinstance(e, UserError):
        return error_response(
            message=str(e),
            code=400,
        )

    # Fallback → unexpected server error
    return error_response(
        message=str(e),
        body=_unexpected_error(e),
        code=500,
    )

# ==========================================================
# 🔐 TOKEN VALIDATION DECORATOR
# ==========================================================

def check_api_token():
    """
    Decorator to validate JWT token before route execution.

    Expected Header:
        Authorization: Bearer <token>

    Flow:
    -----
    1) Extract Authorization header
    2) Validate format
    3) Verify token via model
    4) Update request.env user
    5) Execute endpoint

    Security Notes:
    ---------------
    - Token must be cryptographically verified.
    - Should validate expiration.
    - Should validate user active status.
    """

    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                input_token = request.httprequest.headers.get('Authorization')

                if not input_token or not input_token.startswith('Bearer '):
                    return invalid_response(
                        code=400,
                        message="Missing or Invalid Authorization Header",
                    )

                # Extract raw token
                key = input_token[len('Bearer '):]

                # Verify token in custom model
                check_token_user = request.env['odoo.restful.user.tokens'].sudo()._token_verify(key)

                if not check_token_user:
                    return invalid_response(
                        code=400,
                        message="Invalid Authorization Token",
                    )

                # Inject authenticated user into environment
                request.update_env(user=check_token_user)

                return func(*args, **kwargs)

            except Exception as e:
                return handel_odoo_api_errors(e)

        return wrapper

    return decorator

# ==========================================================
# 📤 RESPONSE BUILDERS
# ==========================================================

def valid_response(body=None, message="Successful", code=200, status=200):
    """
    Return standardized success response.
    """
    if body is None:
        body = {}

    return Response(
        json.dumps({
            "code": code,
            "message": message,
            "body": body,
        }),
        status=status,
        content_type='application/json'
    )

def invalid_response(body=None, message="Invalid Request", code=400, status=400):
    """
    Return standardized invalid request response.
    """
    if body is None:
        body = {}

    return Response(
        json.dumps({
            "code": code,
            "message": message,
            "body": body,
        }),
        status=status,
        content_type='application/json'
    )

def error_response(body=None, message="Error", code=400, status=400):
    """
    Return standardized error response.
    Used by exception mapper.
    """
    if body is None:
        body = {}

    return Response(
        json.dumps({
            "code": code,
            "message": message,
            "body": body,
        }),
        status=status,
        content_type='application/json'
    )

# ==========================================================
# 🛣 ROUTE OPTIONS HELPER
# ==========================================================

def route_options(method):
    """
    Return standardized route configuration.

    Supports:
        GET
        POST
        PUT
        DELETE

    Notes:
    ------
    - CSRF disabled for API usage.
    - CORS enabled.
    - save_session enabled only when needed.
    """

    route_options = {
        'GET': {
            'type': 'http',
            'auth': 'none',
            'methods': ['GET'],
            'csrf': False,
            'save_session': False,
            'cors': '*'
        },
        'POST': {
            'type': 'http',
            'auth': 'none',
            'methods': ['POST'],
            'csrf': False,
            'save_session': True,
            'cors': '*'
        },
        'PUT': {
            'type': 'http',
            'auth': 'none',
            'methods': ['PUT'],
            'csrf': False,
            'save_session': False,
            'cors': '*'
        },
        'DELETE': {
            'type': 'http',
            'auth': 'none',
            'methods': ['DELETE'],
            'csrf': False,
            'save_session': True,
            'cors': '*'
        },
    }

    return route_options[method.upper()]

# ==========================================================
# 📥 JSON BODY PARSER
# ==========================================================

def get_json_body():
    """
    Parse and validate JSON request body.

    Returns:
        tuple:
            (dict_data, None) if valid
            (None, Response) if error

    Handles:
    --------
    - Missing body
    - Invalid JSON
    """

    if not request.httprequest.data:
        return None, invalid_response(
            message="Missing request body",
            body={},
            code=400,
        )

    try:
        return json.loads(request.httprequest.data.decode('utf-8')), None

    except ValueError:
        return None, invalid_response(
            message="Invalid JSON body",
            body={},
            code=400,
        )
