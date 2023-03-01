from odoo import _
import datetime
import json
import requests


MIN_DATE = datetime.date(2023,2,28)
BARQ_BASE_URL = "https://api.barq.wide-techno.com/api/crm/invoices"

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


def add_invoices(obj, data, barq_call_type, uid=None):
    result = dict()
    for invoice in data:
        try:
            _date = datetime.datetime.strptime(invoice['created_at'], "%Y-%m-%d %H:%M:%S").date()
            today = datetime.datetime.now().date()
            if not (MIN_DATE <= _date <= today):
                result[invoice['id']] = {"status": "Failed", "error": f"out of range ({MIN_DATE} - {today})"}
                continue
            
            client = get_or_create_client(obj, invoice['client'], uid)
            if obj.env['account.move'].sudo().search([('ref', '=', f'Barq Invoice {invoice["id"]}')]):
                result[invoice['id']] = {"status": "Already added"}
                continue

            product_name = BARQ_PRODUCT.get(str(invoice['invoiceable_type']), None)
            if not product_name:
                result[invoice['id']] = {"status": "Failed", "error": f"Unknown invoiceable type {invoice['invoiceable_type']}"}
                continue
            product = get_or_create_product(obj, product_name, invoice['sub_total'], uid)
            move = create_move(obj, client, product, invoice, _date, uid)
            if move:
                if move.amount_total_signed:
                    payment_method_id = obj.env['account.payment.method'].sudo().search([('name', '=', 'Manual'), ('payment_type', '=', 'inbound')]).ids[0]
                    journal_id = obj.env['account.journal'].sudo().search([('name', '=', 'بنك الانماء - ريال')]).ids[0]
                    payment_register_model = obj.env['account.payment.register']
                    params = {
                        'journal_id': journal_id,  # 18 inma bank, 19 rajhi bank, 20 cach
                        'payment_method_id': payment_method_id, #1 manuel inbound, 2 manuel outbound, 3 electronic inbound
                        }
                    if uid:
                        payment_register_id = payment_register_model.with_user(uid).with_context(active_model='account.move', active_ids= move.ids).create(params)
                    else:
                        payment_register_id = payment_register_model.with_user(uid).with_context(active_model='account.move', active_ids= move.ids).create(params)
                    payment_register_id.action_create_payments()
                result[invoice['id']] = {"status": "Success"}
            else:
                result[invoice['id']] = {"status": "Failed", "error": "Unknown"}
        except Exception as e:
            result[invoice['id']] = {"status": "Failed", "error": str(e)}
    barq_call = obj.env['barq.call'].sudo().create({
        'call_type': barq_call_type,
        'barq_data': json.dumps(data, indent=4),
        'result': json.dumps(result, indent=4)
    })
    return result, barq_call



def get_or_create_client(obj, invoice_client, uid=None):
    invoice_client['status'] = CLIENT_STATUS.get(str(invoice_client['status']), "Unknown")
    client_params = {
                    'email': invoice_client['email'],
                    'name': invoice_client['name'],
                    'phone': invoice_client['phone'],
                    'vat': str(invoice_client.get('tax_number', '')),
                    'ref': f"Barq Client_{invoice_client['id']}",
                    'comment': json.dumps({k: invoice_client.get(k, None) for k in invoice_client.keys() if k not in ('key', 'secret')}, indent=4),
                    'lang': 'ar_001'
                }
    client_model =  obj.env['res.partner']
    client = client_model.sudo().search([('ref', '=', f"Barq Client_{invoice_client['id']}")], limit=1)
    if client:
        if uid:
            client.with_user(uid).write(client_params)
        else:
            client.write(client_params)
    else:
        account_model = obj.env['account.account']
        client_params['property_account_receivable_id'] = account_model.sudo().search([('name', '=', 'العملاء')], limit=1).ids[0]
        client_params['property_account_payable_id'] = account_model.sudo().search([('name', '=', 'متنوعون ')], limit=1).ids[0]
        if uid:
            client = client_model.with_user(uid).create(client_params)
        else:
            client = client_model.create(client_params)
    return client


def get_or_create_product(obj, product_name, price, uid=None):
    product_model = obj.env['product.product']
    product = product_model.sudo().search([('name', '=', product_name)])
    product_params = {
            'name': product_name,
            'sale_ok': True,
            'purchase_ok': False,
            'can_be_expensed': False,
            'type': 'service',
            'list_price': price
        }
    if not product:
        if uid:
            product = product_model.with_user(uid).create(product_params)
        else:
            product = product_model.create(product_params)
    return product


def create_move(obj, client, product, invoice_data, _date, uid=None):
    journal_id = obj.env['account.journal'].sudo().search([('name', '=', 'فواتير العملاء')], limit=1).ids[0]
    payment_term_id = obj.env['account.payment.term'].sudo().search([('name', '=', 'Immediate Payment')], limit=1).ids[0]
    tax_ids = obj.env['account.tax'].sudo().search([
        ('name', '=', 'ضريبة القيمة المضافة VAT'), 
        ('type_tax_use', '=', 'sale'), 
        ('amount', '=', '15')
        ], limit=1).ids
    
    move_params = {
        'move_type': "out_invoice",
        'partner_id': client.ids[0],
        'journal_id': journal_id,
        'invoice_date': _date,
        'l10n_sa_delivery_date': _date,
        'state': 'draft',
        'invoice_payment_term_id': payment_term_id,
        'ref': f'Barq Invoice {invoice_data["id"]}',
        'activity_summary': json.dumps({k: invoice_data.get(k, None) for k in invoice_data.keys() if k not in ('client')}, indent=4),
        'invoice_line_ids':
            [(0, 0, {
                'product_id': product.ids[0],
                'quantity': 1,
                'price_unit': invoice_data['sub_total'],
                'discount': (float(invoice_data['discount']) / float(invoice_data['sub_total'])) * 100,
                'tax_ids': tax_ids
            })]
    }
    if uid:
        move_params['company_id'] = obj.env['res.users'].browse([uid]).company_id
        move = obj.env['account.move'].with_user(uid).with_context(check_move_validity= False).create(move_params)
        move.with_user(uid).write({'state': 'posted'})
    else:
        move_params['company_id'] = obj.env.user.company_id
        move = obj.env['account.move'].with_context(check_move_validity= False).create(move_params)
        move.write({'state': 'posted'})
    return move
    

def check_invoices(_date=None):
    url = BARQ_BASE_URL + f"?day={_date}" if _date else BARQ_BASE_URL
    try:
        resp = requests.get(url, headers=get_headers())
        result = resp.json()
        data = result.get('data', '')
    except Exception as e:
        data = e
    return data
    


def get_headers():
    return {
        'Client-Id': 'qduBJm9YYAsjnDhzcLK81YNNnn7dL4g7pCLo8PZTHV2o2xyakfow',
        'Client-Secret': 'krK7HLmo0lHVhK85uE056NhZDiGi5qvveS91k4u4Lfm1IURhgSdfKAEU5onXZ8GHq7nMd0xm1JAfGvOtyHyyP',
        }