# -*- coding: utf-8 -*-
from odoo import http, _
import json
import datetime

BARQ_PRODUCT = {
    '1': 'اشتراك برق واتساب لمدة 30 يوم',
}

CLIENT_STATUS = {
    '1': 'APPROVED',
    '2': 'PENDING',
    '3': 'REJECTED',
    '4': 'BLOCKED',
}

PAYMENT_METHOD = {
    '1': 'WALLET',
    '2': 'VISA',
    '3': 'MASTER_CARD',
    '4': 'MADA',
    '5': 'STC_PAY',
}


class BarqInvoice(http.Controller):
    @http.route('/test', type='json', auth="none", csrf=False)
    def add_barq_invoice(self, **kw):
        model = kw.get('model')
        fields = kw.get('fields')
        result = http.request.env[model].sudo().search_read([], fields)
        print('  result  '.center(100, '*'))
        print('-' * 100)
        http.Response.status = '200'
        return result

    # 9b221395b07f32318027e5309d9c6baa4ec50113
    @http.route('/barq/invoice/add', type='json', auth="none", csrf=False)
    def add_barq_invoice(self, **kw):
        method = http.request.httprequest.method
        if method != 'POST':
            return invalid_response('405 Error', f'{method} Method Not Allowed', 405 )

        uid, err_msg = authenticate(kw)
        if not uid or err_msg:
            return invalid_response('APi Key Error', err_msg, 401 )
        
        data = kw.get('data')
        if not data:
            return invalid_response('Data Error', "No data Received!", 400 )

        result = dict()
        for invoice in data:
            print('-' * 100)
            product_name = BARQ_PRODUCT.get(str(invoice['invoiceable_type']), None)
            if not product_name:
                result[invoice['id']] = f"Unknow invoiceable type {invoice['invoiceable_type']}"
                continue
            product = get_or_create_product(uid, product_name, invoice['sub_total'])
            print(product, type(product))
            client = get_or_create_client(uid, invoice['client'])
            print(client, type(client))
            move = create_move(uid, client, product, invoice)
            print(move, type(move))
            print('-' * 100)
            result[invoice['id']] = {
                "state": "success",
                "invoice": model_data(move)
            }
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


def get_or_create_client(uid, invoice_client):
    client_model =  http.request.env['res.partner']
    client = client_model.sudo().search([
        ('name', '=', str(invoice_client['name'])),
        ('email', '=', str(invoice_client['email'])),
        ('phone', '=', str(invoice_client['phone'])),
        ('ref', '=', _("Barq Client")),
        ],
        limit=1
        )
    print('  no client  '.center(100, '/'))
    if not client:
        client = client_model.with_user(uid).create({
                'email': invoice_client['email'],
                'name': invoice_client['name'],
                'phone': invoice_client['phone'],
                'ref': _("Barq Client"),
                'comment': json.dumps({'barq_info': invoice_client}),
            })
    return client


def get_or_create_product(uid, product_name, price):
    product_model = http.request.env['product.product']
    product = product_model.sudo().search([('name', '=', product_name)])
    if not product:
        product = product_model.with_user(uid).create({
            'name': product_name,
            'sale_ok': True,
            'purchase_ok': False,
            'can_be_expensed': False,
            'type': 'service',
            'list_price': price
        })
    return product



def create_move(uid, client, product, invoice_data):
    move = http.request.env['account.move'].with_user(uid).create({
        'partner_id': client.ids[0],
        'company_id': 1,
        'invoice_date': datetime.datetime.strptime(invoice_data['created_at'], "%Y-%m-%d %H:%M:%S").date(),
        'state': 'draft',
        'ref': 'Barq Invoice',
        'invoice_origin': json.dumps({k: invoice_data.get(k, None) for k in invoice_data.keys() if k not in ('client', 'invoiceable')}),
        'invoice_line_ids':
            [(0, 0, {
                'product_id': product.ids[0],
                'quantity': 1,
                'price_unit': invoice_data['sub_total'],
                'discount': invoice_data['discount'],
                'ref': json.dumps({"barq_invoiceable": invoice_data['invoiceable']})
            })]
    })
    move.with_user(uid).write({'state': 'posted', 'payment_state': 'paid'})
    return move


def model_data(obj):
    fields_dict = {}
    for key in obj.fields_get():
        fields_dict[key] = obj[key]
    return fields_dict


class Test(http.Controller):
    @http.route('/test', type='json', auth="none", csrf=False)
    def add_barq_invoice(self, **kw):
        model = kw.get('model')
        fields = kw.get('fields')
        filters = kw.get('filters')
        result = http.request.env[model].sudo().search_read(filters, fields)
        http.Response.status = '200'
        return result


class createinvoice(http.Controller):
    @http.route('/onvoice/create', type='json', auth="none", csrf=False)
    def add_barq_invoice(self, **kw):
        uid = kw.get('uid')
        client_id = kw.get('client_id')
        product_id = kw.get('product_id')
        ref = kw.get('ref')
        update = kw.get('update')
        move = http.request.env['account.move'].with_user(uid).create({
        'partner_id': client_id,
        'company_id': 1,
        'journal_id': 16,
        #'invoice_date': datetime.datetime.strptime(invoice_data['created_at'], "%Y-%m-%d %H:%M:%S").date(),
        'state': 'draft',
        'ref': ref,
        #'invoice_origin': json.dumps({k: invoice_data.get(k, None) for k in invoice_data.keys() if k not in ('client', 'invoiceable')}),
        'invoice_line_ids':
            [http.request.env['account.move.line'].with_user(uid).create({
                'product_id': product_id,
                'quantity': 1,
                'price_unit': 10,
                'discount': 0,
                #'ref': json.dumps({"barq_invoiceable": invoice_data['invoiceable']})
            })]
        })
        if update:
            move.with_user(uid).write({'state': 'posted', 'payment_state': 'paid'})
        http.Response.status = '200'
        return {
                "state": "success",
                "invoice": model_data(move)
            }
