# -*- coding: utf-8 -*-

from openerp import api, models, fields
from openerp.osv import orm

class mrp_installer(models.Model):
    _name="mrp.installer"
    _description = "Configurazione modulo mrp idi"

    location_tmp_id = fields.Many2one('stock.location', 'Deafult Magazzino Temporaneo',
                        help="Location where the system will stock the products required for production")

    location_src_id = fields.Many2one('stock.location', 'Deafult Magazzino Materie Prime',
                        help="Location where the system will stock the products required for production")

    @api.multi
    def set_tmp_location(self):
        self.env.user.company_id.location_src_id = self.location_src_id.id
        self.env.user.company_id.location_tmp_id = self.location_tmp_id.id

        return True