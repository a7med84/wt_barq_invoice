# -*- coding: utf-8 -*-

from odoo import fields, models, _
import json
import requests
from ..utils.barqutils import get_headers


BARQ_BASE_URL = "https://api.barq.wide-techno.com/api/crm/clients/"


class BarqCheckWizard(models.TransientModel):
    _name = "barq.clients.wizard"
    _description = "Update Barq Cliemts"

    client = fields.Many2one(comodel_name='res.partner', ondelete='restrict', domain=[('ref', 'ilike', 'Barq Client')])    

    def action_update_clients(self):
        data = self.read(['client'])[0]
        clients = data['client']  
        client_model = self.env['res.partner']
        clients = client_model.browse([clients[0]]) if clients else client_model.search([('ref', 'ilike', 'Barq Client')])

        result = dict()
        all_data = dict()
        for client in clients:
            try:
                client_barq_id = client.ref.split('_')[-1]
            except Exception as e:
                result[client.id ] = {
                    'name': client.name,
                    'barq_id': "Not Found",
                    'result': "Error: " + str(e)
                }
            if client_barq_id:
                url = BARQ_BASE_URL + client_barq_id
                try:
                    resp = requests.get(url, headers=get_headers())
                    data = resp.json().get('data', '')
                    
                except Exception as e:
                    result[client.id ] = {
                    'name': client.name,
                    'barq_id': client_barq_id,
                    'result': "Error: " + str(e)
                    }
                    continue
                if data:
                    # remove client senstive data so it wont be saved
                    data = {k: data.get(k, None) for k in data.keys() if k not in ('key', 'secret')}
                    all_data[client_barq_id] = data
                    client_params = {
                    'email': data['email'],
                    'name': data['name'],
                    'phone': data['phone'],
                    'vat': str(data.get('tax_number', '')),
                    'comment': json.dumps({k: data.get(k, None) for k in data.keys() if k not in ('key', 'secret')}, indent=4),
                    'lang': 'ar_001'
                    }
                    client.write(client_params)
                    result[client.id ] = {
                            'name': client.name,
                            'barq_id': client_barq_id,
                            'result': "Updated"
                        }
                else:
                    result[client.id ] = {
                            'name': client.name,
                            'barq_id': client_barq_id,
                            'result': "Error : No data"
                        }
        barq_call = self.env['barq.call'].sudo().create({
        'call_type': 'vat_manuel',
        'barq_data': json.dumps(all_data, indent=4),
        'result': json.dumps(result, indent=4)
        })
        action = self.env.ref('wt_barq_invoice.wt_barq_call_action_window').read()[0]
        action.update({
            'domain': [('id', 'in', barq_call.ids)],
        })
        return action
