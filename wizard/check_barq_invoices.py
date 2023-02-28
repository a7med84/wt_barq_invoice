# -*- coding: utf-8 -*-

from odoo import fields, models, _
import datetime
from ..utils.barqutils import add_invoices, check_invoices, MIN_DATE



class BarqCheckWizard(models.TransientModel):
    _name = "barq.check.wizard"
    _description = "Check Barq Invoices"

    date = fields.Date(string="Date")

    help = fields.Char(readonly=True,default=_(
         'Select a date between ') + 
         datetime.datetime.strftime(MIN_DATE, '%Y/%m/%d') + 
         _(' and today or leave blank to check all')
         )
        
    def action_check_invoices(self):
        data = self.read(['date'])[0]
        date = data['date']
        if date:
            date = min(max([data['date'], MIN_DATE]), fields.Date.today())
        
        invoices = check_invoices(date)
        if invoices:
            result, barq_call = add_invoices(self, invoices, 'manuel_check', None)
        elif isinstance(invoices, Exception):
            barq_call = self.env['barq.call'].sudo().create({
                'call_type': 'manuel_check',
                'barq_data': 'None',
                'result': f'Error: {str(invoices)}'
            })
        else:
            barq_call = self.env['barq.call'].sudo().create({
                'call_type': 'manuel_check',
                'barq_data': 'None',
                'result': 'Error: No data Received!'
            })

        action = self.env.ref('wt_barq_invoice.wt_barq_call_action_window').read()[0]
        action.update({
            'domain': [('id', 'in', barq_call.ids)],
        })
        return action
    