import numpy as np
from scipy.stats import norm
from datetime import datetime, timedelta
from utc_bot import UTCBot, start_bot
import proto.utc_bot as pb
import betterproto
import asyncio
import json
import py_vollib
from py_vollib.black_scholes.greeks import analytical
from typing import DefaultDict, Dict, Tuple, List
from collections import defaultdict

PARAM_FILE = "params.json"
OPTIONS_NAMES = ['SPY'+str(i)+'C' for i in range(65,135,5)] + ['SPY'+str(i)+'P' for i in range(65,135,5)]

class OptionBot(UTCBot):
    """
    An example bot that reads from a file to set internal parameters during the round
    """
    async def handle_exchange_update(self, update: pb.FeedMessage):
        kind, _ = betterproto.which_one_of(update, "msg")
        # Competition event messages
        if kind == "generic_msg":
            msg = update.generic_msg.message
            print(msg)
            
        if kind == "market_data":
            # Replace this as necessary: I'm not sure what the interface is for the actual market data
            market_data = update.market_data
            self.update_quotes(market_data)
        
        elif kind == "market_snapshot_msg":
            for asset in OPTIONS_NAMES:
                book = update.market_snapshot_msg.books[asset]
                if len(book.bids) > 0:
                    self._best_bid[asset] = float(book.bids[0].px)
                if len(book.asks) > 0:
                    self._best_ask[asset] = float(book.asks[0].px)
        
    async def handle_round_started(self):
        await asyncio.sleep(0.1)
        asyncio.create_task(self.handle_read_params())
        ### Best Bid in the order book
        self._best_bid: Dict[str, float] = defaultdict(
            lambda: 0
        )
        ### Best Ask in the order book
        self._best_ask: Dict[str, float] = defaultdict(
            lambda: 0
        )
        await asyncio.sleep(1)
        ######   TASKS     ######
       # asyncio.create_task(self.handle_read_params())
        for option in OPTIONS_NAMES:
            asyncio.create_task(self.grid_pricer(option))
            if self.params["strangle"] == 1:
                asyncio.create_task(self.strangle())
            if self.params["iron_condor"]:
                asyncio.create_task(self.iron_condor())

    async def handle_read_params(self):
        while True:
            try:
                self.params = json.load(open(PARAM_FILE, "r"))
            except:
                print("Unable to read file " + PARAM_FILE)

            await asyncio.sleep(1)
            
            # The following parameters were taken from the case packet
            self.underlying_price = 100
            self.strikes = np.arange(65, 136, 5)
            self.quote_expiry = timedelta(seconds=10)
            self.macro_shock_coefficient = 0.01
            self.sentiment_coefficient = 0.005
            self.risk_free_rate = 0.02
            self.time_to_expiry = 30  # In days

            #need way to store each iv
            self.iv_dict = dict({'call'+str(i):0 for i,j in zip(self.strikes,self.strikes)},**{'put'+str(i):0 for i,j in zip(self.strikes,self.strikes)})
            self.greeks = {
                'Delta':0,
                'Gamma':0,
                'Vega':0,
                'Theta':0
            }
        #     # self.orders = self.__orders: DefaultDict[str, Tuple[str, float]] = defaultdict(
        #     # lambda: ("", 0)
        # )
            
    def black_scholes(self, call, S, K, T, r, sigma):
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        if call:
            return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    # #new stuff - Ralph
    # async def IV_Update(self, asset):
    #     #Sth to scan for if its "{Call}65" or "{Put}65
    #     price = #UTC Bot code to get current asset price
    #     iv = 0.4
    #     black_calc = 0
    #     while price != iv:
    #         black_calc = self.black_scholes(call, self.underlying, /K, /T, /r, iv)
    #         if abs(black_calc - price) < 0.05 # good enough val?
    #             return iv
    #         elif black_calc > price:
    #         iv = .01 * (black_calc - price)
    #             #when black calc is higher gotta make iv lower and vice versa. Unclear or how much to increment

    # async def greek_update(self):
    #     #again scan if call or put
    #     # add_delta = py_vollib.black_scholes.greeks.analytical.delta(flag, /S, /K, /t, /r, iv) #flag is c or p for call and put #derive from data
    #     # add_gamma = py_vollib.black_scholes.greeks.analytical.gamma(flag, /S, /K, /t, /r, iv)
    #     # add_vega = py_vollib.black_scholes.greeks.analytical.vega(flag, /S, /K, /t, /r, iv)
    #     # add_theta = py_vollib.black_scholes.greeks.analytical.theta(flag, /S, /K, /t, /r, iv)
    #     #add this to dictionary values for the greeks, apprently u can't just plus the stuff   
    #     #if 'c' in self._ord

    #     self.greeks["Delta"] += analytical.delta(flag, /S, /K, /t, /r, iv) #flag is c or p for call and put #derive from data
    #     self.greeks["Gamma"] += analytical.gamma(flag, /S, /K, /t, /r, iv)
    #     self.greeks["Vega"] += analytical.vega(flag, /S, /K, /t, /r, iv)
    #     self.greeks["Theta"] += analytical.theta(flag, /S, /K, /t, /r, iv)       

    # for option in OPTIONS_NAMES:
    #     asyncio.create_task(self.IV_Update)

    # for order in self.orders:
    #     asyncio.create_task(self.greek_update)

    def update_quotes(self, market_data):
        now = datetime.utcnow()
        T = (self.time_to_expiry - (now - self.round_start_time).days) / 365.0

        # Adjust underlying price based on macroeconomic shocks and sentiments (if provided, just delete this line if we're not using these factors)
        self.underlying_price *= (1 + self.macro_shock_coefficient * np.random.randn() + self.sentiment_coefficient * np.random.randn())

        for strike in self.strikes:
            call_price = self.black_scholes(True, self.underlying_price, strike, T, self.risk_free_rate, self.volatility)
            put_price = self.black_scholes(False, self.underlying_price, strike, T, self.risk_free_rate, self.volatility)
            
            # Synthesize market data and calculate expected profit
            bid, ask = self.synthesize_market_data_and_calculate_profit(option_type="CALL", strike=strike, price=call_price)
            if bid is not None and ask is not None:
                self.place_limit_order("CALL", strike, bid, ask, self.quote_expiry)

            bid, ask = self.synthesize_market_data_and_calculate_profit(option_type="PUT", strike=strike, price=put_price)
            if bid is not None and ask is not None:
                self.place_limit_order("PUT", strike, bid, ask, self.quote_expiry)


    def synthesize_market_data_and_calculate_profit(self, option_type, strike, price):
        # Calculate the spread and mid-price based on the Black-Scholes price
        spread = 0.02 * price
        mid_price = price

        # Determine the bid and ask prices
        bid = mid_price - spread / 2
        ask = mid_price + spread / 2
        
        # Adjust bid and ask prices based on strike distance from the underlying price
        distance = abs(self.underlying_price - strike)
        bid_adjustment = distance * 0.01
        ask_adjustment = distance * 0.01

        bid += bid_adjustment
        ask -= ask_adjustment

        # Calculate expected profit
        expected_profit_bid = mid_price - bid
        expected_profit_ask = ask - mid_price
        
        # Check if the option is a call or a put, and apply any additional logic based on option type if needed
        if option_type == "CALL":
            # Apply any call-specific logic here, if needed (otherwise just delete this line)
            pass
        elif option_type == "PUT":
            # Apply any put-specific logic here, if needed 
            pass

        # If the expected profit is positive, quote the bid and ask prices
        if expected_profit_bid > 0 and expected_profit_ask > 0:
            return bid, ask

        # If the expected profit is not positive, do not quote the prices
        return None, None
    

    # def place_limit_order(self, option_type, strike, bid, ask, expiry):
    #     # Place a limit order for both bid and ask prices
    #     order_bid = pb.Order(
    #         order_type=pb.OrderType.LIMIT,
    #         option_type=pb.OptionType[option_type],
    #         strike=strike,
    #         buy_sell=pb.BuySell.BUY,
    #         price=bid,
    #         quantity=1,
    #         expire_time=datetime.utcnow() + expiry
    #     )
    #     order_ask = pb.Order(
    #         order_type=pb.OrderType.LIMIT,
    #         option_type=pb.OptionType[option_type],
    #         strike=strike,
    #         buy_sell=pb.BuySell.SELL,
    #         price=ask,
    #         quantity=1,
    #         expire_time=datetime.utcnow() + expiry
    #     )

    #     # Send the orders to the exchange
    #     asyncio.create_task(self.place_order(order_bid))
    #     asyncio.create_task(self.place_order(order_ask))
    
    async def grid_pricer(self, asset):
        await asyncio.sleep(2)
        spot = (self._best_bid[asset]+self._best_ask[asset])/2 
        for level in np.arange(0.5,2,0.5):
            await self.place_order(asset,pb.OrderSpecType.LIMIT, pb.OrderSpecSide.ASK, 5, spot+level)   
            await self.place_order(asset,pb.OrderSpecType.LIMIT, pb.OrderSpecSide.BID, 5, spot-level)

    async def strangle(self):
        spot = (self._best_bid["SPY"]+self._best_ask['SPY'])/2
        new = (spot // 5)*5
        lower = new - 15
        upper = new + 15
        self.place_order('SPY'+str(lower)+'p',pb.OrderSpecType.MARKET, pb.OrderSpecSide.BID, 5) 
        self.place_order('SPY'+str(upper)+'c',pb.OrderSpecType.MARKET, pb.OrderSpecSide.BID, 5) 
        asyncio.sleep(63)  ########################### change to 21 v 63 

    async def iron_condor(self):    
        spot = (self._best_bid["SPY"]+self._best_ask['SPY'])/2
        new = (spot // 5)*5
        super_low = new-  20
        low = new - 10
        up = new + 10
        super_up = new+20
        self.place_order('SPY'+str(super_low)+'p',pb.OrderSpecType.MARKET, pb.OrderSpecSide.BID, 5) 
        self.place_order('SPY'+str(super_up)+'c',pb.OrderSpecType.MARKET, pb.OrderSpecSide.BID, 5) 
        self.place_order('SPY'+str(low)+'p',pb.OrderSpecType.MARKET, pb.OrderSpecSide.ASK, 5) 
        self.place_order('SPY'+str(up)+'c',pb.OrderSpecType.MARKET, pb.OrderSpecSide.BID, 5) 
        asyncio.sleep(63)


if __name__ == "__main__":
    start_bot(OptionBot)
