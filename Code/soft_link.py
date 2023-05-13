# -*- coding: utf-8 -*-
"""
Created on Mon May  8 17:10:04 2023

@author: loren
"""

esm_mrio_map = {
    'techs-comms': {
        'PV power': {
            'Commodity': ['Photovoltaic plants'],
            'Unit conv': 1e12,
            },
        'Wind power': {
            'Commodity': ['Wind plants'],
            'Unit conv': 1e12,
            },
        'BEVs': {
            'Commodity': ['LFP batteries','NCA batteries','NMC batteries'],
            'Unit conv': 1e6*0.3, #☺ assuming cost of battery is 0.35 of the total cost of the car
            }
        },
    'regions': {
        'Rest of the World': ['Australia','India','Africa','Middle East','Asia & Pacific']}
    }


new_technologies = [
    'PV power',
    'Wind power',
    'BEVs',
    ]


def aggregate_regions_esm(data):
    
    for new_region,regions_to_aggregate in esm_mrio_map['regions'].items():
        for i in data.index:
            if data.loc[i,'regions'] in regions_to_aggregate:
                data.loc[i,'new_regions'] = new_region
            else:
                data.loc[i,'new_regions'] = data.loc[i,'regions']
    
    data.drop('regions',axis=1,inplace=True)
    data.rename(columns={"new_regions":"regions"},inplace=True)
    data = data.groupby([col for col in data.columns if col!="value"], axis=0).sum()
    data.reset_index(inplace=True)
    
    return data
        

def shock_capacity_demand(mrio, cap, prices):

    print(f"Implementing new capacity demand in mrio")
    
    # Aggregate regions
    cap = aggregate_regions_esm(cap)
    
    # Create sets
    sets = {s: sorted(list(set(cap.loc[:,s]))) for s in cap.columns if s!='value'}
    sets['price sentitivity'] = sorted(list(set(prices.index.get_level_values(1))))
    
    # Get scemarios
    sets['scemarios'] = []
    for s in sets['scenarios']:
        for y in sets['years']:
            for p in sets['price sentitivity']:
                scemario = f"{s} - {y} - {p}"
                mrio.clone_scenario(scenario='baseline', name=scemario)
                sets['scemarios'] += [scemario]
            
    # Implement new capacity demand shocks
    for scem in sets['scemarios']:
        year = int(scem.split(' - ')[1])
        scenario = scem.split(' - ')[0]
        price = scem.split(' - ')[2]
        Y_new = mrio.matrices[scem]['Y']
        
        for tech in new_technologies:
            for com in esm_mrio_map['techs-comms'][tech]['Commodity']:  
                for region in mrio.get_index('Region'): 
                    if tech == 'BEVs':
                        conv = prices.loc[(region,price),(com,slice(None))][0]
                    else:
                        conv = prices.loc[(region,price),(tech,slice(None))][0]
                    new_capacity = cap.query(f"scenarios=='{scenario}' & regions=='{region}' & technologies=='{tech}' & years=={year}")['value'].iloc[0]
                    Y_new.loc[(region,'Commodity',com),(region,'Consumption category','Final demand')] = new_capacity*conv*esm_mrio_map['techs-comms'][tech]['Unit conv']
        
        mrio.update_scenarios(scenario=scem, Y=Y_new)
        mrio.reset_to_coefficients(scenario=scem)
        print(f"{scem} implemented")
    
    return mrio



    
    