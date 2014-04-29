# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website
from openerp.tools.translate import _
 
class IpMyAccount(http.Controller):

    @http.route(['/account/', '/account/<page>'], type='http', auth="public", multilang=True, website=True)
    def account(self, page=None, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        user_obj = pool['res.users']
        invoices_obj = pool['account.invoice']
        sale_obj = pool['sale.order']
        auto_ship_obj = pool['ip.auto_ship']
        delivery_obj = pool['stock.picking.out']
        incoming_obj = pool['stock.picking.in']
        payment_obj = pool['payment.transaction']

        # get customer from logged in user
        user = user_obj.browse(cr, 1, uid)
        partner_id = user.partner_id.id
        
        # if user is public user, redirect to login page
        public_user_id = pool['website'].get_public_user(cr, 1)
        if user.id == public_user_id:
            return request.redirect("/web/login?redirect=/account/") 
        
        # get sales orders
        sale_order_ids = sale_obj.search(cr, uid, [
                ('partner_id.commercial_partner_id', '=', partner_id),
                ('state', 'not in', ['draft', 'cancelled', 'invoice_except', 'shipping_except'])
            ], context=context)
        sale_orders = sale_obj.browse(cr, uid, sale_order_ids, context=context)

        # get invoices
        invoice_ids = invoices_obj.search(cr, uid, [
                ('partner_id.commercial_partner_id', '=', partner_id), 
                ('type', '=', 'out_invoice'), 
                ('state', 'in', ['open', 'paid'])
            ], context=context)
        invoices = invoices_obj.browse(cr, uid, invoice_ids, context=context)

        # get delivery orders
        delivery_ids = delivery_obj.search(cr, uid, [
                ('type', '=', 'out'), 
                ('sale_id', 'in', sale_order_ids), 
                ('state', 'in', ['confirmed', 'assigned', 'done'])
            ], context=context)
        deliveries = delivery_obj.browse(cr, uid, delivery_ids, context=context)

        # get auto ships
        auto_ship_ids = auto_ship_obj.search(cr, uid, [
                ('partner_id', '=', partner_id),
            ], context=context)
        auto_ships = auto_ship_obj.browse(cr, uid, auto_ship_ids)
        
        # get transactions
        transaction_ids = payment_obj.search(cr, uid, [('partner_id', '=', partner_id)])
        transactions = payment_obj.browse(cr, uid, transaction_ids, context=context)
        
        # get returns
        return_ids = incoming_obj.search(cr, uid, [
                ('partner_id', '=', partner_id), 
                ('type', '=', 'in'),
                ('state', '!=', 'draft'),
            ], context=context) 
        returns = incoming_obj.browse(cr, uid, return_ids, context=context)
        
        vals = {
            'page': page,
            'invoices': invoices,
            'sale_orders': sale_orders,
            'deliveries': deliveries,
            'auto_ships': auto_ships,
            'transactions': transactions,
            'returns': returns,
         }

        return request.website.render("ip_web_addons.account", vals)
    
    @http.route(['/account/auto-ship/update/<int:auto_ship_id>'], type='http', auth="public", multilang=True, website=True)
    def update_auto_ship(self, auto_ship_id, interval, end_date, **post):
        """ Update an auto ship's interval and end date """
        assert auto_ship_id and interval and end_date, "All variables are required to be truthy"
        cr, uid, pool = request.cr, request.uid, request.registry
        # TODO: do we need to check permission?
        pool['ip.auto_ship'].write(cr, uid, auto_ship_id, {'interval': interval, 'end_date': end_date})
        return 'Your changes have been saved'
    
    @http.route(['/account/auto-ship/delete/<int:auto_ship_id>'], type='http', auth="public", multilang=True, website=True)
    def delete_auto_ship(self, auto_ship_id, **post):
        """ delete an auto ship """
        assert auto_ship_id and isinstance(auto_ship_id, (int, long)), "Invalid auto ship ID"
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        # TODO: do we need to check permission?
        pool['ip.auto_ship'].unlink(cr, uid, auto_ship_id, context=context)
        return 'true'

    @http.route(['/account/number-remaining/<int:interval>/<end_date>'], type='http', auth="public", multilang=True, website=True)
    def number_remaining(self, interval, end_date, **post):
        """ Return the number of auto shipments remaining based on end_date and interval """
        if not interval or not end_date:
            return ''
        try:
            return str(request.registry['ip.auto_ship']._calculate_number_remaining(float(interval), end_date))
        except:
            return ''
