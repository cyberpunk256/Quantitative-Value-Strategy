#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import pandas as pd
import requests
import math
from scipy import stats 
from himitsu import TOKEN # API token


# In[ ]:


baskets =pd.read_csv("s&p500.csv") # import stocks


# In[ ]:


ticker = "NKE"
api_url = f"https://sandbox.iexapis.com/stable/stock/{ticker}/stats?token={TOKEN}"
data = requests.get(api_url).json()


# In[ ]:


def hoge(lst,n):
    for i in range(0,len(lst),n):
        yield lst[i:1 + n]
        
symbol_groups = list(hoge(baskets["Ticker"],100))
symbol_strings = []
for i in range(0,len(symbol_groups)):
    symbol_strings.append(",".join(symbol_groups[i]))    

my_columns = ["Ticker","Price","PE Ratio","No of shares to buy"]


# In[ ]:


final_dataframe = pd.DataFrame(columns = my_columns)

for symbol_string in symbol_strings:
    batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch/?types=stats,quote&symbols={symbol_string}&token={TOKEN}'
    data = requests.get(batch_api_call_url).json()
    for symbol in symbol_string.split(','):
        final_dataframe = final_dataframe.append(
                                        pd.Series([symbol, 
                                                   data[symbol]['quote']['latestPrice'],
                                                   data[symbol]['quote']['peRatio'],
                                                   'N/A'
                                                   ], 
                                                  index = my_columns), 
                                        ignore_index = True)


# # Filtering

# (What): select only top 50 stocks (How): filter the dataframe by price-to-earning ratio

# In[ ]:


final_dataframe.sort_values("Price-to-Earnings Ratio",inplace=True)
final_dataframe = final_dataframe[final_dataframe["Price-to-Earnings Ratio"] > 0]
final_dataframe = final_dataframe[:50]
final_dataframe.reset_index(inplace=True)
final_dataframe.drop("index",axis=1,inplace=True)


# In[ ]:


def portfolio_input():
    global pf_size
    pf_size = input("How big is your PF:")
    
    try:
        val = float(pf_size)
    except ValueError:
        print("Error:It is not Number")
        pf_size= input("How big is your PF:")


# In[ ]:


portfolio_input()


# # Value Strategy

# (What): create metrics such as "PER","PBR","PSR","EBITDA","EV" 

# In[ ]:


position_size = float(pf_size) / len(final_dataframe.index)
for i in range(0,len(final_dataframe["Ticker"])):
    final_dataframe.loc[i,"No of shares to buy"] = math.floor(position_size / final_dataframe["Price"][i])
final_dataframe


# In[ ]:


symbol = 'NKE'
batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch/?types=advanced-stats,quote&symbols={symbol}&token={TOKEN}'
data = requests.get(batch_api_call_url).json()

pe_ratio = data[symbol]['quote']['peRatio'] ## P/E Ratio

pb_ratio = data[symbol]['advanced-stats']['priceToBook']# P/B Ratio

ps_ratio = data[symbol]['advanced-stats']['priceToSales']#P/S Ratio

enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']# EV/EBITDA
ebitda = data[symbol]['advanced-stats']['EBITDA']
ev_to_ebitda = enterprise_value/ebitda

gross_profit = data[symbol]['advanced-stats']['grossProfit']
ev_to_gross_profit = enterprise_value/gross_profit# EV/GP


# In[ ]:


rv_columns = [
        'Ticker',
    'Price',
    'Number of Shares to Buy', 
    'Price-to-Earnings Ratio',
    'PE Percentile',
    'Price-to-Book Ratio',
    'PB Percentile',
    'Price-to-Sales Ratio',
    'PS Percentile',
    'EV/EBITDA',
    'EV/EBITDA Percentile',
    'EV/GP',
    'EV/GP Percentile',
    'RV Score'
]

rv_dataframe = pd.DataFrame(columns = rv_columns)

for symbol_string in symbol_strings:
    batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch?symbols={symbol_string}&types=quote,advanced-stats&token={TOKEN}'
    data = requests.get(batch_api_call_url).json()
    for symbol in symbol_string.split(','):
        enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']
        ebitda = data[symbol]['advanced-stats']['EBITDA']
        gross_profit = data[symbol]['advanced-stats']['grossProfit']
        
        try:
            ev_to_ebitda = enterprise_value/ebitda
        except TypeError:
            ev_to_ebitda = np.NaN
        
        try:
            ev_to_gross_profit = enterprise_value/gross_profit
        except TypeError:
            ev_to_gross_profit = np.NaN
            
        rv_dataframe = rv_dataframe.append(
            pd.Series([
                symbol,
                data[symbol]['quote']['latestPrice'],
                'N/A',
                data[symbol]['quote']['peRatio'],
                'N/A',
                data[symbol]['advanced-stats']['priceToBook'],
                'N/A',
                data[symbol]['advanced-stats']['priceToSales'],
                'N/A',
                ev_to_ebitda,
                'N/A',
                ev_to_gross_profit,
                'N/A',
                'N/A'
        ],
        index = rv_columns),
            ignore_index = True
        )


# In[ ]:


rv_dataframe[rv_dataframe.isnull().any(axis=1)] #"isnull" method detects invalid data


# In[ ]:


for column in ['Price-to-Earnings Ratio', 'Price-to-Book Ratio','Price-to-Sales Ratio',  'EV/EBITDA','EV/GP']:
    rv_dataframe[column].fillna(rv_dataframe[column].mean(), inplace = True) #"fillna" method replace missing value with new one


# # Calculation 

# In[ ]:


metrics = {
            'Price-to-Earnings Ratio': 'PE Percentile',
            'Price-to-Book Ratio':'PB Percentile',
            'Price-to-Sales Ratio': 'PS Percentile',
            'EV/EBITDA':'EV/EBITDA Percentile',
            'EV/GP':'EV/GP Percentile'
}

for row in rv_dataframe.index:
    for metric in metrics.keys():
        rv_dataframe.loc[row, metrics[metric]] = stats.percentileofscore(rv_dataframe[metric], rv_dataframe.loc[row, metric])/100

for metric in metrics.values():
    print(rv_dataframe[metric])


# # Top 50 stocks

# In[ ]:


rv_dataframe.sort_values(by = 'RV Score', inplace = True)
rv_dataframe = rv_dataframe[:50]
rv_dataframe.reset_index(drop = True, inplace = True)


# In[ ]:


position_size = float(portfolio_size) / len(rv_dataframe.index)
for i in range(0, len(rv_dataframe['Ticker'])-1):
    rv_dataframe.loc[i, 'No of Shares to Buy'] = math.floor(position_size / rv_dataframe['Price'][i])

