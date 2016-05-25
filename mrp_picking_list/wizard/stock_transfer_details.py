# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime

class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    def default_get(self, cr, uid, fields, context=None):
        ret = super(stock_transfer_details,self).default_get(cr, uid, fields, context)
        for item in ret.get('item_ids'):
            item.update(result_package_id=item.get('package_id'))
            #sposto la location dei pacchi legati alla distinta di prelievo
            package_obj = self.pool('stock.quant.package').browse(cr, uid, item.get('package_id'), context)
            self.write(cr, uid, [package_obj], {'location_id':item.get('destinationloc_id'),})
        return ret
