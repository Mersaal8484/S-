# -*- coding: utf-8 -*-
# Copyright 2004-2010 OpenERP SA
# Copyright 2014 Angel Moya <angel.moya@domatix.com>
# Copyright 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# Copyright 2016-2017 LasLabs Inc.
# Copyright 2015-2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountAnalyticContract(models.Model):
    _name = 'account.analytic.contract'

    # These fields will not be synced to the contract

    NO_SYNC = [
        'name',
        'partner_id',
        'recurring_invoice_meterline_ids',
        'meter_contractid',
        'meter_id',
        'partner_old_id',
        'meter_chechid',
        'date_Sub_start',
        'meter_first_reading',
        'meter_val',
        'meter_uses',
        'meter_vastype',
        'meter_type',
        'meter_cableid',
        'meter_cablename',
        'meter_cabletype',
        'date_contract',
        'meter_idcard',
        'meter_cardtype',
        'meter_cardprint',
        'date_idcard',
        'meter_current_reading',
        'datetime_lastreading',
        'meter_isinv_ready',
        'recurring_invoice_meterlineinv_ids',
        'meter_lastInvo_reading',
        'meter_canusedunit',
        'meter_usedunit',
        'datetime_lastinvreading',
    ]

    name = fields.Char(
        required=True,
    )
    # Needed for avoiding errors on several inherited behaviors
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner (always False)",
    )
    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string='Pricelist',
    )
    recurring_invoice_line_ids = fields.One2many(
        comodel_name='account.analytic.contract.line',
        inverse_name='analytic_account_id',
        copy=True,
        string='Invoice Lines',
    )
    recurring_invoice_meterline_ids = fields.One2many(
        'account.analytic.contract.meter.line', 'a_meterline_id', string='Meter Lines', copy=True)
    recurring_invoice_meterlineinv_ids = fields.One2many(
        'account.analytic.contract.meter.line.inv', 'a_meterline_id', string='Meter Lines Inv', copy=True)
    recurring_rule_type = fields.Selection(
        [('daily', 'Day(s)'),
         ('weekly', 'Week(s)'),
         ('monthly', 'Month(s)'),
         ('monthlylastday', 'Month(s) last day'),
         ('yearly', 'Year(s)'),
         ],
        default='monthly',
        string='Recurrence',
        help="Specify Interval for automatic invoice generation.",
    )
    recurring_invoicing_type = fields.Selection(
        [('pre-paid', 'Pre-paid'),
         ('post-paid', 'Post-paid'),
         ],
        default='pre-paid',
        string='Invoicing type',
        help="Specify if process date is 'from' or 'to' invoicing date",
    )
    recurring_interval = fields.Integer(
        default=1,
        string='Repeat Every',
        help="Repeat every (Days/Week/Month/Year)",
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        default=lambda s: s._default_journal(),
        domain="[('type', '=', 'sale'),('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.user.company_id,
    )
    meter_contractid = fields.Char(string='الرقم',copy=False,)
    meter_id = fields.Char(string='رقم العداد',copy=False,)
    partner_old_id = fields.Char(string='رقم المشترك',)
    meter_chechid = fields.Char(string='رقم ختم العداد',)
    meter_cableid = fields.Char(string='رقم الخلية',)
    meter_cablename = fields.Char(string='اسم المحول',)
    meter_cabletype = fields.Char(string='نوع المحول',)
    meter_current_reading = fields.Float(string="اخر قراءه  للعداد",default=1.0,compute="_compute_old_reading",store=True,)
    meter_lastInvo_reading = fields.Float(string="اخر قراءه  في اخر فاتوره",default=1.0,compute="_compute_oldinv_reading",store=True,)
    meter_first_reading = fields.Float(string="قراءه العداد بدايه الاشتراك",)
    meter_val = fields.Float(string="معامل الضرب للعداد",default=1.0,)
    meter_usedunit = fields.Float(string="الوحدات المستخدمة من بعد اخر فاتوره",default=1.0,compute="_compute_usedunit_reading",store=True,)
    meter_canusedunit = fields.Float(string="متوسط استخدام الطاقة",default=1.0,compute="_compute_canusedunit_reading",store=True,)
    meter_idcard = fields.Char(string='رقم البطاقة',)
    meter_cardtype = fields.Char(string='نوعها',)
    meter_cardprint = fields.Char(string='مكان الاصدار',)
    meter_uses = fields.Selection(
        [('home', 'منزلي'),
         ('trad', 'تجاري'),
         ('gover', 'حكومي'),
         ('manve', 'صناعي'),
         ('water', 'ضخ ماء'),
         ('other', 'اخرى'),
         ],
        default='trad',
        string='نوع الاستعمال',
    )
    meter_vastype = fields.Selection(
        [('1vas', 'واحد فاز'),
         ('3vas', 'ثلاثة فاز'),
         ('allvas', 'محول تيار'),
         ],
        default='1vas',
        string='طور العداد',
    )
    meter_type = fields.Selection(
        [('meck', 'ميكانيكي'),
         ('elec', 'الكتروني'),
         ('ppay', 'دفع مسبق'),
         ],
        default='meck',
        string='نوع العداد',
    )
    date_Sub_start = fields.Date(
        string='تاريخ التوصيل',
    )
    date_contract = fields.Date(
        string='تاريخ العقد',
    )
    date_idcard = fields.Date(
        string='تاريخ الاصدار',
        default=fields.Date.context_today,
    )
    datetime_lastreading = fields.Datetime(
        string='تاريخ اخر قراءه للعداد',store=True,compute="_compute_lastdate_reading",
    )
    datetime_lastinvreading = fields.Datetime(
        string='تاريخ اخر قراءه في اخر فاتورة',store=True,compute="_compute_lastdateinv_reading",
    )
    meter_isinv_ready = fields.Boolean(string="Inv Ready",default=False,store=True,compute="_compute_inv_ready",)


    @api.multi
    @api.depends('datetime_lastreading','meter_lastInvo_reading','recurring_invoice_meterline_ids.date_readed','recurring_invoice_meterline_ids.isinvoced','recurring_invoice_meterline_ids.mseterLine_current_reading', 'recurring_invoice_meterline_ids', 'meter_first_reading')
    def _compute_old_reading(self):
        for line in self:
            query = '''
            SELECT "mseterLine_current_reading"
            FROM account_analytic_meter_line
            where a_meterline_id= %s 
            ORDER BY id DESC
            LIMIT 1 '''
            if line.id:
                l_id=line.id
            else:
               l_id=self._context.get('active_id') 
            self.env.cr.execute(query, [l_id])
            last_id = self.env.cr.fetchone()
            #last_id = self.env['account.analytic.meter.line'].search([('a_meterline_id','=',line.id)], order='date_readed desc', limit=1)
            if last_id:
                line.meter_current_reading = last_id[0]
            else:
                line.meter_current_reading = line.meter_lastInvo_reading

            
    @api.multi
    @api.depends('datetime_lastinvreading','recurring_invoice_meterline_ids.date_readed', 'recurring_invoice_meterline_ids', 'meter_first_reading','recurring_invoice_meterline_ids.isinvoced')
    def _compute_lastdate_reading(self):
        for line in self:
            query = '''
            SELECT date_readed
            FROM account_analytic_meter_line
            where a_meterline_id= %s 
            ORDER BY id DESC
            LIMIT 1 '''
            if line.id:
                l_id=line.id
            else:
               l_id=self._context.get('active_id') 
            self.env.cr.execute(query, [l_id])
            last_id = self.env.cr.fetchone()
            #last_id = self.env['account.analytic.meter.line'].search([('a_meterline_id','=',line.id)], order='date_readed desc', limit=1)
            if last_id:
                line.datetime_lastreading = last_id[0]
            else:
                line.datetime_lastreading = line.datetime_lastinvreading
     
    @api.multi
    @api.depends('datetime_lastinvreading','recurring_invoice_meterlineinv_ids.date_readed', 'recurring_invoice_meterlineinv_ids', 'meter_first_reading','recurring_invoice_meterlineinv_ids.isinvoced')
    def _compute_lastdateinv_reading(self):
        for line in self:
            query = '''
            SELECT date_readed
            FROM account_analytic_meter_line_inv
            where a_meterline_id= %s 
            ORDER BY id DESC
            LIMIT 1 '''
            if line.id:
                l_id=line.id
            else:
               l_id=self._context.get('active_id') 
            self.env.cr.execute(query, [l_id])
            last_id = self.env.cr.fetchone()
            #last_id = self.env['account.analytic.meter.line.inv'].search([('a_meterline_id','=',line.id),('isinvoced','=',True)], order='date_readed desc', limit=1)
            if last_id:
                line.datetime_lastinvreading = last_id[0]
            else:
                line.datetime_lastinvreading = fields.Datetime.now()           
            
    @api.multi
    @api.depends('datetime_lastinvreading','recurring_invoice_meterlineinv_ids.date_readed','recurring_invoice_meterlineinv_ids.mseterLine_current_reading', 'recurring_invoice_meterlineinv_ids', 'meter_first_reading','recurring_invoice_meterlineinv_ids.isinvoced')
    def _compute_oldinv_reading(self):
        for line in self:
            query = '''
            SELECT "mseterLine_current_reading"
            FROM account_analytic_meter_line_inv
            where a_meterline_id= %s 
            ORDER BY id DESC
            LIMIT 1 '''
            if line.id:
                l_id=line.id
            else:
               l_id=self._context.get('active_id') 
            self.env.cr.execute(query, [l_id])
            last_id = self.env.cr.fetchone()
            #last_id = self.env['account.analytic.meter.line.inv'].search([('a_meterline_id','=',line.id),('isinvoced','=',True)], order='date_readed desc', limit=1)
            if last_id:
                line.meter_lastInvo_reading = last_id[0]
            else:
                if line.meter_first_reading:
                    line.meter_lastInvo_reading = line.meter_first_reading
                else:
                    line.meter_lastInvo_reading = 0

    @api.multi
    @api.depends('meter_current_reading', 'meter_lastInvo_reading', 'meter_val')
    def _compute_usedunit_reading(self):
        for sub in self:
            sub.meter_usedunit = (sub.meter_current_reading-sub.meter_lastInvo_reading)*sub.meter_val
            
    @api.multi
    @api.depends('recurring_invoice_meterline_ids.date_readed','recurring_invoice_meterline_ids.mseterLine_current_reading', 'recurring_invoice_meterline_ids', 'meter_first_reading','recurring_invoice_meterline_ids.isinvoced')
    def _compute_inv_ready(self):
        for line in self:
            query = '''
            SELECT "mseterLine_current_reading"
            FROM account_analytic_meter_line
            where a_meterline_id= %s 
            ORDER BY id DESC
            LIMIT 1 '''
            if line.id:
                l_id=line.id
            else:
               l_id=self._context.get('active_id') 
            self.env.cr.execute(query, [l_id])
            last_id = self.env.cr.fetchone()
            #last_id = self.env['account.analytic.meter.line'].search([('a_meterline_id','=',line.id)], order='date_readed desc', limit=1)
            if last_id:
                line.meter_isinv_ready = True
            else:
                line.meter_isinv_ready = False
     
            
    @api.multi
    @api.depends('meter_current_reading', 'meter_lastInvo_reading', 'meter_val','recurring_invoice_meterlineinv_ids','recurring_invoice_meterlineinv_ids.isinvoced','recurring_invoice_meterlineinv_ids.totalmeter_usedunit')
    def _compute_canusedunit_reading(self):
        for line in self:
            query = '''
            SELECT sum(totalmeter_usedunit)/count(*)
            FROM account_analytic_meter_line_inv
            where a_meterline_id= %s '''
            #if line.id:
                #l_id=line.id
            #else:
               #l_id=self._context.get('active_id') 
            #self.env.cr.execute(query, [l_id])
            #last_id = self.env.cr.fetchone()
            last_id = 1
            line.meter_canusedunit = last_id
            #records = self.env['account.analytic.meter.line.inv'].search([('a_meterline_id','=',line.id),('isinvoced','=',True)])
            #if last_id:
                #line.meter_canusedunit = last_id[0]
            #else:
                #line.meter_canusedunit = 0

    @api.model
    def _default_journal(self):
        company_id = self.env.context.get(
            'company_id', self.env.user.company_id.id)
        domain = [
            ('type', '=', 'sale'),
            ('company_id', '=', company_id)]
        return self.env['account.journal'].search(domain, limit=1)
