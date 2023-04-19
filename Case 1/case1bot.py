#!/usr/bin/env python

from collections import defaultdict
from typing import DefaultDict, Dict, Tuple, List
from utc_bot import UTCBot, start_bot
import math
import proto.utc_bot as pb
import betterproto
import asyncio
import re
import numpy as np

DAYS_IN_MONTH = 21
DAYS_IN_YEAR = 252
INTEREST_RATE = 0.02
NUM_FUTURES = 14
TICK_SIZE = 0.00001
FUTURE_CODES = [chr(ord('A') + i) for i in range(NUM_FUTURES)] # Suffix of monthly future code
CONTRACTS = ['SBL'] +  ['LBS' + c for c in FUTURE_CODES] + ['LLL']
FUTURE_CONTRACTS = ['LBS' + c for c in FUTURE_CODES]
MODELS = {"LBSA": (0.28879233138041943,-0.014344824571183334),
        "LBSB": (0.6023066202936028,-0.01742281880526749),
        "LBSC":(0.8747229246467849,-0.01603930017915729),
        "LBSD":(1.1543478486715124,-0.015346389592722219),
        "LBSE":(1.439323350349281,-0.014980766538606423),
        "LBSF":(1.7269722251729744,-0.01474918508793019),
        "LBSG":(2.0176883330792914,-0.014615905960060582),
        "LBSH":(2.310686575613605,-0.014543274018779122),
        "LBSI": (2.6038558941207475,-0.014480841755721306),
        "LBSJ":(2.896932431674776,-0.01441989764077772),
        "LBSK":(3.1904995109088903,-0.014366250143628783),
        "LBSL":(3.485096226619385,-0.014324380781456666),
        "LBSM":(3.7841457099191853, -0.014331826875116666),
        "LBSN":(4.08370669520336,-0.014339285233264)}


