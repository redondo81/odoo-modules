# -*- coding: utf-8 -*-

from openerp import api, models, fields
from openerp.osv import orm

class res_company(models.Model):
    _inherit = "res.company"

    location_tmp_id = fields.Many2one('stock.location', 'Ubicazione temporanea',
        help="Location where the system will temporany stock the products required for production")

    location_src_id = fields.Many2one('stock.location', 'Ubicazione materie prime',
        help="Location where the system will stock the products required for production")
