# -*- coding: utf-8 -*-
from openerp import models, fields, api, osv
import logging
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import ValidationError, Warning
from datetime import datetime
from openerp import workflow
import operator
import itertools

_logger = logging.getLogger(__name__)

class return_stock_lines(models.TransientModel):
    _name = 'return.stock.lines'

    def get_product_uom_id(self):

        return

    product_id = fields.Many2one('product.product', 'Product')
    return_stock_mrp_id = fields.Many2one('return.stock.mrp')
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure')

    _columns = {
        'product_qty' : osv.fields.float(readonly=True, digits_compute=dp.get_precision('Product Unit of Measure')),
        'return_product_qty' : osv.fields.float(digits_compute=dp.get_precision('Product Unit of Measure')),
        'package_id': osv.fields.many2one('stock.quant.package', 'Source Package'),
        'result_package_id': osv.fields.many2one('stock.quant.package', 'Destination Package'),
        'lot_id': osv.fields.many2one('stock.production.lot', 'Lot/Serial Number'),
    }

    @api.onchange('product_id')
    def get_domain_product_id(self):
        product_ids = []
        mrp_move_lines = self.return_stock_mrp_id.mrp_order_id.move_lines
        for mrp_move_line in mrp_move_lines:
            product_ids.append(mrp_move_line.product_id.id)
        self.product_uom_id = self.product_id.uom_id if self.product_id else None
        return {
                    'domain': {'product_id':[('id','in',product_ids)],
                                },
                }

    '''
    @api.onchange('return_product_qty')
    def check_return_product_qty(self):
        t_group_by_product = {}

        for return_line in self.return_lines:
            if return_line.product_id.id not in t_group_by_product:
                t_value = {return_line.product_id.id: return_line.return_product_qty}
                t_group_by_product.update(t_value)
            else:
                old_qty = t_group_by_product.get(return_line.product_id.id)
                t_value = {return_line.product_id.id: return_line.return_product_qty + old_qty}
                t_group_by_product.update(t_value)

        if self.return_product_qty > t_group_by_product[self.product_id]:
            raise Warning(_('Attenzione: quantità da restituire maggiore di quella presente.'))
    '''


