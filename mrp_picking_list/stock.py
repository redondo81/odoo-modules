# -*- coding: utf-8 -*-

from openerp import api, models, fields
from openerp.osv import orm

class stock_picking(models.Model):
    _inherit = "stock.picking"

    @api.one
    def do_transfer(self):
        ret = super(stock_picking,self).do_transfer()
        from openerp import workflow
        mrp_order_obj = self.env['mrp.production'].search([("distinct_picking_id","=",self.id)])
        if mrp_order_obj:
            workflow.trg_validate(self._uid, 'mrp.production', mrp_order_obj.id, 'moves_ready', self._cr)
        return ret

class StockMove(models.Model):
    _inherit = 'stock.move'

    returned_qty = fields.Float()