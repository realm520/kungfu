import time
import concurrent.futures
import pywingchun
# import pyyjj
import json
# import kungfu.wingchun.utils as wc_utils
from .api.client import Client
from dotted_dict import DottedDict
from collections import namedtuple

OrderRecord = namedtuple("OrderRecord", ["source", "dest", "order"])
OrderStatusMapping = {
    'NEW': 1,
    'PARTIALLY_FILLED': 7,
    'FILLED': 5,
    'CANCELED': 3,
    'REJECTED': 4,
    'EXPIRED': 4
}

class TraderGate(pywingchun.Trader):
    def __init__(self, low_latency, locator, account_id, json_config):
        pywingchun.Trader.__init__(self, low_latency, locator, "sim", account_id)
        config = json.loads(json_config)
        self.ctx = DottedDict()
        self.ctx.orders = {}
        self.markets_info = {}
        self.api = Client(config['api_key'], config['secret_key'])
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            order_updater = executor.submit(self.update_order_status)

    def on_start(self):
        markets = self.api.get_all_pairs_info()
        for m in markets['result']['symbols']:
            if m['symbol'] not in self.markets_info:
                self.markets_info[m['symbol']] = m
        pywingchun.Trader.on_start(self)

    def insert_order(self, event):
        order_input = event.data
        order = pywingchun.utils.order_from_input(order_input)
        if not self._check_volume(self.markets_info[order.instrument_id], order_input.volume):
            order.status = pywingchun.constants.OrderStatus.Error
        else:
            order.status = pywingchun.constants.OrderStatus.Pending
        # self.get_writer(event.source).write_data(0, order)
        ret = self.api.send_order(
            symbol=order.instrument_id, price=order.limit_price, 
            quantity=order.volume, side='BUY' if order.side == 0 else 'SELL', 
            order_type='LIMIT')
        if ret['rc'] == 0:
            order.order_id = ret['result']['orderId']
            self.ctx.orders[order.order_id] = OrderRecord(source=event.source, dest=event.dest, order=order)
            return True
        else:
            return False
        # if order.volume_traded > 0:
        #     trade = pywingchun.Trade()
        #     trade.account_id = self.io_device.home.name
        #     trade.order_id = order.order_id
        #     trade.volume = order.volume_traded
        #     trade.price = order.limit_price
        #     trade.instrument_id = order.instrument_id
        #     trade.exchange_id = order.exchange_id
        #     trade.trade_id = self.get_writer(event.source).current_frame_uid()
        #     self.get_writer(event.source).write_data(0, trade)
        # if order.active:

    def cancel_order(self, event):
        order_action = event.data
        ret = self.api.cancel_order(order_action.order_id)
        if ret['rc'] == 0:
            record = self.ctx.orders[order_action.order_id]
            order = record.order
            order.status = pywingchun.constants.OrderStatus.Pending
            self.get_writer(event.source).write_data(0, order)
            return True
        else:
            return False

    def update_order_status(self):
        while not self.stop:
            time.sleep(1)
            # deleted_ids = []
            for oid, record in self.ctx.orders.items():
                ret = self.api.get_order_by_id(order_id=oid)
                if ret['rc'] == 0:
                    if record.order.status != OrderStatusMapping[ret['result']['state']]:
                        record.order.status = OrderStatusMapping[ret['result']['state']]
                        self.get_writer(record.source).write_data(0, record.order)
                if record.order.status not in [1, 7]:
                    del self.ctx.orders[oid]

    def _check_volume(self, market, volume: float):
        market_info = self.markets_info[market]
        for f in market_info['filters']:
            if f['filter'] == 'QUANTITY':
                if 'min' in f:
                    if volume < float(f['min']):
                        return False
                if 'max' in f:
                    if volume > float(f['max']):
                        return False
                # if 'tickSize' in f:
        return True
