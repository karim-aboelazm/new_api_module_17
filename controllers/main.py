# -*- coding: utf-8 -*-
# ----------------------------
"""

Api ----->
----------------------
1) From Odoo To Others
----------------------
-> http
    -> request -> Used for generate odoo env
               -> request.env.user.id
               -> request.env['res.users']

    -> route   -> route [url]
               -> auth [public, user, none]
               -> type [http,json]
               -> method [GET, POST, PUT, DELETE]
                    ** GET --> retreive data from Odoo
                    ** POST --> create new record in Odoo or run actions or methods
                    ** PUT --> update record in Odoo
                    ** DELETE --> delete record in Odoo
               -> save_session = False
               -> cros = "*"

    -> Controller -> base controller Class

    -> JWT (JSON Web Token)

class TestOdooApi(http.Controller):

    @http.route("/api/v1/get_all_users", type="http", auth="user",method=['GET'], csrf=False, save_session=False,cors="*")
    def get_all_users(self,*args,**kwargs):
        all_users = request.env['res.users'].search([])
        return all_users


2. Check Token, responses, error handel
------------------------------------------

3. prepare base model for api
----------------------------------
1) from_dict   --> cleaning and prepareing data which come from users in api and gegenrate recordset values
2) to_dict     --> give me output standard for record as json
3) create , update , search , delete , run proccess ....


2) From Other To Odoo
----------------------

"""

import json
from odoo import http
from odoo.http import request, route, Response
from odoo.exceptions import ValidationError
from .utils import *

class OdooApi(http.Controller):

    @route("/api/v1/login",**route_options('post'))
    def generate_new_access_token(self):
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

    @route(model_api_urls('users'),**route_options('get'))
    @check_api_token()
    def get_all_users(self,user_id=None,query=None):
        data, error = get_json_body()
        if error:
            return invalid_response(message=error)
        domain = data.get('domain',[])
        limit = data.get('limit',100)
        fields = data.get('fields',[])
        all_users = request.env['res.users']._api_search_all(domain=domain,limit=limit,list_of_fields=fields)
        return valid_response(body=all_users,message="User Retreive Successfully")

    @route(model_api_urls('partner'),**route_options('post'))
    @check_api_token()
    def create_new_partner(self):
        data, error = get_json_body()
        if error:
            return invalid_response(message=error)
        partner = request.env['res.partner']._create_new_record(data,list_of_fields=data.get('fields',[]))
        return valid_response(body=partner,message="Partner Created Successfully")