#!/usr/bin/python3
"""
Market data generator script.
"""

import argparse
import csv
import itertools
import math
import random
import struct
import sys
import time
from enum import Enum
from functools import reduce

import numpy
from recordclass import recordclass
from sortedcontainers import SortedListWithKey

MIN_TICK = 0.01
MAX_TICK = 20 * MIN_TICK
DECIMALS = int(abs(math.log10(MIN_TICK)))
DECIMAL_CONVERT = math.pow(10, DECIMALS)
MAX_QUANTITY = 40
VAL_RATIO_MAX = 0.95
SPREAD_MAX = 20 * MIN_TICK
MAX_DEPTH = 20
MAX_QTY = 100

LEVEL_FIELDS = ['price', 'qty', 'order_count']
TRADE_FIELDS = ['price', 'qty', 'aggressor']
FIELDS = ['timestamp', 'secid', 'trade_valid', 'book_valid']

MIN_TIME_DELTA_NANOS = 200
MAX_TIME_DELTA_NANOS = 100000000

OrderBookLevel = recordclass('OrderBookLevel',
                             LEVEL_FIELDS)
Order = recordclass('Order', ['secid', 'side', 'price', 'qty'])
Trade = recordclass('Trade', TRADE_FIELDS)

LEVEL_FORMAT = "lvl{}_{}_{}"
TRADE_FORMAT = "trade_{}"

def now_nanos():
    """Returns the current simulation time in nanoseconds"""
    if now_nanos.sim_time == 0:
        now_nanos.sim_time += int(time.time() * 1000000000)
    else:
        now_nanos.sim_time += random.randint(MIN_TIME_DELTA_NANOS, MAX_TIME_DELTA_NANOS)

    return now_nanos.sim_time

class Side(Enum):
    """
        Trading Side
    """
    BUY = 1
    SELL = 2

class OrderBookUtils(object):
    """Utility class for OrderBook manipulation"""

    @staticmethod
    def compact(levels, start):
        """
            Compacts an order list, such that orders at the same price level are merged.
            This assumes the order list is sorted.
        """

        # print("Compacting book")
        # self.print()
        last_level = None
        for i in range(start, -1, -1):
            level = levels[i]
            if last_level:
                if level.price == last_level.price:
                    last_level.qty += level.qty
                    last_level.order_count += level.order_count
                    del levels[i]
                else:
                    break
            else:
                last_level = level

    @staticmethod
    def reduce_book_value(level1, level2):
        """
            Reduction function for price * qty
        """
        value1 = level1
        value2 = level2
        if isinstance(level1, OrderBookLevel):
            value1 = level1.price * level1.qty
        if isinstance(level2, OrderBookLevel):
            value2 = level2.price * level2.qty
        return value1 + value2

    @staticmethod
    def qty(levels, at_level):
        """Get qty at sepcific level"""
        if len(levels) > at_level:
            return levels[at_level].qty
        return 0

    @staticmethod
    def price(levels, at_level):
        """Get price at sepcific level"""
        if len(levels) > at_level:
            return levels[at_level].price
        return 0.0

    @staticmethod
    def book_value(levels):
        """
            Computes the value of open orders on a list of book levels
        """
        if len(levels) > 1:
            return reduce(OrderBookUtils.reduce_book_value, levels)
        elif len(levels) > 0:
            return levels[0].price * levels[0].qty
        else:
            raise Exception("Cannot reduce empty book")


