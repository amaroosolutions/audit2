# -*- coding: utf-8 -*-
# (C) 2018 Smile (<http://www.smile.fr>)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import datetime

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def create(self, vals):
        res = super(Base, self).create(vals)
        if not res.display_name:
            res.display_name = res.name_get()[0][1]
        return res

    @api.multi
    def write(self, vals):
        res = super(Base, self).write(vals)
        for rec in self:
            if not rec.display_name or vals.get('name_get'):
                rec.display_name = rec.name_get()[0][1]
                if rec.child_ids:
                    for child in rec.child_ids:
                        child.display_name = child.name_get()[0][1]
        return res

    @api.multi
    def _read_from_database(self, field_names, inherited_field_names=[]):
        super(Base, self)._read_from_database(
            field_names, inherited_field_names)
        # Store history revision in cache
        if self._context.get('history_revision'):
            group_ids = self.env.user.groups_id.ids
            audit_rules = self.env['audit.rule']._check_audit_rule(
                group_ids).get(self._name, {})
            if audit_rules:
                history_date = fields.Datetime.from_string(
                    self._context.get('history_revision'))
                date_operator = audit_rules.get('create') and '>' or '>='
                domain = [
                    ('model', '=', self._name),
                    ('res_id', 'in', self.ids),
                    ('create_date', date_operator, history_date),
                ]
                logs = self.env['audit.log'].sudo().search(
                    domain, order='create_date desc')
                for record in self:
                    vals = {}
                    for log in logs:
                        if log.res_id == record.id:
                            data = safe_eval(log.data or '{}',
                                             {'datetime': datetime})
                            vals.update(data.get('old', {}))
                    if 'message_ids' in self._fields:
                        vals['message_ids'] = record.message_ids.filtered(
                            lambda msg: msg.date <= history_date)
                    record._cache.update(record._convert_to_cache(
                        vals, validate=False))

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(Base, self).fields_get(allfields, attributes)
        if self.env.context.get('history_revision'):
            for field in res:
                res[field]['readonly'] = True
        return res

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        try:
            return super(Base, self).read(fields, load)
        # To contourn a native bug with the last version of Odoo
        except KeyError:
            return super(Base, self).read(fields, load)
