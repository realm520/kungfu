import random
import kungfu.yijinjing.time as kft
from kungfu.wingchun.constants import *

md_source = Source.RESTBN
td_source = Source.SIM
exchange = Exchange.BN

def test_timer(context, event):
    context.log.info('test timer')

def test_time_interval(context, event):
    context.log.info('test time interval')

def pre_start(context):
    context.log.info("pre run strategy")
    context.add_account(td_source, "sim1", 100000000.0)
    context.subscribe(md_source, ["BTCUSDT_SPOT", "ETCUSDT_SPOT"], exchange)

def on_quote(context, quote):
    context.logger.info("position: {}".format(context.book.get_position(quote.instrument_id, exchange)))
    amount = random.uniform(1, 200)
    order_id = context.insert_order(quote.instrument_id, exchange, "sim1", quote.ask_price[0], amount, PriceType.Limit, Side.Buy, Offset.Open, HedgeFlag.Speculation)
    context.log.info(
        "quote received: [time]{} [instrument_id]{} [last_price]{} [order_id]{}"\
            .format(kft.strftime(quote.data_time), quote.instrument_id, quote.last_price, order_id))

def on_transaction(context, transaction):
    context.log.info("{} {}".format(transaction.instrument_id, transaction.exchange_id))
    pass

def on_entrust(context, entrust):
    context.log.info("{} {}".format(entrust.instrument_id, entrust.exchange_id))
    pass

def on_order(context, order):
    context.log.info('order received: [instrument_id]{} [volume]{} [price]{}'.format(order.instrument_id, order.volume, order.limit_price))

def on_trade(context, trade):
    context.log.info('trade received: {} [trade_id]{} [volume]{} [price]{}'.format(kft.strftime(trade.trade_time), trade.order_id, trade.volume, trade.price))
