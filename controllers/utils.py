import json
import functools
from odoo import http,tools
from odoo.http import request, route, Response
from odoo.exceptions import ValidationError

import traceback
from psycopg2 import IntegrityError
from odoo.exceptions import (
    AccessDenied,
    AccessError,
    UserError,
    ValidationError,
    MissingError,
)

def _parse_psql_integrity_error(e):
    message = "Database Constrains Error"
    if hasattr(e,'diag'):
        if e.diag.message_detail:
            message = e.diag.message_detail
        elif e.diag.message_primary:
            message = e.diag.message_primary
        elif e.diag.constraint_name:
            message = f"Constraint Error : {e.diag.constraint_name}"
    return message

def _unexpected_error(e):
    body = {"error":str(e)}
    try:
        if tools.config.get('dev_mode'):
            body['traceback'] = traceback.format_exc()
    except Exception:
        body['traceback'] = traceback.format_exc()
    return body

def handel_odoo_api_errors(e):
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

    else:
        return error_response(
            message=str(e),
            body=_unexpected_error(e),
            code=500,
        )

def check_api_token():
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
                key = input_token[len('Bearer '):]
                check_token_user = request.env['odoo.restful.user.tokens'].sudo()._token_verify(key)
                if not check_token_user:
                    return invalid_response(
                        code=400,
                        message="Invalid Authorization Token",
                    )
                request.update_env(user=check_token_user)
                return func(*args, **kwargs)
            except Exception as e:
                return handel_odoo_api_errors(e)
        return wrapper
    return decorator

def valid_response(body=None,message="Successfull",code=200,status=200):
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

def invalid_response(body=None,message="Invalid Request",code=400,status=400):
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

def error_response(body=None,message="Invalid Request",code=400,status=400):
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

def route_options(method):
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
            'auth': 'user',
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
            'auth': 'user',
            'methods': ['DELETE'],
            'csrf': False,
            'save_session': True,
            'cors': '*'
        },
    }
    return route_options[method.upper()]

def model_api_urls(prefix):
    return {
        f'{prefix}_get_all': f'/api/v1/{prefix}/search/all',
        f'{prefix}_get_one': f'/api/v1/{prefix}/search/one/<int:record_id>',
        f'{prefix}_filter':  f'/api/v1/{prefix}/filter',
        f'{prefix}_create':  f'/api/v1/{prefix}/create',
        f'{prefix}_update':  f'/api/v1/{prefix}/update/<int:record_id>',
        f'{prefix}_delete':  f'/api/v1/{prefix}/delete/<int:record_id>',
        f'{prefix}_action':  f'/api/v1/{prefix}/action/<int:record_id>',
    }

def get_json_body():
    """Parse and validate JSON request body."""
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