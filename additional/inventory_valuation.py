# inventory_valuation.py - محاسبه ارزش موجودی انبار با روش‌های مختلف

from database import get_db
from collections import deque


class InventoryValuation:
    """محاسبه ارزش موجودی انبار با روش‌های FIFO، LIFO، میانگین موزون و ساده"""
    
    @staticmethod
    def get_in_transactions(product_id):
        """دریافت همه تراکنش‌های ورودی کالا به ترتیب تاریخ"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, date, quantity, unit_price, total_price, ref_no, description
                FROM stock_transactions 
                WHERE product_id = ? AND type = 'in'
                ORDER BY date ASC, id ASC
            ''', [product_id])
            return c.fetchall()
    
    @staticmethod
    def get_out_transactions(product_id):
        """دریافت همه تراکنش‌های خروجی کالا به ترتیب تاریخ"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, date, quantity, unit_price, total_price, ref_no, description
                FROM stock_transactions 
                WHERE product_id = ? AND type = 'out'
                ORDER BY date ASC, id ASC
            ''', [product_id])
            return c.fetchall()
    
    @staticmethod
    def calculate_fifo(product_id, current_stock):
        """محاسبه ارزش موجودی به روش FIFO (First In, First Out)"""
        in_transactions = InventoryValuation.get_in_transactions(product_id)
        if not in_transactions:
            return 0
        
        queue = deque()
        for t in in_transactions:
            queue.append({
                'quantity': t['quantity'],
                'price': t['unit_price'],
                'date': t['date'],
                'id': t['id']
            })
        
        out_total = 0
        out_transactions = InventoryValuation.get_out_transactions(product_id)
        for out in out_transactions:
            out_total += out['quantity']
        
        remaining_out = out_total
        while queue and remaining_out > 0:
            first_item = queue[0]
            if first_item['quantity'] <= remaining_out:
                remaining_out -= first_item['quantity']
                queue.popleft()
            else:
                queue[0]['quantity'] -= remaining_out
                remaining_out = 0
        
        remaining_stock = current_stock
        total_value = 0
        
        for item in queue:
            if remaining_stock <= 0:
                break
            qty = min(item['quantity'], remaining_stock)
            total_value += qty * item['price']
            remaining_stock -= qty
        
        return total_value
    
    @staticmethod
    def calculate_lifo(product_id, current_stock):
        """محاسبه ارزش موجودی به روش LIFO (Last In, First Out)"""
        in_transactions = InventoryValuation.get_in_transactions(product_id)
        if not in_transactions:
            return 0
        
        stack = []
        for t in in_transactions:
            stack.append({
                'quantity': t['quantity'],
                'price': t['unit_price'],
                'date': t['date'],
                'id': t['id']
            })
        
        out_total = 0
        out_transactions = InventoryValuation.get_out_transactions(product_id)
        for out in out_transactions:
            out_total += out['quantity']
        
        remaining_out = out_total
        while stack and remaining_out > 0:
            last_item = stack[-1]
            if last_item['quantity'] <= remaining_out:
                remaining_out -= last_item['quantity']
                stack.pop()
            else:
                stack[-1]['quantity'] -= remaining_out
                remaining_out = 0
        
        remaining_stock = current_stock
        total_value = 0
        
        for item in reversed(stack):
            if remaining_stock <= 0:
                break
            qty = min(item['quantity'], remaining_stock)
            total_value += qty * item['price']
            remaining_stock -= qty
        
        return total_value
    
    @staticmethod
    def calculate_weighted_average(product_id, current_stock):
        """محاسبه ارزش موجودی به روش میانگین موزون"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT 
                    COALESCE(SUM(quantity * unit_price), 0) as total_cost,
                    COALESCE(SUM(quantity), 0) as total_quantity
                FROM stock_transactions 
                WHERE product_id = ? AND type = 'in'
            ''', [product_id])
            row = c.fetchone()
            
            if not row or row['total_quantity'] == 0:
                return 0
            
            avg_price = row['total_cost'] / row['total_quantity']
            return current_stock * avg_price
    
    @staticmethod
    def calculate_simple(product_id, current_stock):
        """محاسبه ارزش موجودی به روش ساده (قیمت خرید فعلی)"""
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT purchase_price FROM products WHERE id = ?', [product_id])
            product = c.fetchone()
            return current_stock * (product['purchase_price'] if product else 0)
    
    @staticmethod
    def get_inventory_value(product_id, current_stock, method='simple'):
        """دریافت ارزش موجودی بر اساس روش انتخاب شده"""
        methods = {
            'fifo': InventoryValuation.calculate_fifo,
            'lifo': InventoryValuation.calculate_lifo,
            'weighted_average': InventoryValuation.calculate_weighted_average,
            'simple': InventoryValuation.calculate_simple
        }
        calc_func = methods.get(method, InventoryValuation.calculate_simple)
        return calc_func(product_id, current_stock)