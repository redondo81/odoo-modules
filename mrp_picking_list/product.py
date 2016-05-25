# -*- coding: utf-8 -*-
##############################################################################
#Eliminazione controllo su campo ean13 di product product
##############################################################################
from openerp import api, models, fields,osv
import openerp.addons.decimal_precision as dp
from openerp.exceptions import ValidationError, Warning

class product_template(models.Model):
    _inherit = "product.template"

    _columns = {
         'uom_mrp_coeff' : osv.fields.float('Mrp Unit of Measure -> UO-MRP Coeff', digits_compute= dp.get_precision('Product Unit of Measure'),
                                help='Coefficient to convert default Unit of Measure to Mrp Unit'),
    }
    uom_mrp_id = fields.Many2one('product.uom', 'Mrp Unit of Measure', help="Secondary Unit of Measure used for mrp operation.")


    @api.multi
    def write(self, vals):
        if (
                (vals.get('uom_mrp_id')) and
                ('uom_mrp_coeff' in vals and
                (vals.get('uom_mrp_coeff') == None or vals.get('uom_mrp_coeff') == 0))):
                                                                    raise Warning(('Attenzione: specificare un coefficiente di conversione!'))
        return super(product_template, self).write(vals)


    