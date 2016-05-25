# -*- coding: utf-8 -*-

from openerp import api, models, fields
from openerp.osv import orm
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class mrp_production(models.Model):

    _inherit = "mrp.production"

    @api.multi
    def _compute_performance(self):
        produced_lines = self.move_created_ids2
        produced_qty = 0
        for produced_line in produced_lines:
            produced_qty += produced_line.product_uom_qty
        self.mrp_performance = (produced_qty/self.product_qty)*100

    @api.multi
    def _src_id_default(self):
        try:
            location_id = self.env.user.company_id.location_src_id.id
        except (orm.except_orm, ValueError):
            location_id = False
        return location_id

    @api.multi
    def _tmp_id_default(self):
        try:
            location_id = self.env.user.company_id.location_tmp_id.id
        except (orm.except_orm, ValueError):
            location_id = False
        return location_id
        
    location_tmp_id = fields.Many2one('stock.location', 'Ubicazione materie prime',required=True, readonly=True, states={'draft': [('readonly', False)]},
        help="Location where the system will stock the products required for production")
    distinct_picking_id = fields.Many2one('stock.picking', 'Distinta Prelievo',readonly=True,
        help="Picking linked to mrp production order")
    state = fields.Selection(string='Status', readonly=True, selection=[('draft', 'New'), ('cancel', 'Cancelled'),
                ('confirmed', 'Awaiting Raw Materials'),
                ('ready', 'Ready to Produce'), ('in_production', 'Production Started'), ('scrap_op', 'Scrap Management'), ('done', 'Done')])
    move_lines = fields.One2many('stock.move', 'raw_material_production_id', 'Products to Consume',
            domain=[('state', 'not in', ('done', 'cancel'))],readonly=False)

    mrp_performance = fields.Float(string = 'Resa Produzione', digits=dp.get_precision('Account'), compute='_compute_performance')

    _defaults = {
        'location_src_id': _tmp_id_default,
        'location_tmp_id': _src_id_default
    }    


     #Genero un picking dal mazazzino principale al magazzino temporaneo
    @api.multi
    def action_transfer_to_tmp_stock(self):
        picking_type_id = self.env['stock.picking.type'].search([('name','=','Movimentazione Magazzino Temporaneo')])
        stock_picking_obj = self.env['stock.picking']
        picking_lines = []
        for move_line in self.move_lines:
            picking_line = {
                        'product_id': move_line.product_id.id,
                        'product_uom_qty': move_line.product_uom_qty,
                        'product_uom': move_line.product_uom.id,
                        'location_id': self.location_tmp_id.id,
                        'location_dest_id': self.location_src_id.id,
                        'invoice_state': 'none',
                        'name': move_line.product_id.name,
                   }
            picking_lines.append((0, 0, picking_line))

        vals = {
            'partner_id': self.user_id.company_id.partner_id.id,
            'origin': self.name,
            'move_type': 'direct',
            'invoice_state': 'none',
            'picking_type_id': picking_type_id.id,
            'move_lines': picking_lines,
            'name': 'Distinta Ordine %s' %self.name
        }
        picking_obj = stock_picking_obj.create(vals)
        self.pool.get("stock.picking").action_confirm(self._cr, self._uid, picking_obj.id, self._context)
        self.pool.get("stock.picking").action_assign(self._cr, self._uid, picking_obj.id, self._context)
        self.distinct_picking_id = picking_obj.id
        return {
                "type": "ir.actions.act_window",
                "res_model": "stock.picking",
                "views": [[False, "form"]],
                "res_id":  picking_obj.id,
            }


    def action_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
        super(mrp_production,self).action_produce(cr, uid, production_id, production_qty, production_mode, wiz, context)
        self.signal_workflow(cr, uid, [production_id], 'scrap_on')
        return True

    @api.multi
    def return_stock_mrp(self):
        context =   {'default_mrp_order_id' : self.id,
                     'default_state' : self.state,
                     'product_ids' : 20,
                     }
        return {
                "type": "ir.actions.act_window",
                "res_model": "return.stock.mrp",
                "views": [[False, "form"]],
                "target": "new",
                "context": context
            }
