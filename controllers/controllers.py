# -*- coding: utf-8 -*-
from odoo import http, _
import json
from ..utils.barqutils import add_invoices, get_or_create_client


class BarqInvoiceController(http.Controller):
    @http.route('/barq/invoice/add', type='json', auth="none", csrf=False)
    def add_barq_invoice(self, **kw):
        method = http.request.httprequest.method
        if method != 'POST':
            http.request.env['barq.call'].sudo().create({
                'call_type': 'new',
                'barq_data': 'Unknown',
                'result': f'405 Error: {method} Method Not Allowed'
            })
            return invalid_response('405 Error', f'{method} Method Not Allowed', 405 )

        uid, err_msg = authenticate(kw)
        if not uid or err_msg:
            http.request.env['barq.call'].sudo().create({
                'call_type': 'new',
                'barq_data': 'Unknown',
                'result': '401 Error: APi Key Error'
            })
            return invalid_response('APi Key Error', err_msg, 401 )
        
        data = kw.get('data', '')
        if not data:
            http.request.env['barq.call'].sudo().create({
                'call_type': 'new',
                'barq_data': 'None',
                'result': '400 Error: No data Received!'
            })
            return invalid_response('Data Error', "No data Received!", 400 )

        result, barq_call = add_invoices(http.request, data, 'new', uid)
        http.Response.status = '200'
        return {'message': "done", 'result': result}

class BarqClientController(http.Controller):
    @http.route('/barq/client/vat', type='json', auth="none", csrf=False)
    def add_barq_invoice(self, **kw):
        method = http.request.httprequest.method
        if method != 'POST':
            http.request.env['barq.call'].sudo().create({
                'call_type': 'new',
                'barq_data': 'Unknown',
                'result': f'405 Error: {method} Method Not Allowed'
            })
            return invalid_response('405 Error', f'{method} Method Not Allowed', 405 )

        uid, err_msg = authenticate(kw)
        if not uid or err_msg:
            http.request.env['barq.call'].sudo().create({
                'call_type': 'new',
                'barq_data': 'Unknown',
                'result': '401 Error: APi Key Error'
            })
            return invalid_response('APi Key Error', err_msg, 401 )
        
        data = kw.get('data', '')
        
        if not data:
            http.request.env['barq.call'].sudo().create({
                'call_type': 'vat',
                'barq_data': 'None',
                'result': '400 Error: No data Received!'
            })
            return invalid_response('Data Error', "No data Received!", 400 )
        result = dict()
        for x in data:
            client = get_or_create_client(http.request, x, uid)
            result[x['id']] = "Updated"
        http.request.env['barq.call'].sudo().create({
                'call_type': 'vat',
                'barq_data': json.dumps(data, indent=4),
                'result': json.dumps(result, indent=4)
            })
        http.Response.status = '200'
        return {'message': "done", 'result': result}


def authenticate(kw):
        uid = None
        err_msg = 'API Key is missing!'
        api_key = kw.get('api_key')
        if api_key:
            err_msg = None
            uid = http.request.env['res.users.apikeys']._check_credentials(scope='rpc', key=api_key)
            if not uid:
                err_msg = 'API Key is not valid!'
        return uid , err_msg


def invalid_response(type='Error', msg=None, code=401):
    http.Response.status = '403'
    return {"type": type, "message": msg}