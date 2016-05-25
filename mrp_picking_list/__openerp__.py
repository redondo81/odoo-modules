# -*- encoding: utf-8 -*-

{
    'name': 'Distinta Prelievo MRP',
    'version': '0.1',
    'author': 'Isa s.r.l.',
    'description': """
Aggiunta distinta prelivelo Ordini MRP
================================================

    """,
    'license': 'AGPL-3',
    'category': 'Manufacturing',
    'website': 'http://www.isa.it/',
    'depends': ['base',
                'mrp',
                ],
    'data': [
            'mrp.xml',
            'res_company_view.xml',
            'mrp_installer_view.xml',
            'data/stock.picking.type.xml',
            'mrp_workflow.xml',
            'wizard/return_stock_mrp.xml',
            'product_view.xml'
             ],
    'installable': True,
    'auto_install': False,
}