class return_stock_mrp(models.TransientModel):

    _name = 'return.stock.mrp'

    def getMrpOrderLines(self):
        mrp_production_obj = self.env['mrp.production'].browse(self._context.get('active_id'))
        #raggruppo le quants relative alla distinta di prelievo per prodotto, lotto e pacco
        sql = ('''  SELECT
                        stock_picking.id as return_stock_mrp_id,
                        stock_quant.product_id as product_id,
                        stock_quant.lot_id as lot_id,
                        stock_quant.package_id as package_id,
                        stock_quant.package_id as result_package_id,
                        product_template.uom_id as product_uom_id,
                        sum(stock_quant.qty) as product_qty
                    FROM
                        stock_picking
                    INNER JOIN stock_move ON stock_move.picking_id = stock_picking.id
                    INNER JOIN stock_quant_move_rel ON stock_quant_move_rel.move_id = stock_move.id
                    INNER JOIN stock_quant ON stock_quant.id = stock_quant_move_rel.quant_id
                    INNER JOIN product_product ON stock_quant.product_id = product_product.id
                    INNER JOIN product_template ON product_template.id = product_product.product_tmpl_id
                    WHERE
                        stock_picking.id = %s
                        AND stock_quant.location_id = %s
                    GROUP BY
                        stock_quant.product_id,
                        stock_quant.lot_id,
                        stock_quant.package_id,
                        product_template.uom_id,
                        stock_picking.id
                    ORDER BY
                        stock_quant.product_id,
                        stock_quant.lot_id,
                        stock_quant.package_id
                        ''')
        self.env.cr.execute(sql, (mrp_production_obj.distinct_picking_id.id,mrp_production_obj.location_src_id.id))
        queryResult = self.env.cr.dictfetchall()

        return queryResult

    mrp_order_id = fields.Many2one('mrp.production', readonly=True)
    state = fields.Char(readonly=True)
    location_return_id = fields.Many2one('stock.location', 'Returning Products Location', readonly=True,)
    return_lines = fields.One2many('return.stock.lines','return_stock_mrp_id', default = getMrpOrderLines)

    @api.one
    def action_return(self):
        '''Gestire il raggruppamento delle varie linee per prodotto per calcolare il reso e lo scarto'''
        t_group_by_product = {}

        for return_line in self.return_lines:
            if return_line.product_id.id not in t_group_by_product:
                t_value = {return_line.product_id.id: return_line.return_product_qty}
                t_group_by_product.update(t_value)
            else:
                old_qty = t_group_by_product.get(return_line.product_id.id)
                t_value = {return_line.product_id.id: return_line.return_product_qty + old_qty}
                t_group_by_product.update(t_value)

        mrp_production_obj = self.env['mrp.production'].browse(self._context.get('active_id'))
        stock_picking_type_id= self.env['stock.picking.type'].search([('name','=','Movimentazione Magazzino Temporaneo Rientro')]).id
        location_obj = self.env['stock.location']
        scrap_location_id = location_obj.search([('scrap_location','=',True)])
        product_return_moves = [] #per stock_move

        #assegnazione pacchi e lotti per il wizard di trasferimento picking
        items_value = []
        for return_line in self.return_lines:
            if (return_line.return_product_qty > 0):
                product_return_move = {
                    'product_id': return_line.product_id.id,
                    'product_uom_qty': return_line.return_product_qty / return_line.product_id.uom_mrp_coeff if return_line.product_id.uom_mrp_id else return_line.return_product_qty,
                    'product_uom': return_line.product_id.uom_id.id,
                    'location_id': mrp_production_obj.location_src_id.id,
                    'location_dest_id': mrp_production_obj.location_tmp_id.id,
                    'name': return_line.product_id.name,
                }

                if product_return_move.get('product_uom_qty') > 0:
                    product_return_moves.append((0, 0, product_return_move))

                    lot_id = return_line.lot_id
                    package_id = return_line.package_id.id
                    result_package_id = return_line.result_package_id.id

                    # Per ogni riga di item_ids devo aggiornare il lotto
                    items_value.append((0, 0, { 'product_id': return_line.product_id.id,
                                                'product_uom_id': return_line.product_id.uom_id.id,
                                                'lot_id': lot_id.id,
                                                'package_id': package_id,
                                                'result_package_id': result_package_id,
                                                'sourceloc_id': mrp_production_obj.location_src_id.id,
                                                'destinationloc_id': mrp_production_obj.location_tmp_id.id,
                                                'quantity': return_line.return_product_qty / return_line.product_id.uom_mrp_coeff if return_line.product_id.uom_mrp_id else return_line.return_product_qty,
                                            }
                                        ))

            #per ogni linea genero un movimento di scarto
            if return_line.product_qty - return_line.return_product_qty > 0:
                product_scrap_move = {
                    'product_id': return_line.product_id.id,
                    'product_uom_qty': (return_line.product_qty - return_line.return_product_qty)/return_line.product_id.uom_mrp_coeff if return_line.product_id.uom_mrp_id else return_line.product_qty - return_line.return_product_qty,
                    'product_uom': return_line.product_id.uom_id.id,
                    'location_id': mrp_production_obj.location_src_id.id,
                    'location_dest_id': scrap_location_id.id,
                    'name': return_line.product_id.name,
                }
                if product_scrap_move.get('product_uom_qty') > 0:
                    product_return_moves.append((0, 0, product_scrap_move))

                    lot_id = return_line.lot_id
                    package_id = return_line.package_id.id
                    result_package_id = return_line.result_package_id.id
                    # Per ogni riga di item_ids devo aggiornare il lotto
                    items_value.append((0, 0, { 'product_id': return_line.product_id.id,
                                                'product_uom_id': return_line.product_id.uom_id.id,
                                                'lot_id': lot_id.id,
                                                'package_id': package_id,
                                                'result_package_id': result_package_id,
                                                'sourceloc_id': mrp_production_obj.location_src_id.id,
                                                'destinationloc_id': scrap_location_id.id,
                                                'quantity': (return_line.product_qty - return_line.return_product_qty)/return_line.product_id.uom_mrp_coeff if return_line.product_id.uom_mrp_id else return_line.product_qty - return_line.return_product_qty,
                                               }
                                        ))
        vals_return = {
            'partner_id': mrp_production_obj.user_id.company_id.partner_id.id,
            'origin': mrp_production_obj.distinct_picking_id.name,
            'move_type': 'direct',
            'invoice_state': 'none',
            'picking_type_id': stock_picking_type_id,
            'move_lines': product_return_moves,
            'state': 'draft',
            'origin_picking_id': mrp_production_obj.distinct_picking_id.id,
            'origin_picking_id'
            'date': mrp_production_obj.distinct_picking_id.date
        }

        #genero un picking per il ritorno della merce in magazzino
        back_picking_obj = self.env['stock.picking'].create(vals_return)

        self.pool.get('stock.picking').action_confirm(self._cr, self._uid, back_picking_obj.id, self._context)
        self.pool.get('stock.picking').force_assign(self._cr, self._uid, back_picking_obj.id, self._context)
        stock_transfer_details_obj = self.pool.get('stock.picking').do_enter_transfer_details(self._cr, self._uid, [back_picking_obj.id], self._context)
        stock_transfer_id = stock_transfer_details_obj['res_id']
        stock_transfer_details = self.pool.get('stock.transfer_details').browse(
                                                                self._cr, self._uid, stock_transfer_id, self._context)

        #Elimino i vecchi valori del transfer
        for item in stock_transfer_details.item_ids:
            items_value.append((2, item.id))

        self.pool.get('stock.transfer_details').write(self._cr, self._uid, stock_transfer_details.id, {'item_ids':items_value})

        stock_transfer_details.do_detailed_transfer()
        mrp_production_obj.state = 'done'
        mrp_production_obj.signal_workflow('done')
        return True
