# -*- coding: utf-8 -*-
# © 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api,fields, models
from odoo.osv import osv
from datetime import datetime
from odoo import tools


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    contract_id = fields.Many2one('account.analytic.account',string='Contract')
    previous_invoice_id = fields.Many2one('account.invoice',compute='_previous_invoice_get',store=True)
        
    @api.multi
    @api.depends('date_invoice', 'partner_id', 'date_invoice')
    def _previous_invoice_get(self):
        res = {}
        query = '''
            SELECT id
            FROM account_invoice 
            where state not in ('draft','cancel') and
            partner_id=  %s and date_invoice< %s 
            ORDER BY id DESC
            LIMIT 1 '''
        for invoice in self:
            if invoice.partner_id and invoice.date_invoice:
                self.env.cr.execute(query, [invoice.partner_id.id,invoice.date_invoice])
                openbal = self.env.cr.fetchone()
                if openbal:
                    invoice.previous_invoice_id=openbal[0]
            else:
                invoice.previous_invoice_id=False
                    

    @api.model
    def get_quantity_subscription1(self):
        for line in self:
            if line.previous_invoice_id:
                start_date = datetime.strptime(line.previous_invoice_id.date_invoice, '%Y-%m-%d').date()
            else:
                start_date = datetime.strptime(line.invdatetime_lastreading, '%Y-%m-%d %H:%M:%S').date()
            end_date = datetime.strptime(line.date_invoice, '%Y-%m-%d').date()
            delta = end_date - start_date
            if delta.days <= 10:
                return "1"
            elif delta.days <= 20:
                return "1,2"
            elif delta.days <= 30:
                 return "1,2,3"
            elif delta.days <= 40:
                return "1,2,3,4"
            else:
                return "1,2,3,4,5"
