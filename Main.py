# -*- coding: utf-8 -*-
"""
Created on Mon May  8 09:19:46 2023

@author: loren
"""

import pandas as pd
from copy import deepcopy as dc
from Code.database_building import read_esm, read_mrio, add_supply_chains, esm_filters
from Code.soft_link import shock_capacity_demand
from Code.plot import plot_esm_data, plot_mat_demand
import plotly.express as px

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

#%%
plot_mat_demand(paths,user,mrio,mat_prices)

#%%
techs = ['PV power','Wind power','BEVs']
cap_d = esm_data['cap_d'].query("technologies in @techs")

bevs_share = {
    'LFP batteries': 0.4,
    'NCA batteries': 0.3,
    'NMC batteries': 0.3
    }

#%%
acts =  ['NCA batteries', 'NMC batteries', 'LFP batteries', 'Wind power', 'PV power']
mats =  ['Nickel','Copper','Lithium','Silicon','Neodymium','Dysprosium']

cap_d_dict = {
    'PV power': esm_data['cap_d'].query("technologies == 'PV power'"),
    'Wind power': esm_data['cap_d'].query("technologies == 'Wind power'"),
    'LFP batteries': esm_data['cap_d'].query("technologies == 'BEVs'"),
    'NCA batteries': esm_data['cap_d'].query("technologies == 'BEVs'"),
    'NMC batteries': esm_data['cap_d'].query("technologies == 'BEVs'"),
    }

for bat,share in bevs_share.items():
    cap_d_dict[bat]['value']*=share
    cap_d_dict[bat] = cap_d_dict[bat].replace('BEVs',bat)

for tech, cap in cap_d_dict.items():
    cap['Sensitivity'] =  'Avg'
    cap_min = dc(cap)
    cap_max = dc(cap)
    cap_min['Sensitivity'] = 'Min'
    cap_max['Sensitivity'] = 'Max'
    cap = pd.concat([cap,cap_min,cap_max],axis=0)
    
    cap_d_dict[tech] = cap

#%%
mat_recycled = {}

for act in acts:
    mat_recycled[act] = {}
    for scen in sorted(list(set(cap_d_dict[act]['scenarios']))):
        mat_recycled[act][scen] = {}
        for region in sorted(list(set(cap_d_dict[act]['regions']))):
            mat_recycled[act][scen][region] = {}
            for sens in ['Min','Avg','Max']:
                mat_recycled[act][scen][region][sens] = {}
                for mat in mats:
                    mat_recycled[act][scen][region][sens][mat] = cap_d_dict[act].query(f"scenarios=='{scen}' & regions=='{region}' & Sensitivity=='{sens}'")
                    mat_recycled[act][scen][region][sens][mat].set_index(["years"], inplace=True)
                    mat_recycled[act][scen][region][sens][mat] = mat_recycled[act][scen][region][sens][mat].loc[:,"value"].to_frame()
                    
                    u = mrio.get_data(matrices=['u'],scenarios= [f"{scen} - 2022 - {sens}"])[f"{scen} - 2022 - {sens}"][0]
                    
                    if region in ['China','Europe','United States']:
                        if act not in ['Wind power','PV power']:
                            mat_content_money = u.loc[(slice(None),slice(None),mat),(region,slice(None),act)].sum().sum()
                        elif act=="Wind power":
                           mat_content_money = u.loc[(slice(None),slice(None),mat),(region,slice(None),"Wind plants")].sum().sum()
                        elif act=="PV power":
                            mat_content_money = u.loc[(slice(None),slice(None),mat),(region,slice(None),"PV plants")].sum().sum()
                    else:
                        if act not in ['Wind power','PV power']:
                            mat_content_money = u.loc[(slice(None),slice(None),mat),('Rest of the World',slice(None),act)].sum().sum()
                        elif act=="Wind power":
                            mat_content_money = u.loc[(slice(None),slice(None),mat),('Rest of the World',slice(None),"Wind plants")].sum().sum()
                        elif act=="PV power":
                            mat_content_money = u.loc[(slice(None),slice(None),mat),('Rest of the World',slice(None),"PV plants")].sum().sum()

                    if region in ['China','Europe','United States']:
                        mat_content_cap = mat_content_money * tech_prices.loc[(region,sens),(act,slice(None))].values[0]
                        mat_content_weight = mat_content_cap / mat_prices.loc[(region,sens),mat]
                    else:
                        mat_content_cap = mat_content_money * tech_prices.loc[('Rest of the World',sens),(act,slice(None))].values[0]
                        mat_content_weight = mat_content_cap / mat_prices.loc[('Rest of the World',sens),mat]

                    mat_recycled[act][scen][region][sens][mat] *= mat_content_weight
                    
#%%
mat_recycled_df = pd.DataFrame()

for act in acts:
    for scen in sorted(list(set(cap_d_dict[act]['scenarios']))):
        for region in sorted(list(set(cap_d_dict[act]['regions']))):
            for sens in ['Min','Avg','Max']:
                for mat in mats:
                    df = dc(mat_recycled[act][scen][region][sens][mat])
                    df.reset_index(inplace=True)
                    df['scenarios'] = scen
                    df['technologies'] = act
                    df['regions'] = region
                    df['sensitivities'] = sens
                    df['materials'] = mat
                    
                    mat_recycled_df = pd.concat([mat_recycled_df,df],axis=0)

#%%
colors = px.colors.qualitative.Pastel

mat_recycled_df_tot = dc(mat_recycled_df) 
mat_recycled_df_tot.set_index(["scenarios","technologies","regions","sensitivities","materials",'years'],inplace=True)
mat_recycled_df_tot = mat_recycled_df_tot.groupby(level=["scenarios","regions","sensitivities","materials",'years'], axis=0).sum()
mat_recycled_df_tot = mat_recycled_df_tot.groupby(level=["scenarios","regions","sensitivities","materials",'years'])['value'].cumsum().to_frame()
mat_recycled_df_tot.reset_index(inplace=True)

for mat in mats:
    fig_rec = px.area(
        mat_recycled_df_tot.query(f"materials=='{mat}'"), 
        x='years',
        y='value',
        color='regions',
        facet_col='scenarios',
        facet_row='sensitivities',
        template = 'seaborn',
        color_discrete_sequence=colors,
        title=f'{mat} recycling by region [kton]'
        )
    fig_rec.update_layout(legend=dict(title=None),font_family='HelveticaNeue Light', font_size=16)   
    fig_rec.for_each_xaxis(lambda axis: axis.update(title=None))
    fig_rec.for_each_yaxis(lambda axis: axis.update(title=None))
    fig_rec.for_each_annotation(lambda a: a.update(text=a.text.split("=")[1]))
                            
    fig_rec.write_html(f"{paths.loc['esm plots',user]}\\Recycling_{mat}_by_region.html", auto_open=True)
                   
                
        
         
    