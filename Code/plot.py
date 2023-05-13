# -*- coding: utf-8 -*-
"""
Created on Mon May  8 11:33:25 2023

@author: loren
"""

import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import pandas as pd

raw_materials = {
    'Copper': {'rename': 'Copper', 'price':1},
    'Lithium': {'rename': 'Lithium', 'price':1},
    'Nickel': {'rename': 'Nickel', 'price':1},
    'Silicon': {'rename': 'Silicon', 'price':1},
    'Neodymium': {'rename': 'Neodymium', 'price':1},
    'Dysprosium': {'rename': 'Dysprosium', 'price':1},
    }

activities = ['PV plants','Onshore wind plants','Offshore wind plants','LFP batteries','NCA batteries','NMC batteries']

colors = px.colors.qualitative.Pastel
template = "seaborn"
font = "HelveticaNeue Light"
size = 16
auto_open = True

def plot_esm_data(paths, user, esm_data):

    # create sets
    sets = {s: sorted(list(set(esm_data['cap_n'].loc[:,s]))) for s in esm_data['cap_n'].columns if s!='value'}

    # plot esm    
    for file,data in esm_data.items():
        for tech in sets['technologies']:
            plot = data.query(f"technologies == '{tech}'")       
            fig = px.bar(plot, x='years', y='value', color='regions', facet_col='scenarios', color_discrete_sequence=colors, template=template, title=f"{file}_{tech}")
            fig.update_layout(legend=dict(title=None,traceorder='reversed'), font_family=font, font_size=size)   
            fig.for_each_xaxis(lambda axis: axis.update(title=None))
            fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[1]))
            fig.write_html(f"{paths.loc['esm plots',user]}\\{file}_{tech}.html", auto_open=auto_open)
        

