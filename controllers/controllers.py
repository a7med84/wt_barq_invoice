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


class BarqInvoiceController(http.Controller):
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
            if http.request.env['account.move'].sudo().search([('ref', '=', f'Barq Invoice {invoice["id"]}')]):
                result[invoice['id']] = "Already added"
                continue

            product_name = BARQ_PRODUCT.get(str(invoice['invoiceable_type']), None)
            if not product_name:
                result[invoice['id']] = f"Unknow invoiceable type {invoice['invoiceable_type']}"
                continue
            product = get_or_create_product(uid, product_name, invoice['sub_total'])

            client = get_or_create_client(uid, invoice['client'])
            
            _date = datetime.datetime.strptime(invoice['created_at'], "%Y-%m-%d %H:%M:%S").date()
            move = create_move(uid, client, product, invoice, _date)
            if move:
                payment_method_id = http.request.env['account.payment.method'].sudo().search([('name', '=', 'Manual'), ('payment_type', '=', 'inbound')]).ids[0]
                journal_id = http.request.env['account.journal'].sudo().search([('name', '=', 'بنك الانماء - ريال')]).ids[0]
                payment_register_model = http.request.env['account.payment.register']
                payment_register_id = payment_register_model.with_user(uid).with_context(active_model='account.move', active_ids= move.ids).create({
                                'journal_id': journal_id,  # 18 inma bank, 19 rajhi bank, 20 cach
                                'payment_method_id': payment_method_id, #1 manuel inbound, 2 manuel outbound, 3 electronic inbound
                                })

                payment_register_id.action_create_payments()
                result[invoice['id']] = "Success"
            else:
                result[invoice['id']] = "Failed"
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

    invoice_client['status'] = CLIENT_STATUS.get(str(invoice_client['status']), "Unknown")
    if not client:
        account_model = http.request.env['account.account']
        receivable_id = account_model.with_user(uid).search([('name', '=', 'العملاء')], limit=1).ids[0]
        payable_id = account_model.with_user(uid).search([('name', '=', 'متنوعون ')], limit=1).ids[0]
        client = client_model.with_user(uid).create({
                'email': invoice_client['email'],
                'name': invoice_client['name'],
                'phone': invoice_client['phone'],
                'property_account_receivable_id': receivable_id,
                'property_account_payable_id': payable_id,
                'ref': _("Barq Client"),
                'comment': json.dumps({k: invoice_client.get(k, None) for k in invoice_client.keys() if k not in ('key', 'secret')}),
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



def create_move(uid, client, product, invoice_data, _date):
    company_id = http.request.env['res.users'].browse([uid]).company_id
    journal_id = http.request.env['account.journal'].with_user(uid).search([('name', '=', 'فواتير العملاء')], limit=1).ids[0]
    payment_term_id = http.request.env['account.payment.term'].with_user(uid).search([('name', '=', 'Immediate Payment')], limit=1).ids[0]
    move = http.request.env['account.move'].with_user(uid).with_context(check_move_validity= False).create({
        'move_type': "out_invoice",
        'partner_id': client.ids[0],
        'company_id': company_id,
        'journal_id': journal_id,
        'invoice_date': _date,
        'l10n_sa_delivery_date': _date,
        'state': 'draft',
        'invoice_payment_term_id': payment_term_id,
        'ref': f'Barq Invoice {invoice_data["id"]}',
        'activity_summary': json.dumps({k: invoice_data.get(k, None) for k in invoice_data.keys() if k not in ('client')}),
        'invoice_line_ids':
            [(0, 0, {
                'product_id': product.ids[0],
                'quantity': 1,
                'price_unit': invoice_data['sub_total'],
                'discount': invoice_data['discount'],  
            })]
    })
    move.with_user(uid).write({'state': 'posted'})
    return move
