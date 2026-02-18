import jwt
from datetime import timedelta
from odoo import api, fields, models


class UsersAccessToken(models.Model):
    _name = 'odoo.restful.user.tokens'
    _description = 'Odoo Restful User Tokens'

    token = fields.Char(
        string='Token',
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        required=True,
        ondelete='cascade',
    )
    expires = fields.Datetime(
        string='Expires',
        required=True,
    )
    is_expired = fields.Boolean(
        string='Is Expired',
        compute='_compute_expires',
    )

    @api.depends_context('context_today')
    @api.depends('expires')
    def _compute_expires(self):
        for token in self:
            token.is_expired = fields.Datetime.now() > token.expires

    @api.model
    def _create_new_jwt_token(self, user):
        expire = fields.Datetime.now() + timedelta(days=10)
        payload = {
            'exp': expire ,
            'iat': fields.Datetime.now(),
            'sub': user.id,
            'lgn': user.login,
        }

        token = jwt.encode(payload, 'ODOO_JWT_KEY', algorithm='HS256')
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        values = {
            'user_id': user.id,
            'expires': expire,
            'token': token,
        }
        self.env['odoo.restful.user.tokens'].create(values)
        return token

    def _token_verify(self, token):
        domain = [('token','=',token),('is_expired','=',False)]
        token_rec = self.env[self._name].search(domain, limit=1)
        if token_rec:
            return token_rec.user_id
        return False

    @api.autovacuum
    def _delete_expired_token(self):
        for token in self:
            if token.is_expired:
                token.unlink()


class ResUsers(models.Model):
    _inherit = 'res.users'

    user_token_ids = fields.One2many(
        comodel_name='odoo.restful.user.tokens',
        inverse_name='user_id',
        string='User Tokens',
    )