class Case1Bot(UTCBot):
    """
    An example bot
    """
    etf_suffix = ''
    async def create_etf(self, qty: int):
        '''
        Creates qty amount the ETF basket
        DO NOT CHANGE
        '''
        if len(self.etf_suffix) == 0:
            return pb.SwapResponse(False, "Unsure of swap")
        return await self.swap("create_etf_" + self.etf_suffix, qty)

    async def redeem_etf(self, qty: int):
        '''
        Redeems qty amount the ETF basket
        DO NOT CHANGE
        '''
        if len(self.etf_suffix) == 0:
            return pb.SwapResponse(False, "Unsure of swap")
        return await self.swap("redeem_etf_" + self.etf_suffix, qty) 
    
    async def days_to_expiry(self, asset):
        '''
        Calculates days to expiry for the future
        '''
        future = ord(asset[-1]) - ord('A')
        expiry = 21 * (future + 1)
        return self._day - expiry

    async def handle_exchange_update(self, update: pb.FeedMessage):
        '''
        Handles exchange updates
        '''
        kind, _ = betterproto.which_one_of(update, "msg")
        #print(kind)
        #Competition event messages
        if kind == "generic_msg":
            msg = update.generic_msg.message
            
            # Used for API DO NOT TOUCH
            if 'trade_etf' in msg:
                self.etf_suffix = msg.split(' ')[1]
                
            # Updates current weather
            if "Weather" in update.generic_msg.message:
                msg = update.generic_msg.message
                weather = float(re.findall("\d+\.\d+", msg)[0])
                self._weather_log.append(weather)
                
            # Updates date
            if "Day" in update.generic_msg.message:
                self._day = int(re.findall("\d+", msg)[0])
                            
            # Updates positions if unknown message (probably etf swap)
            else:
                resp = await self.get_positions()
                if resp.ok:
                    self.positions = resp.positions
                    
        elif kind == "market_snapshot_msg":
            for asset in CONTRACTS:
                book = update.market_snapshot_msg.books[asset]
                self._best_bid[asset] = float(book.bids[0].px)
                self._best_ask[asset] = float(book.asks[0].px)
                
            


    async def handle_round_started(self):
        ### Current day
        self._day = 0
        ### Current Bids
        self._bids: Dict[str, List[pb.MarketSnapshotMessageBookPriceLevel]] = defaultdict(
            lambda: None
        )
        ### Current Asks
        self._asks: Dict[str, List[pb.MarketSnapshotMessageBookPriceLevel]] = defaultdict(
            lambda: None
        )
        
        ### Best Bid in the order book
        self._best_bid: Dict[str, float] = defaultdict(
            lambda: 0
        )
        ### Best Ask in the order book
        self._best_ask: Dict[str, float] = defaultdict(
            lambda: 0
        )
        ### Order book for market making
        self.__orders: DefaultDict[str, Tuple[str, float]] = defaultdict(
            lambda: ("", 0)
        )
        ### TODO Recording fair price for each asset
        self._fair_price: DefaultDict[str, float] = defaultdict(
            lambda: ("", 0)
        )
        ### TODO spread fair price for each asset
        self._spread: DefaultDict[str, float] = defaultdict(
            lambda: ("", 0)
        )

        ### TODO order size for market making positions
        self._quantity: DefaultDict[str, int] = defaultdict(
            lambda: ("", 0)
        )
        
        ### List of weather reports
        self._weather_log = []
        
        await asyncio.sleep(.1)
        ###
        ### TODO START ASYNC FUNCTIONS HERE
        ###

        ###asyncio.create_task(self.example_redeem_etf())
        ####asyncio.create_task(self.no_soybean())
        asyncio.create_task(self.etf_ask_arb())
        asyncio.create_task(self.etf_bid_arb())
        asyncio.create_task(self.sell_bean())
        for asset in FUTURE_CONTRACTS:
            await asyncio.sleep(.1)
            asyncio.create_task(self.buy_on_leq_fair(asset,20))
            await asyncio.sleep(.1)
            asyncio.create_task(self.sell_on_ge_fair(asset,20))
            await asyncio.sleep(.1)
            asyncio.create_task(self.grid_pricer(asset))
        
        # Starts market making for each asset
        # for asset in CONTRACTS:
            # asyncio.create_task(self.make_market_asset(asset))

    # This is an example of creating and redeeming etfs
    # You can remove this in your actual bots.
    async def example_redeem_etf(self):
        while True:
            redeem_resp = await self.redeem_etf(1)
            create_resp = await self.create_etf(5)
            await asyncio.sleep(1)


    ### Helpful ideas
    async def calculate_risk_exposure(self):
        pass
    
    async def calculate_fair_price(self, asset):
        pass
        

    async def etf_ask_arb(self):
        while self._day <= DAYS_IN_YEAR:
            month = (self._day // 21) + 1
            asset1 = CONTRACTS[month]
            asset2 = CONTRACTS[month+1]
            asset3 = CONTRACTS[month+2]

            if self._best_bid["LLL"] == 0.0001:
                continue

            # viableTrades = min(self._asks_qty["LLL"], self._bids_qty[asset1]//5, self._bids_qty[asset2]//3, self._bids_qty[asset3]//2)

            if float(self._best_ask["LLL"]) < float(self._best_bid[asset1])*5 + float(self._best_bid[asset2])*3 + float(self._best_bid[asset3])*2:
                continue
           
            a = await self.place_order(asset1, pb.OrderSpecType.MARKET, pb.OrderSpecSide.BID, 5)#*viableTrades)
            b = await self.place_order(asset2, pb.OrderSpecType.MARKET, pb.OrderSpecSide.BID, 3)#*viableTrades)
            c = await self.place_order(asset3, pb.OrderSpecType.MARKET, pb.OrderSpecSide.BID, 2)#*viableTrades)
            s = await self.create_etf(1)#viableTrades)
            d = await self.place_order("LLL", pb.OrderSpecType.MARKET, pb.OrderSpecSide.ASK, 1)#viableTrades)

    async def etf_bid_arb(self):
        await asyncio.sleep(.1)
        while self._day <= DAYS_IN_YEAR:
            month = (self._day // 21) + 1
            asset1 = CONTRACTS[month]
            asset2 = CONTRACTS[month+1]
            asset3 = CONTRACTS[month+2]

            if self._best_ask["LLL"] == 0.0001:
                continue

            # viableTrades = min(self._asks_qty["LLL"], self._bids_qty[asset1]//5, self._bids_qty[asset2]//3, self._bids_qty[asset3]//2)

            if float(self._best_bid["LLL"]) > float(self._best_ask[asset1])*5 + float(self._best_ask[asset2])*3 + float(self._best_ask[asset3])*2:
                continue
           
            d = await self.place_order("LLL", pb.OrderSpecType.MARKET, pb.OrderSpecSide.BID, 10)#viableTrades)
            s = await self.redeem_etf(1)#viableTrades)
            a = await self.place_order(asset1, pb.OrderSpecType.MARKET, pb.OrderSpecSide.ASK, 5)#*viableTrades)
            b = await self.place_order(asset2, pb.OrderSpecType.MARKET, pb.OrderSpecSide.ASK, 3)#*viableTrades)
            c = await self.place_order(asset3, pb.OrderSpecType.MARKET, pb.OrderSpecSide.ASK, 2)#*viableTrades)
    
    
    async def calculate_preliminary_fair(self, asset):
        await asyncio.sleep(.2)
        spot = (self._best_bid["SBL"] + self._best_ask["SBL"]) / 2
        # days_to_expiry = await self.days_to_expiry(asset)
        month = ((self._day // 21) + 1)*21
        adjusted_daily_spot = spot * (math.e ** ((((1.02) ** (252 ** -1)) -1) + (0.1 / spot) * (month/252)))
        actual_fair = adjusted_daily_spot + MODELS[asset][0] + MODELS[asset][1] * self._day
        return actual_fair
    
    async def buy_on_leq_fair(self, asset, amount):
        await asyncio.sleep(.1)
        spot = (self._best_bid[asset] + self._best_ask[asset]) / 2
        fair_price = await self.calculate_preliminary_fair(asset)
        if spot < fair_price:
            await self.place_order(asset, pb.OrderSpecType.LIMIT, pb.OrderSpecSide.BID, amount,spot)
            
    async def sell_on_ge_fair(self, asset, amount):
        await asyncio.sleep(.1)
        spot = (self._best_bid[asset] + self._best_ask[asset]) / 2
        fair_price = await self.calculate_preliminary_fair(asset)
        if spot > fair_price:
            await self.place_order(asset, pb.OrderSpecType.LIMIT, pb.OrderSpecSide.ASK, amount, spot)

    async def grid_pricer(self, asset):
        await asyncio.sleep(.1)
        spot = (self._best_bid[asset]+self._best_ask[asset])/2
        for level in np.arange(0.1,0.4,0.1):
            await self.place_order(asset,pb.OrderSpecType.LIMIT, pb.OrderSpecSide.ASK, 20, spot+level)   
            await self.place_order(asset,pb.OrderSpecType.LIMIT, pb.OrderSpecSide.BID, 20, spot-level) 

    def round_nearest(x, a):
        return round(round(x / a) * a, -int(math.floor(math.log10(a))))   

    async def sell_bean(self):
        self.place_order('SBL', pb.OrderSpecType.MARKET,pb.OrderSpecSide.ASK, 1)

if __name__ == "__main__":
    start_bot(Case1Bot)

# python case1_botcopy_True.py "BostonCollege" --key Beedrill58 --host 9090 --port 9090

