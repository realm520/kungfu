import threading
from .gate_api import GateWebSocketApp
import pywingchun
from .api.client import Client
from collections import namedtuple
from . import mdmaker
from kungfu.yijinjing.log import create_logger
import kungfu.yijinjing.time as kft
import pyyjj
import kungfu.wingchun.msg as wc_msg

MakerConfig = namedtuple("MakerConfig", ["base", "bound", "samples", "variation", "randseed"])

class MarketDataGate(pywingchun.MarketData):
    def __init__(self, low_latency, locator, config_json):
        pywingchun.MarketData.__init__(self, low_latency, locator, "gate")
        self.config = MakerConfig(base=200.0, bound=1000, samples=1000,variation=4, randseed=6)
        self.api = Client("", "")
        self.orderbooks = {}
        self.logger = create_logger("gate_md", "info", pyyjj.location( pyyjj.mode.LIVE, pyyjj.category.MD, "gate", "gate", locator))
        self.precision = 10 ** 18
        self.gate_thread = None
        self.gate_app = GateWebSocketApp("wss://api.gateio.ws/ws/v4/",
                           "",
                           "",
                           on_open=self.g_on_open,
                           on_message=self.g_on_message)

    def on_start(self):
        pywingchun.MarketData.on_start(self)
        self.gate_thread = threading.Thread(target=self.start_gate_api)
        # self.markets = self.api.get_exchange_info()

    def quote_from_orderbook(self, ob):
        quote = pywingchun.Quote()
        instrument_id, exchange_id = ob.security.split(".")
        quote.data_time = self.now()
        quote.instrument_id = instrument_id
        quote.exchange_id = exchange_id
        quote.ask_price = [ob.offer_price(i) for i in range(0, min(10, ob.depth_offers()))]
        quote.ask_volume = [ob.offer_qty(i) for i in range(0, min(10, ob.depth_offers()))]
        quote.bid_price = [ob.bid_price(i) for i in range(0, min(10, ob.depth_bids()))]
        quote.bid_volume = [ob.bid_qty(i) for i in range(0, min(10, ob.depth_bids()))]
        quote.last_price = round((quote.ask_price[0] + quote.bid_price[0]) / 2.0, 2)
        return quote

    def start_gate_api(self):
        self.gate_app.run_forever(ping_interval=5)

    def init_order_book(self, instrument_id, exchange_id):
        security = instrument_id + "." + exchange_id
        symbol_id = pywingchun.utils.get_symbol_id(instrument_id, exchange_id)
        book = mdmaker.OrderBook(security=security)
        try:
            symbol = self._get_symbol_from_instrument_id(instrument_id)
            if symbol is None:
                return
            depth = self.api.get_order_book(symbol=symbol, limit=20)
            for a in depth['asks']:
                book.order(mdmaker.Order(secid=book.security, side=mdmaker.Side.SELL, price=self._add_precision(a[0]), qty=self._add_precision(a[1])))
            for b in depth['bids']:
                book.order(mdmaker.Order(secid=book.security, side=mdmaker.Side.BUY, price=self._add_precision(b[0]), qty=self._add_precision(b[1])))
        except:
            return
        self.orderbooks[symbol_id] = book

    def update_orderbooks(self):
        self.logger.debug(f"update_orderbooks: {len(self.orderbooks)}")
        for book in self.orderbooks.values():
            security = book.security
            instrument_id = security.split('.')[0]
            new_book = mdmaker.OrderBook(security=security)
            try:
                symbol = self._get_symbol_from_instrument_id(instrument_id)
                if symbol is None:
                    return
                depth = self.api.get_order_book(symbol=symbol, limit=20)
                for a in depth['asks']:
                    new_book.order(mdmaker.Order(secid=book.security,side=mdmaker.Side.SELL, price=self._add_precision(a[0]), qty=self._add_precision(a[1])))
                for b in depth['bids']:
                    new_book.order(mdmaker.Order(secid=book.security,side=mdmaker.Side.BUY, price=self._add_precision(b[0]), qty=self._add_precision(b[1])))
            except:
                continue
            quote = self.quote_from_orderbook(new_book)
            self.logger.debug(f"quote: {quote}")
            self.get_writer(0).write_data(0, wc_msg.Quote, quote)

    def subscribe(self, instruments):
        self.logger.debug(f"subscribe: {instruments}")
        for inst in instruments:
            symbol_id = pywingchun.utils.get_symbol_id(inst.instrument_id, inst.exchange_id)
            if symbol_id not in self.orderbooks:
                self.init_order_book(inst.instrument_id, inst.exchange_id)
        return True

    def unsubscribe(self, instruments):
        for inst in instruments:
            symbol_id = pywingchun.utils.get_symbol_id(inst.instrument_id, inst.exchange_id)
            self.orderbooks.pop(symbol_id, None)
        return True

    def g_on_open(self, ws):
        self.logger.info('websocket connected')
        ws.subscribe("spot.trades", ['BTC_USDT'], False)

    def on_message(self, ws, message):
        self.logger.info("message received from server: {}".format(message))


    def _add_precision(self, value):
        return float(value)
        # return int(float(value) * self.precision)

    def _get_symbol_from_instrument_id(self, instrument_id):
        try:
            loc = instrument_id.rindex('_')
            return instrument_id[:loc]
        except:
            self.logger.warning(f"invalid instrument_id: {instrument_id}")
            return None
