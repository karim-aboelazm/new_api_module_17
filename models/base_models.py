import base64
import json as pyjson
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import re

def html_to_text(html_code):
    if not html_code:
        return ''
    return re.sub(r'<[^>]+>', '', html_code)


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _from_dict(self, data):
        """
        Convert a dict into ORM-compatible vals for all fields,
        including binary, json, relational, date/datetime fields,
        and automatically handle nested attachments.
        """
        if not isinstance(data, dict):
            return {}

        vals = {}

        for field_name, field in self._fields.items():
            if field_name not in data:
                continue

            value = data[field_name]

            # ------------------
            # Many2one
            # ------------------
            if field.type == 'many2one':
                if value:
                    record = self.env[field.comodel_name].browse(value)
                    if not record.exists():
                        raise UserError(_("Invalid ID %s for field '%s'") % (value, field_name))
                    vals[field_name] = record.id

            # ------------------
            # Many2many
            # ------------------
            elif field.type == 'many2many':
                if isinstance(value, list):
                    commands = []

                    for item in value:
                        if isinstance(item, dict):
                            # --- Flatten attachments ---
                            if 'attachment' in field.name:
                                attach_commands = []
                                for key in list(item.keys()):
                                    if 'attachment' in key:
                                        attachments = item.pop(key)
                                        if isinstance(attachments, list):
                                            for att in attachments:
                                                # Flat attachment
                                                if isinstance(att, dict) and 'attachment' in att:
                                                    attach_commands.append((0, 0, {
                                                        'name': att.get('name', 'file'),
                                                        'datas': att.get('attachment'),
                                                        'type': 'binary',
                                                    }))
                                                # Nested attachments inside a group
                                                elif isinstance(att, dict) and 'attachment_ids' in att:
                                                    for sub in att['attachment_ids']:
                                                        if isinstance(sub, dict) and sub.get('attachment'):
                                                            attach_commands.append((0, 0, {
                                                                'name': sub.get('name', 'file'),
                                                                'datas': sub.get('attachment'),
                                                                'type': 'binary',
                                                            }))
                                        elif isinstance(attachments, str):
                                            attach_commands.append((0, 0, {
                                                'name': item.get('name', 'file'),
                                                'datas': attachments,
                                                'type': 'binary',
                                            }))

                                if len(attach_commands) == 1:
                                    commands.append(attach_commands)
                                else:
                                    commands.extend(list(set(attach_commands)))

                            # --- Append proper m2m command ---
                            if 'id' in item and len(item) == 1:  # Only ID exists
                                commands.append((4, item['id']))
                            else:
                                commands.append((0, 0, item))

                        elif isinstance(item, int):
                            commands.append((4, item))

                    if commands:
                        vals[field_name] = commands


            # ------------------
            # One2many
            # ------------------
            elif field.type == 'one2many':
                if isinstance(value, list):
                    commands = []

                    for item in value:
                        if isinstance(item, dict):
                            # --- Flatten attachments ---
                            for key in list(item.keys()):
                                if key == 'attachment_ids' or key.endswith('_attachment_ids'):
                                    attachments = item.pop(key)
                                    if isinstance(attachments, list):
                                        attach_commands = []
                                        for att in attachments:
                                            # Flat attachment
                                            if isinstance(att, dict) and 'attachment' in att:
                                                attach_commands.append((0, 0, {
                                                    'name': att.get('name', 'file'),
                                                    'datas': att.get('attachment'),
                                                    'type': 'binary',
                                                }))
                                            # Nested attachments inside a group
                                            elif isinstance(att, dict) and 'attachment_ids' in att:
                                                for sub in att['attachment_ids']:
                                                    if isinstance(sub, dict) and sub.get('attachment'):
                                                        attach_commands.append((0, 0, {
                                                            'name': sub.get('name', 'file'),
                                                            'datas': sub.get('attachment'),
                                                            'type': 'binary',
                                                        }))
                                        if attach_commands:
                                            item['attachment_ids'] = attach_commands

                            # --- Append o2m command ---
                            commands.append((0, 0, item))

                        elif isinstance(item, int):
                            # Normally O2M should not be int, but just in case
                            commands.append((4, item))

                    if commands:
                        vals[field_name] = commands

            # ------------------
            # Date / Datetime
            # ------------------
            elif field.type == 'date':
                if isinstance(value, str):
                    try:
                        vals[field_name] = datetime.strptime(value, "%Y-%m-%d").date()
                    except Exception:
                        raise UserError(_("Invalid date format for field '%s': %s") % (field_name, value))
                else:
                    vals[field_name] = value

            elif field.type == 'datetime':
                if isinstance(value, str):
                    try:
                        vals[field_name] = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        raise UserError(_("Invalid datetime format for field '%s': %s") % (field_name, value))
                else:
                    vals[field_name] = value

            # ------------------
            # Binary
            # ------------------
            elif field.type == 'binary':
                if isinstance(value, str):
                    vals[field_name] = value
                elif isinstance(value, bytes):
                    vals[field_name] = base64.b64encode(value).decode('utf-8')
                else:
                    raise UserError(_("Invalid binary value for field '%s'") % field_name)

            # ------------------
            # JSON / Serialized
            # ------------------
            elif field.type in ['json', 'serialized']:
                if isinstance(value, str):
                    try:
                        vals[field_name] = pyjson.loads(value)
                    except Exception:
                        raise UserError(_("Invalid JSON for field '%s': %s") % (field_name, value))
                else:
                    vals[field_name] = value

            # ------------------
            # Simple fields
            # ------------------
            else:
                vals[field_name] = value

        return vals

    def _fields_not_display(self):
        return {
            "message_ids", "my_activity_date_deadline","message_follower_ids", "message_partner_ids",
            "message_attachment_count", "message_unread", "message_unread_counter",
            "message_needaction", "message_needaction_counter", "message_has_error","display_name"
            "message_has_error_counter", "message_has_sms_error", "message_is_follower",
            "message_main_attachment_id", "activity_ids", "activity_state",
            "activity_user_id", "activity_type_id", "activity_date_deadline",
            "activity_summary", "activity_exception_decoration", "activity_exception_icon",
            "website_message_ids", "message_notify", "message_subtype_id", "duration_tracking",
            "activity_calendar_event_id","activity_type_icon","Record_count","create_date","create_uid","write_date","write_uid"
        }

    def _to_dict(self, list_of_fields=None, recurse_many2one=True, skip_chatter=True, memo=None):
        if memo is None:
            memo = set()

        if len(self) > 1:
            return [rec._to_dict(list_of_fields, recurse_many2one, skip_chatter, memo) for rec in self]

        if not self:
            return {}

        self.ensure_one()

        record_ref = (self._name, self.id)
        if record_ref in memo:
            return {"id": self.id, "name": self.display_name}
        memo.add(record_ref)

        CHATTER_FIELDS = self._fields_not_display()

        def fmt_value(val, field):
            # normalize empty values
            if val in [False, None, '']:
                if field.type in ['char', 'text', 'selection']:
                    return ""
                elif field.type == 'many2one':
                    return {}
                elif field.type in ['many2many', 'one2many']:
                    return []
                else:
                    return False

            # strip string-like fields
            if field.type in ['char', 'text', 'selection', 'html'] and isinstance(val, str):
                val = val.strip().replace("\u200F", "")

                if field.type == 'html':
                    val = html_to_text(val)

            if field.type == 'date':
                return val.strftime('%Y-%m-%d')
            elif field.type == 'datetime':
                return val.strftime('%Y-%m-%d %H:%M:%S')
            elif field.type == 'binary':
                return base64.b64encode(val).decode('utf-8') if isinstance(val, bytes) else val
            elif field.type == 'many2one':
                if not val:
                    return {}
                if recurse_many2one:
                    return {"id": val.id, "name": val.display_name}
                return val.id
            elif field.type in ['one2many', 'many2many']:
                return [{"id": r.id, "name": r.display_name} for r in val]

            return val

        res = {}
        target_fields = list_of_fields if list_of_fields else self._fields.keys()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for name in target_fields:
            if name not in self._fields:
                continue
            if skip_chatter and name in CHATTER_FIELDS:
                continue

            field = self._fields[name]

            try:
                value = self[name]
                if field.comodel_name == 'ir.attachment' and field.type in ['one2many', 'many2many']:
                    res[name] = [{
                        "id": att.id,
                        "name": att.display_name,
                        "mimetype": att.mimetype,
                        "url": f"{base_url}/web/content/{att.id}"
                    } for att in value] or []
                else:
                    res[name] = fmt_value(value, field)

                if field.type in ['one2many', 'many2many']:
                    res[f"{name}_count"] = len(value)

            except Exception as e:
                res[name] = fmt_value(False, field)
                if field.type in ['one2many', 'many2many']:
                    res[f"{name}_count"] = 0

        FIELD_ORDER = ['char', 'text', 'boolean', 'float', 'integer', 'date', 'datetime', 'many2one', 'many2many',
                       'one2many']
        ordered_res = {}

        for key in ['id', 'name']:
            if key in res:
                ordered_res[key] = res.pop(key)

        for ftype in FIELD_ORDER:
            for key in list(res.keys()):
                field = self._fields.get(key)
                if field and field.type == ftype:
                    ordered_res[key] = res.pop(key)
                    if field.type in ['one2many', 'many2many']:
                        count_key = f"{key}_count"
                        if count_key in res:
                            ordered_res[count_key] = res.pop(count_key)

        ordered_res['name'] = self.display_name
        ordered_res.update(res)

        return ordered_res

    @api.model
    def _create_new_record(self, data, list_of_fields=None):
        formated_data = self._from_dict(data)
        record = self.sudo().create(formated_data)
        return record._to_dict(list_of_fields=list_of_fields)

    @api.model
    def _update_existing_record(self, data, list_of_fields=None):
        record_id = data.pop('id', None)  # Remove ID from data and store it
        if not record_id:
            return False

        existing_record = self.sudo().browse(int(record_id))
        if not existing_record.exists():
            return False

        formated_data = self._from_dict(data)
        existing_record.sudo().write(formated_data)
        return existing_record._to_dict(list_of_fields=list_of_fields)

    @api.model
    def _api_search_all(self, domain=None, limit=100, offset=0, list_of_fields=None):
        domain = domain or []
        Records = self.search(domain, limit=limit, offset=offset)
        return [rec._to_dict(list_of_fields=list_of_fields) for rec in Records]

    @api.model
    def _api_search_one(self, record_id, list_of_fields):
        record = self.browse(int(record_id))
        if not record.exists():
            raise UserError(_("Record not found."))
        return record._to_dict(list_of_fields=list_of_fields)

    @api.model
    def _api_delete_one(self, record_id):
        if not record_id:
            raise UserError(_("Missing Record_id"))

        record = self.sudo().browse(record_id)

        if not record.exists():
            raise UserError(_("Record record not found."))

        record.unlink()

        return {"id": record_id}

    @api.model
    def _get_all_filter_conditions(self, keyword):
        return [('name', 'like', keyword)]

    @api.model
    def _api_filter_with_keywords(self, domain=None, keyword=None, list_of_fields=None):
        if keyword:
            conditions = self._get_all_filter_conditions(keyword)
            filter_domain = ['|'] * (len(conditions) - 1) + conditions
        else:
            filter_domain = domain or []
        records = self.search(filter_domain)
        return [rec._to_dict(list_of_fields=list_of_fields) for rec in records]