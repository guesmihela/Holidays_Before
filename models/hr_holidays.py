# -*- coding: utf-8 -*-
# ©  2015 iDT LABS (http://www.@idtlabs.sl)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import math
from datetime import timedelta
from datetime import datetime
from werkzeug import url_encode
from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError, ValidationError
from openerp.tools import float_compare
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class HrHolidays(models.Model):
    _inherit = 'hr.holidays'

    is_before = fields.Boolean('Apply Double Validation', related='holiday_status_id.is_before')
    current_date = fields.Datetime(string='current Date',default=datetime.now())
    diff = fields.Float('Before Number of Days', readonly=True, copy=False,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    val_before = fields.Float('nbr days before',related='holiday_status_id.val_before')
    
    def not_allocation(self):
        type = self._context.get('default_type', False)
        if type == 'remove':
            return True
    @api.multi
    def _before_number_of_days(self):
        for holiday in self:
            from_dt = self.date_from
            now_dt = self.current_date
            self.diff = self._get_number_of_days(now_dt, from_dt, self.employee_id.id)
            

    @api.onchange('date_from')
    def _onchange_date_from(self):
        """ If there are no date set for date_to, automatically set one 8 hours later than
            the date_from. Also update the number_of_days.
        """
        date_from = self.date_from
        now_dt = self.current_date

        # Compute and update the number of days before
        
        if (now_dt and date_from) and (now_dt <= date_from):
            self.diff = self._get_number_of_days(now_dt, date_from, self.employee_id.id)
        else:
            self.diff = 0
    @api.multi
    def action_draft(self):
        for holiday in self:
            if not holiday.can_reset:
                raise UserError(_('Only an HR Manager or the concerned employee can reset to draft.'))
            if holiday.state not in ['confirm', 'refuse']:
                raise UserError(_('Leave request state must be "Refused" or "To Approve" in order to reset to Draft.'))
            holiday.write({
                'state': 'draft',
                'manager_id': False,
                'manager_id2': False,
            })
            linked_requests = holiday.mapped('linked_request_ids')
            for linked_request in linked_requests:
                linked_request.action_draft()
            linked_requests.unlink()
        return True

    @api.multi
    def action_confirm(self):
    
        for holiday in self:
            if holiday.is_before and holiday.diff < holiday.val_before and self.not_allocation():
                raise UserError("demande de congé doit etre  avant  : %r" " "  "jours" " "  % holiday.val_before)
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Leave request must be in Draft state ("To Submit") in order to confirm it.'))
        return self.write({'state': 'confirm'})
        
            

    @api.multi
    def action_approve(self):
        # if double_validation: this method is the first approval approval
        # if not double_validation: this method calls action_validate() below
        for holiday in self:
            if holiday.is_before and holiday.diff < holiday.val_before and self.not_allocation():
                raise UserError("demande de congé doit etre  avant : %r" " "  "jours" " "  % holiday.val_before)
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            raise UserError(_('Only an HR Officer or Manager can approve leave requests.'))

        manager = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for holiday in self:
            if holiday.state != 'confirm':
                raise UserError(_('Leave request must be confirmed ("To Approve") in order to approve it.'))

            if holiday.double_validation:
                return holiday.write({'state': 'validate1', 'manager_id': manager.id if manager else False})
            else:
                holiday.action_validate()
    @api.multi
    def action_validate(self):
        self.write({'pending_approver': None})
        for holiday in self:
            if holiday.is_before and holiday.diff < holiday.val_before and self.not_allocation():
                raise UserError("demande de congé doit etre  avant  : %r" " "  "jours" " "  % holiday.val_before)
            self.env['hr.employee.holidays.approbation'].create({'holidays': holiday.id, 'approver': self.env.uid, 'date': fields.Datetime.now()})
        super(HrHolidays, self).action_validate()
    @api.model
    def create(self, values):
        """ Override to avoid automatic logging of creation """
        employee_id = values.get('employee_id', False)
        if self.is_before and self.diff < self.val_before and self.not_allocation():
            raise UserError("demande de congé doit etre  avant  : %r" " "  "jours" " "  % self.val_before)
        if not self._check_state_access_right(values):
            raise AccessError(_('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % values.get('state'))
        if not values.get('department_id'):
            values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})
        holiday = super(HrHolidays, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)).create(values)
        holiday.add_follower(employee_id)
        return holiday
    def not_allocation(self):
        type = self._context.get('default_type', False)
        if type == 'remove':
            return True
    @api.multi
    def write(self, values):
        employee_id = values.get('employee_id', False)
        if self.is_before and self.diff < self.val_before and self.not_allocation():
            raise UserError("demande de congé doit etre  avant  : %r" " "  "jours" " "  % self.val_before)
        if not self._check_state_access_right(values):
            raise AccessError(_('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % values.get('state'))
        result = super(HrHolidays, self).write(values)
        self.add_follower(employee_id)
        return result
    @api.multi
    def _create_resource_leave(self):
        """ This method will create entry in resource calendar leave object at the time of holidays validated """
        for leave in self:
            if leave.is_before and leave.diff < leave.val_before and self.not_allocation():
                raise UserError("demande de congé doit etre  avant  : %r" " "  "jours" " "  % leave.val_before)
            self.env['resource.calendar.leaves'].create({
                'name': leave.name,
                'date_from': leave.date_from,
                'holiday_id': leave.id,
                'date_to': leave.date_to,
                'resource_id': leave.employee_id.resource_id.id,
                'calendar_id': leave.employee_id.resource_id.calendar_id.id
            })
        return True