class OrderBook(object):
    """An Order Book data model"""
    def __init__(self, security):
        self.bid = SortedListWithKey(key=(lambda level: level.price))
        self.offer = SortedListWithKey(key=(lambda level: level.price))
        self.security = security
        self.mids = []
        self.last_price = 0.0

    def order(self, order):
        if self.security != order.secid:
            raise ("Cannot place order for security "
                   "%s on book[%s]" % (order.security, self.security))

        levels = self.bid
        if order.side == Side.SELL:
            levels = self.offer
        new_level = OrderBookLevel(price=order.price, qty=order.qty, order_count=1)
        levels.add(new_level)
        # if order.side == Side.SELL:
        #     size = len(self.offer)
        #     if size > MAX_DEPTH:
        #         for _ in itertools.repeat(None, size - MAX_DEPTH):
        #             del self.offer[-1]
        # else:
        #     size = len(self.bid)
        #     if size > MAX_DEPTH:
        #         for _ in itertools.repeat(None, size - MAX_DEPTH):
        #             del self.bid[0]

    def mid(self):
        """
            Get mid price of top of Book
        """
        if self.bid and self.offer:
            return (self.bid[-1].price + self.offer[0].price) / 2.0

        raise Exception("No bids / offers!")

    def update_mid_series(self):
        """Adds current mid price to the mid series"""
        self.mids += [self.mid()]

    def spread(self):
        """
            Get the spread at the Top of Book
        """
        if self.bid and self.offer:
            return self.offer[0].price - self.bid[-1].price

        return 0

    def value_offers(self):
        """
            Returns the value of offers on the book
        """
        return OrderBookUtils.book_value(self.offer)

    def value_bids(self):
        """
            Returns the value of bids on the book
        """
        return OrderBookUtils.book_value(self.bid)

    def depth_offers(self):
        """
            Returns the number of offers on the book
        """
        return len(self.offer)

    def depth_bids(self):
        """
            Returns the number of bids on the book
        """
        return len(self.bid)

    def best_bid(self):
        """Get best bid"""
        if self.bid:
            return self.bid[-1].price
        return None

    def best_offer(self):
        """Get best offer"""
        if self.offer:
            return self.offer[0].price
        return None

    def bid_price(self, at_level):
        """Get price at sepcific level"""
        return OrderBookUtils.price(self.bid, -(at_level+1))

    def bid_qty(self, at_level):
        """Get qty at sepcific level"""
        return OrderBookUtils.qty(self.bid, -(at_level+1))

    def offer_price(self, at_level):
        """Get price at sepcific level"""
        return OrderBookUtils.price(self.offer, at_level)

    def offer_qty(self, at_level):
        """Get qty at sepcific level"""
        return OrderBookUtils.qty(self.offer, at_level)

    def aggregate_bid_qty(self, trade_price):
        """Sum of qty that would match a price"""
        qty = 0
        for i in range(len(self.bid)):
            if self.bid[-i].price >= trade_price:
                qty += self.bid[-i].qty
        return qty

    def aggregate_offer_qty(self, trade_price):
        """Sum of qty that would match a price"""
        qty = 0
        for i in range(len(self.offer)):
            # print("trade_price = {} offer[{}] = {}".format(trade_price, i, self.offer[i].price))
            if self.offer[i].price <= trade_price:
                qty += self.offer[i].qty
                # print("Running qty = {}".format(qty))
        return qty

    def display(self):
        """
            Prints the order book
        """
        size_bid = len(self.bid)
        size_offer = len(self.offer)
        print("Book[%s]: %d bids, %d offers --> mid @ %f"  % (self.security,
                                                              size_bid, size_offer, self.mid()))
        print("{0: ^32} | {1: ^32}".format("bid", "offer"))
        print("{0:^10},{1:^10},{2:^10} | {3:^10}, {4:^10}, {5:^10}".format(
            "count", "qty", "price", "price", "qty", "count"))

        empty_level = OrderBookLevel("-", "-", "-")
        for i in range(max(size_bid, size_offer)):
            bid = self.bid[-(i+1)] if i < size_bid else empty_level
            offer = self.offer[i] if i < size_offer else empty_level
            print("{0:^10},{1:^10},{2:^10} | {3:^10}, {4:^10}, {5:^10}".format(
                bid.order_count, bid.qty, bid.price, offer.price, offer.qty, offer.order_count))


