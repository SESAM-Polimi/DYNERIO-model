# -*- coding: utf-8 -*-
"""
Created on Mon May  8 11:31:23 2023

@author: loren
"""

import pandas as pd
import os
import openpyxl
import mario

file_columns = {
    'cap_n': ['scenarios','regions','technologies','years','value'],
    'cap_o': ['scenarios','regions','technologies','years','value'],
    'cap_d': ['scenarios','regions','technologies','years','value'],
    'xy': ['scenarios','regions','technologies','years','value'],
    }

esm_filters = {
    'regions': 'all',
    'scenarios': [
        # 'BAS',
        'BLS',
        'FLS'
        ],
    'technologies': [
        't.bev',
        't.elect_pv',
        't.elect_wind',
        't.elect_coal',
        't.elect_coal_ccs',
        't.elect_oil',
        't.elect_oil_ccs',
        't.elect_natgas',
        't.elect_natgas_ccs',
        't.elect_uranium',
        't.elect_geothermal',
        't.elect_hydro',
        't.elect_waste_biomass',
        't.elect_waste_biomass_ccs',
        ],
    'years': [y for y in range(2022,2051,2)],    
    }

new_commodities = [
    'Photovoltaic plants',
    'Photovoltaic modules',
    'Mono-Si and poli-Si cells',
    'Raw silicon',
    'Onshore wind plants',
    'DFIG generators',
    'Offshore wind plants',
    'PMG generators',
    'Neodymium',
    'Dysprosium',
    'Wind plants',
    'LFP batteries',
    'NMC batteries',
    'NCA batteries',
    'BEV batteries',    
    ]

new_activities = [
    'Production of photovoltaic plants',
    'Production of photovoltaic modules',
    'Production of mono-Si and poli-Si cells',
    'Production of onshore wind plants',
    'Production of DFIG generators',
    'Production of offshore wind plants',
    'Production of PMG generators',
    'Production of wind plants',
    'Manufacture of LFP batteries',
    'Manufacture of NCA batteries',
    'Manufacture of NMC batteries',
    'Manufacture of BEV batteries',
    ]   


def read_esm(paths,user,filters):
    # read esm results
    esm_data = {file: pd.read_csv(os.path.join(paths.loc['esm data',user],f"{file}.csv")) for file in file_columns}
    for file,columns in file_columns.items():
        esm_data[file].columns = columns
        
    for file,data in esm_data.items():
        for s,f in filters.items():
            if f != 'all':
                data = data.query(f"{s} == {f}")
        esm_data[file] = data
        
    # map sets
    map_set_file = openpyxl.load_workbook(paths.loc['esm sets',user])
    map_set = {sheet: pd.read_excel(paths.loc['esm sets',user], sheet_name=sheet, index_col=[0]) for sheet in map_set_file.sheetnames}
    
    for file,data in esm_data.items():
        for s,m in map_set.items():
            for i in m.index:
                data.replace(i,m.loc[i,'NAME'],inplace=True)
        data = data.sort_values(file_columns[file], ascending=[True if i!='regions' else False for i in file_columns[file]])  
        esm_data[file] = data
    
    return esm_data


def read_mrio(database,paths,user,mode='flows',aggregation=False):
    
    #Read database
    db_path = f"{paths.loc[f'mrio db {database}',user]}\\{mode}"
    mrio = mario.parse_from_txt(path=db_path, table='SUT', mode=mode)
    
    # Aggregate in case
    if aggregation==True:
        aggr_path = paths.loc[f"mrio aggr {database}",user]
        mrio.aggregate(aggr_path)
    
    return mrio


def add_supply_chains(mrio,path,item):
    
    if item=='Commodity':
        mrio.add_sectors(io=path, new_sectors=new_commodities, item=item, regions=mrio.get_index('Region'), inplace=True)
    else:
        mrio.add_sectors(io=path, new_sectors=new_activities, item=item, regions=mrio.get_index('Region'), inplace=True)
    
    return mrio
