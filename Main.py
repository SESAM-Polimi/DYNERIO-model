# -*- coding: utf-8 -*-
"""
Created on Mon May  8 09:19:46 2023

@author: loren
"""

import pandas as pd
from Code.database_building import read_esm, read_mrio, add_supply_chains, esm_filters
from Code.soft_link import shock_capacity_demand
from Code.plot import plot_esm_data, plot_mat_demand

user = 'LR'
paths = pd.read_excel('paths.xlsx', index_col=[0])

#%% Read and plot esm data
esm_data = read_esm(paths,user,esm_filters)
# plot_esm(paths,user,esm_data)

#%% Read mrio
database = 'baseline'
mrio = read_mrio(database,paths,user)

#%% save mrio
# database = 'baseline'
# mrio.to_txt(paths.loc[f'mrio db {database}',user])

#%% Add new supply chains
add_commodities = paths.loc['mrio add commodities',user]
add_activities  = paths.loc['mrio add activities',user]

mrio = add_supply_chains(mrio,add_commodities,'Commodity')
mrio = add_supply_chains(mrio,add_activities,'Activity')

#%% Implement new capacity demands
tech_prices = pd.read_excel(paths.loc["link prices",user], sheet_name='technologies', index_col=[0,1], header=[0,1])
mrio = shock_capacity_demand(mrio, esm_data['cap_o'], tech_prices)

#%%
mrio.aggregate(paths.loc["mrio aggr baseline",user],levels=['Activity','Commodity'])

#%% Plot materials demand
mat_prices = pd.read_excel(paths.loc["link prices",user], sheet_name='materials', index_col=[0,1])
plot_mat_demand(paths,user,mrio,mat_prices)


