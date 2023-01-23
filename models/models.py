# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class BarqInvoice(models.Model):
    _name = 'wt.barq.invoice'
    _description = 'Wide Techno Barq Invoice External API'

    barq_id = fields.Integer()
    client_id = fields.Integer()
    invoiceable_id = fields.Integer()
    invoiceable_type = fields.Char()
    sub_total = fields.Float()
    discount = fields.Float()
    total = fields.Float()
    payment_method = fields.Char(size=20)
    invoice_date = fields.Date(string='Invoice Date')

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        )

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        )
    

    _sql_constraints = [
                     ('barq_id_unique', 
                      'unique(barq_id)',
                      _("Duplicate values not allowed for this field!"))
                    ]
    