import logging
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import ValidationError, Warning
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

class HolidaysType(models.Model):
    _inherit = 'hr.holidays.status'

    is_before = fields.Boolean(string="Avant un periode ", default=False)
    val_before = fields.Float(string="Jours")

