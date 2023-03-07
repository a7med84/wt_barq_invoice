# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import requests
from ..utils.barqutils import *


BARQ_BASE_URL = "https://api.barq.wide-techno.com/api/crm/invoices"

class BarqCall(models.Model):
    _name = 'barq.call'
    _description = 'Wide Techno Barq Invoice External API Calls'
    _order = 'create_date desc'

    call_type = fields.Selection([
        ('new', 'Barq Invoice Notification'), 
        ('vat', 'Barq vat Notification'), 
        ('daily_check', 'Invoices Daily Check'), 
        ('manuel_check', 'Invoices Manuel Check'), 
        ('vat_manuel', 'Vat Manuel Check')
        ], required=True
        )
    barq_data = fields.Text(required=True)
    result = fields.Text(required=True)

    @api.model
    def daily_check(self):
        barq_call_type = 'daily_check'
        invoices = check_invoices(fields.Date.today())
        if invoices:
            add_invoices(self, invoices, barq_call_type, None)
        else:
            self.env['barq.call'].sudo().create({
                'call_type': barq_call_type,
                'barq_data': 'None',
                'result': 'No invoices!'
            })
        
    

    
