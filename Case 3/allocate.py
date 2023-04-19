import numpy as np
import pandas as pd
import scipy

#########################################################################
## Change this code to take in all asset price data and predictions    ##
## for one day and allocate your portfolio accordingly.                ##
#########################################################################

df = pd.read_csv("Training Data_Case 3.csv").drop('Unnamed: 0', axis=1)

def allocate_portfolio(asset_prices): #Also needs asset price predictions
    global df
    df.loc[len(df)] = asset_prices
    dfR = df.pct_change()
    R = np.transpose(dfR.to_numpy()[1:,:])
    cov = np.cov(R)
    P =[]

    # Fetching required distribution variables for specific distributions (really ugly!)
    P.append(scipy.stats.hypsecant.fit(R[0]))
    P.append(scipy.stats.norminvgauss.fit(R[1]))
    P.append(scipy.stats.t.fit(R[2]))
    P.append(scipy.stats.dweibull.fit(R[3]))
    P.append(scipy.stats.gennorm.fit(R[4]))
    P.append(scipy.stats.hypsecant.fit(R[5]))
    P.append(scipy.stats.johnsonsu.fit(R[6]))
    P.append(scipy.stats.beta.fit(R[7]))
    P.append(scipy.stats.gennorm.fit(R[8]))
    P.append(scipy.stats.gennorm.fit(R[9]))

    # Based on distribution variables, obtain moments of distributions
    M = np.stack([
        np.array(scipy.stats.hypsecant.stats(P[0][0], P[0][1], moments = 'mvsk')),
        np.array(scipy.stats.norminvgauss.stats(P[1][0], P[1][1], P[1][2], P[1][3], moments = 'mvsk')),
        np.array(scipy.stats.t.stats(P[2][0], P[2][1], moments = 'mvsk')),
        np.array(scipy.stats.dweibull.stats(P[3][0], P[3][1], P[1][2], moments = 'mvsk')),
        np.array(scipy.stats.gennorm.stats(P[4][0], P[4][1], P[4][2], moments = 'mvsk')),
        np.array(scipy.stats.hypsecant.stats(P[5][0], P[5][1], moments = 'mvsk')),
        np.array(scipy.stats.johnsonsu.stats(P[6][0], P[6][1], P[6][2], P[6][3], moments = 'mvsk')),
        np.array(scipy.stats.beta.stats(P[7][0], P[7][1], P[7][2], P[7][3], moments = 'mvsk')),
        np.array(scipy.stats.gennorm.stats(P[8][0], P[8][1], P[8][2], moments = 'mvsk')),
        np.array(scipy.stats.gennorm.stats(P[9][0], P[9][1], P[9][2], moments = 'mvsk')),
        ])
        
    return np.dot(np.linalg.inv(cov), R.mean(axis=1))

def grading(testing): #testing is a pandas dataframe with price data, index and column names don't matter
    weights = np.full(shape=(len(testing.index),10), fill_value=0.0)
    for i in range(0,len(testing)):
        unnormed = np.array(allocate_portfolio(list(testing.iloc[i,:])))
        positive = np.absolute(unnormed)
        normed = positive/np.sum(positive)
    capital = [1]
    for i in range(len(testing) - 1):
        shares = capital[-1] * np.array(weights[i]) / np.array(testing.iloc[i,:])
        capital.append(float(np.matmul(np.reshape(shares, (1,10)),np.array(testing.iloc[i+1,:]))))
    returns = (np.array(capital[1:]) - np.array(capital[:-1]))/np.array(capital[:-1])
    return np.mean(returns)/ np.std(returns) * (252 ** 0.5), capital, weights