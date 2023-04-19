# UChicago-Trading-Comp-2023
Boston College's code for UChicago-Trading-Comp-2023. 

Placed 5th for second case.

## Case 1
For this case, teams were tasked with market making the soybean market (SBL), the corresponding futures markets (LBSA corr. expiry Jan, etc. up to N), and the ETF market (LLL) (which is comprised of 5 futures expiring this month, 3 expiring next month, and 2 expiring next two months). Another factor in this case is weather data, which was to be used to predict price/returns of soybeans. A final key aspect of the case is a carrying cost of 0.10 per unit of SBL per day. Teams were given 2022: SBL, LBS(A-N), LLL, weather, 2021: SBL, weather, 2020: SBL, weather.

### Our Strategy
Our team focused on split our bot into 3 main functions: 1) Etf arb (everyone does this), 2) Futures arb (everyone does this), and 3) Grid pricing (i.e. wide spreads). 

1) The important part of this bot is looking into the "depth" fo the orderbook in order to prevent slippage. So in practice, our bot scanned the bid/asks of LLL and the corresponding futures, then traded as much aas it could while still taking some profit.

2) The first step is getting a fair price for our futures. Our team did this by using the cost-of-carry model and running a linear regression to correct for errors (note. this is probably overfitting but live and learn). Then, our bot simply bought when fair > spot and sold when fair < spot. We chose an arbitrary amount to buy/sell but there is probably a more rigorous way to size bets; the important thing was to have symmetric quotes so we'd be market-netural.

3) Anticpating competing against other teams, we figured we weren't competing against a truly "rational" market. To take advantage of this, we set massive spreads to earn cash from naive bots.

#### Post Case 1 Disc.
1. Portfolio risk relative to weather index or underlying price.
2. Soybean had lognormal stationary distribution. Soybean index after 60 days. 
3. Log common price
4. KEY: Spot Future parity, enable long exp to SBL w/o carry cost. Shorting future. Indep, so greater dev. Can calc weather/underlying risk
5. KEY ETH Arbitrage. Rebalance guaranteed to inc price ETF

## Case 2
For this case, teams were tasked with market making options on a kinda illquid underlying. Options had different strikes by $5 (from 65-135) for calls and puts (e.g. SPY65P would be a put w/ strike 65). Teams were given a year of price path data (spoiler: this isn't enough to do anything). In an ideal world, one would code a black-scholes/tree fct to price options, a function to keep track of greeks, and a function (w/ adjustable param) to model the volatililty smile. With that, the following is our strategy (given that we had poor time management and this definitely wasn't finished on the bus ride to the venue) :

### Our strategy

1) Grid pricing. See Case-1 Strategy 3). Code was copy-pasted and adjusted for the names of assets.
2) Bets on Volatility. A discussion my team had was betting on vol while being neutral on price movements. Thus, we set up strangles and iron-condors to bet on high and low vol (resp.). This helped hedge risk from 1) (probably).

#### Post Case 2 Disc.
1. Oil curve not flat. Key was to predict shape of curve.
2. If u watch order book you get info. 
3. Data gen. Underlying from ARMA model, scale down var to match 2 mon. Moving avg.
4. Based vol on underlying, sth sth time drift.
5. Weighted avg coefficient using iid markvov. 
6. Tips and Tricks
    1. Model vol curve. In params.json, should have had params to adjust skew and smile coefficient vol smile.
    2. Following Smart Bots
        1. Large orders indicate confidence in a trade. Signifies More info
    3. Delta Hedging. Delta risks lower.

## Case 3
Teams were given ten years of prices of ten different stocks. Teams were tasked with submitting optimal portfolio dates for each following day. My team just did basic Markowitz. Winning team just ran a Monte-Carlo and picked from that so....