def plot_mat_demand(paths, user, mrio, prices):
    
    materials_extraction = pd.DataFrame()
    sN = slice(None)
    years = sorted(set([int(i.split(' - ')[1]) for i in mrio.scenarios if i!='baseline']))
        
    for scem in mrio.scenarios:
        if scem!='baseline':
            year = int(scem.split(' - ')[1])
            scenario = scem.split(' - ')[0]
            price = scem.split(' - ')[2]
            U = mrio.get_data(matrices=['U'], scenarios=[scem])[scem][0].loc[(sN,'Commodity',list(raw_materials.keys())),:]
            U = U.droplevel(1,axis=0)
            U = U.droplevel(1,axis=1)
            U = U.stack([0,1]).to_frame()
            U.columns = ['value']
            U.index.names = ['regions from','commodities','regions to','activities']
            U.loc[:,'scenarios'] = scenario
            U.loc[:,'years'] = year
            U.loc[:,'price'] = price
            
            for x in U.index:
                U.loc[x,'value'] /= prices.loc[(x[0],price),x[1]]
            U.reset_index(inplace=True)
            materials_extraction = pd.concat([materials_extraction,U], axis=0)
    
        
    materials_extraction.set_index([i for i in materials_extraction.columns if i!="value"], inplace=True)
    
    # materials_extraction = materials_extraction.sort_index(level='years')
    # materials_extraction['value_cum'] = materials_extraction.groupby(level=['years'])['value'].cumsum()
    # materials_extraction.reset_index(inplace=True)
    
    # materials_extraction.set_index(["regions from","commodities","regions to","activities","scenarios","years","price"], inplace=True)    
    materials_extraction = materials_extraction.loc[:,'value'].to_frame()
    materials_extraction = materials_extraction.unstack("price")
    materials_extraction.columns = materials_extraction.columns.get_level_values(-1)
    materials_extraction.reset_index(inplace=True)
    
    mat_total = materials_extraction.set_index(["regions from","commodities","regions to","activities","scenarios","years"])
    mat_total = mat_total.groupby(["commodities","scenarios","years"]).sum()
    mat_total.reset_index(inplace=True)
    
    num_subplots = len(list(raw_materials.keys()))
    num_rows = int(num_subplots ** 0.5)  # Square root of num_subplots
    num_cols = (num_subplots + num_rows - 1) // num_rows

    for scenario in sorted(list(set(mat_total['scenarios'].to_list()))):
        fig_total = make_subplots(rows=num_rows, cols=num_cols, subplot_titles=list(raw_materials.keys()), shared_xaxes=True)
        counter = 0
        for material in raw_materials:
            df = mat_total.query(f"commodities=='{material}' & scenarios=='{scenario}'")
            fig_total.add_trace(go.Scatter(
                name='Avg',
                x=df['years'],
                y=df['Avg']/1e3,
                mode='lines',
                line=dict(color='rgb(31, 119, 180)'),
                showlegend=False,
                ),
                row=(counter//num_cols) + 1, 
                col=(counter % num_cols) + 1
                )
    
            fig_total.add_trace(go.Scatter(
                name='Upper',
                x=df['years'],
                y=df['Max']/1e3,
                mode='lines',
                marker=dict(color="#444"),
                line=dict(width=0),
                showlegend=False,
                ),
                row=(counter//num_cols) + 1, 
                col=(counter % num_cols) + 1
                )
        
            fig_total.add_trace(go.Scatter(
                name='Lower',
                x=df['years'],
                y=df['Min']/1e3,
                mode='lines',
                marker=dict(color="#444"),
                line=dict(width=0),
                fillcolor='rgba(68, 68, 68, 0.3)',
                fill='tonexty',
                showlegend=False,
                ),
                row=(counter//num_cols) + 1, 
                col=(counter % num_cols) + 1
                )
            
            counter+=1
    
        fig_total.update_layout(font_family=font, font_size=size, template=template, title=f"Total extraction of raw materials [ton] - {scenario} scenario")   
        fig_total.for_each_xaxis(lambda axis: axis.update(title=None))
        fig_total.for_each_yaxis(lambda axis: axis.update(title=None))
        fig_total.write_html(f"{paths.loc['mrio plots',user]}\\Total extraction ({scenario}).html", auto_open=auto_open)
    
    
    for material in raw_materials:
        mat_by_prod_region   = materials_extraction.set_index(["regions from","commodities","regions to","activities","scenarios","years"]).groupby(level=["regions from","commodities","scenarios","years"]).sum().loc[(sN,material,sN,sN),:]/1e6
        
        import copy 
        mat_by_cons_activity = copy.deepcopy(materials_extraction)
        other_activities = sorted(list(set(materials_extraction['activities'].to_list())))
        for a in activities:
            other_activities.remove(a)
        for oa in other_activities:
            mat_by_cons_activity.replace(oa,"Other",inplace=True)
        mat_by_cons_activity.set_index(["regions from","commodities","regions to","activities","scenarios","years"], inplace=True)
        mat_by_cons_activity = mat_by_cons_activity.groupby(["regions from","commodities","regions to","activities","scenarios","years"]).sum()
        mat_by_cons_activity.reset_index(inplace=True)
        mat_by_cons_activity = mat_by_cons_activity.set_index(["regions from","commodities","regions to","activities","scenarios","years"]).groupby(level=["commodities","activities","scenarios","years"]).sum().loc[(material,sN,sN,sN),:]/1e6        
        mat_by_cons_activity = mat_by_cons_activity.sort_values(["activities"], ascending=[True])
        mat_by_cons_region   = materials_extraction.set_index(["regions from","commodities","regions to","activities","scenarios","years"]).groupby(level=["commodities","regions to","scenarios","years"]).sum().loc[(material,sN,sN,sN),:]/1e6
        
        mat_by_prod_region.reset_index(inplace=True)
        mat_by_cons_activity.reset_index(inplace=True)
        mat_by_cons_region.reset_index(inplace=True)
        
        fig_prod_reg = px.area(mat_by_prod_region, x='years',y='Avg',color='regions from',facet_col='scenarios',template = template,color_discrete_sequence=colors,title=f'{material} extraction by region [kton]')
        fig_prod_reg.update_layout(legend=dict(title=None,traceorder='reversed'), font_family=font, font_size=size)   
        fig_prod_reg.for_each_xaxis(lambda axis: axis.update(title=None))
        fig_prod_reg.for_each_yaxis(lambda axis: axis.update(title=None))
        fig_prod_reg.for_each_annotation(lambda a: a.update(text=a.text.split("=")[1]))
        fig_prod_reg.write_html(f"{paths.loc['mrio plots',user]}\\{material} extraction by region (Avg).html", auto_open=auto_open)

        fig_cons_reg = px.area(mat_by_cons_region, x='years',y='Avg',color='regions to',facet_col='scenarios',template = template,color_discrete_sequence=colors,title=f'{material} demand by region [kton]')
        fig_cons_reg.update_layout(legend=dict(title=None,traceorder='reversed'), font_family=font, font_size=size)   
        fig_cons_reg.for_each_xaxis(lambda axis: axis.update(title=None))
        fig_cons_reg.for_each_yaxis(lambda axis: axis.update(title=None))
        fig_cons_reg.for_each_annotation(lambda a: a.update(text=a.text.split("=")[1]))
        fig_cons_reg.write_html(f"{paths.loc['mrio plots',user]}\\{material} demand by region (Avg).html", auto_open=auto_open)

        fig_cons_act = px.area(mat_by_cons_activity, x='years',y='Avg',color='activities',facet_col='scenarios',template = template,color_discrete_sequence=colors,title=f'{material} demand by technology [kton]')
        fig_cons_act.update_layout(legend=dict(title=None,traceorder='reversed'), font_family=font, font_size=size)   
        fig_cons_act.for_each_xaxis(lambda axis: axis.update(title=None))
        fig_cons_act.for_each_yaxis(lambda axis: axis.update(title=None))
        fig_cons_act.for_each_annotation(lambda a: a.update(text=a.text.split("=")[1]))
        fig_cons_act.write_html(f"{paths.loc['mrio plots',user]}\\{material} demand by technology (Avg).html", auto_open=auto_open)
