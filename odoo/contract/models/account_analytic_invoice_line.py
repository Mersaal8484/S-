# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class AccountAnalyticInvoiceLine(models.Model):
    _name = 'account.analytic.invoice.line'
    _inherit = 'account.analytic.contract.line'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        required=True,
        ondelete='cascade',
    )

class AccountAnalyticMeterLineInv(models.Model):
    _name = "account.analytic.meter.line.inv"
    _description = "Account Analytic Meter Line Inv"

    a_meterline_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account',required=True,ondelete='restrict', domain="[('recurring_invoices', '=', True)]",)
    name = fields.Text(
        string='Description',
        required=True,
    )
    mseterLine_current_reading = fields.Float(string="القراءه الحالية",required=True,default=1.0,)
    mseterLine_old_reading = fields.Float(string="القراءه السابقة",default=1.0,required=True,)
    isinvoced = fields.Boolean(default=False,required=True,)
    totalmeter_usedunit = fields.Float(required=True,string="اجمالي الوحدات المستخدمة",default=1.0,)
    date_readed = fields.Datetime(
        string='تاريخ القراءه',
        required=True,
        default=fields.Datetime.now,
    )
    image = fields.Binary(string="Image")
    inv_refrid = fields.Char(string='المرجع',)
    
    @api.constrains('mseterLine_current_reading','mseterLine_old_reading')
    def _check_mseterLine_current_reading(self):
        for line in self:
            if line.mseterLine_current_reading < line.mseterLine_old_reading:
                raise ValidationError(
                    _(u"القراءه الحاليه يجب ان تكون اكبر من القراءه السابقه!"))

    @api.multi
    @api.onchange('a_meterline_id')
    def _onchange_a_meterline_id(self):
        vals = {}
        if self.a_meterline_id:
            contract = self.a_meterline_id
            partner = contract.partner_id
            name =  unicode(u'رقم المشترك:' +contract.name) + '\n' +  unicode(u'رقم العداد:' +contract.meter_id)
            self.name = name
            self.mseterLine_current_reading = contract.meter_current_reading
            self.mseterLine_old_reading = contract.meter_current_reading
            self.update({'mseterLine_old_reading': contract.meter_current_reading,})
            
            
class AccountAnalyticMeterLine(models.Model):
    _name = "account.analytic.meter.line"
    _description = "Account Analytic Meter Line"

    a_meterline_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account',required=True,ondelete='cascade', domain="[('recurring_invoices', '=', True)]",)
    name = fields.Text(
        string='Description',
        required=True,
    )
    mseterLine_current_reading = fields.Float(string="القراءه الحالية",required=True,default=1.0,)
    mseterLine_old_reading = fields.Float(string="القراءه السابقة",default=1.0,required=True,)
    isinvoced = fields.Boolean(default=False,required=True,)
    totalmeter_usedunit = fields.Float(required=True,string="اجمالي الوحدات المستخدمة",default=1.0,)
    date_readed = fields.Datetime(
        string='تاريخ القراءه',
        required=True,
        default=fields.Datetime.now,
    )
    image = fields.Binary(string="Image")
    inv_refrid = fields.Char(string='المرجع',)
    
    @api.constrains('mseterLine_current_reading','mseterLine_old_reading')
    def _check_mseterLine_current_reading(self):
        for line in self:
            if line.mseterLine_current_reading < line.mseterLine_old_reading:
                raise ValidationError(
                    _(u"القراءه الحاليه يجب ان تكون اكبر من القراءه السابقه!"))

    @api.multi
    @api.onchange('a_meterline_id')
    def _onchange_a_meterline_id(self):
        vals = {}
        if self.a_meterline_id:
            contract = self.a_meterline_id
            partner = contract.partner_id
            name =  unicode(u'رقم المشترك:' +contract.name) + '\n' +  unicode(u'رقم العداد:' +contract.meter_id)
            self.name = name
            self.mseterLine_current_reading = contract.meter_current_reading
            self.mseterLine_old_reading = contract.meter_current_reading
            self.update({'mseterLine_old_reading': contract.meter_current_reading,})
            
        
class AccountAnalyticContractMeterLine(models.Model):
    _name = 'account.analytic.contract.meter.line'
    _inherit = 'account.analytic.meter.line'

    a_meterline_id = fields.Many2one(
        'account.analytic.contract',
        string='Analytic contract Account',
        required=True,
        ondelete='cascade',
    )
    
class AccountAnalyticContractMeterLine(models.Model):
    _name = 'account.analytic.contract.meter.line.inv'
    _inherit = 'account.analytic.meter.line.inv'

    a_meterline_id = fields.Many2one(
        'account.analytic.contract',
        string='Analytic contract Account',
        required=True,
        ondelete='cascade',
    )
