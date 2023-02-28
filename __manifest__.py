# -*- coding: utf-8 -*-
{
    'name': "Wide Techno Barq Invoices",

    'summary': """
        Wide Techno Barq Invoices""",

    'description': """
        Wide Techno Barq Invoices
    """,

    'author': "Ahmed Addawody",
    'website': "https://wide-techno.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'product'],

    # always loaded
    'data': [
        'security/sequrity.xml',
        'security/ir.model.access.csv',
        'data/cron_action.xml',
        'views/views.xml',
        'views/templates.xml',
        'wizard/check_wizard_views.xml',
        'wizard/update_client_wizard_views.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
