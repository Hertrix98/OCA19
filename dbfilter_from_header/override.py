
# Migrated and hardened for Odoo 19 compatibility
# © 2013  Therp BV
# © 2014  ACSONE SA/NV
# Copyright 2018 Quartile Limited
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import re

from odoo import http
from odoo.tools import config

# keep original http.db_filter to call it first
db_filter_org = http.db_filter


def db_filter(dbs, host=None):
    """Filter databases using the X-Odoo-DBFilter HTTP header.

    This implementation is defensive: it checks that ``http.request`` and
    ``http.request.httprequest`` exist before attempting to read the header.
    This avoids attribute errors when the module is imported in worker
    processes or during server startup phases where no request is active.
    """
    dbs = db_filter_org(dbs, host)

    # be defensive: http.request may be missing in some contexts
    http_request_obj = getattr(http, 'request', None)
    if not http_request_obj:
        return dbs

    # 'httprequest' attribute holds the Werkzeug request object
    werk_req = getattr(http_request_obj, 'httprequest', None)
    if not werk_req:
        return dbs

    db_filter_hdr = werk_req.environ.get('HTTP_X_ODOO_DBFILTER')
    if db_filter_hdr:
        try:
            dbs = [db for db in dbs if re.match(db_filter_hdr, db)]
        except re.error:
            # if user provides an invalid regex, ignore it (safer than crashing)
            _logger = logging.getLogger(__name__)
            _logger.warning('Invalid regex in X-Odoo-DBFilter header: %r', db_filter_hdr)
    return dbs


# Apply the monkey patch only when running behind a proxy and when the module
# is declared in server_wide_modules (same behavior as original module).
if config.get('proxy_mode') and 'dbfilter_from_header' in config.get('server_wide_modules', []):
    _logger = logging.getLogger(__name__)
    _logger.info('monkey patching http.db_filter (dbfilter_from_header)')
    http.db_filter = db_filter
