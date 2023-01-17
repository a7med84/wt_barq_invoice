# -*- coding: utf-8 -*-
from odoo import http

class BarqInvoice(http.Controller):
    @http.route('/barq/invoice/add', type='json', auth="none", csrf=False)
    def add_barq_invoice(self, **kw):
        method = http.request.httprequest.method
        if method != 'POST':
            return self.invalid_response('405 Error', f'{method} Method Not Allowed', 405 )

        uid, err_msg = self.authenticate(kw)
        if not uid or err_msg:
            return self.invalid_response('APi Key Error', err_msg, 401 )
        
        data = kw.get('data')
        if not data:
            return self.invalid_response('Data Error', "No data Received!", 400 )
     
        return {'message': "done", 'result': [{invoice['id']: 'success'} for invoice in data ]}


    def authenticate(self, kw):
        uid = None
        err_msg = 'API Key is missing!'
        api_key = kw.get('api_key')
        if api_key:
            err_msg = None
            uid = http.request.env['res.users.apikeys']._check_credentials(scope='rpc', key=api_key)
            if not uid:
                err_msg = 'API Key is not valid!'
        return uid , err_msg


    def invalid_response(self, type='Error', msg=None, code=401):
        http.Response.status = '403'
        return {"type": type, "message": msg}


    

