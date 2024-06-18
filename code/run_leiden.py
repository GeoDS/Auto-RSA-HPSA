import time
st = time.time()

import pandas as pd
import numpy as np
import igraph
import os
import math
pd.options.display.max_rows = 5

import matplotlib.pyplot as plt
import geopandas as gpd
from collections import Counter
from functions_leiden import *

parent_path = os.path.dirname(os.getcwd())
print(parent_path)

import argparse
parser = argparse.ArgumentParser(description='The record for cummunity detection algorithm')
parser.add_argument('-pu','--popu', help='pop urban limit',required=True)
parser.add_argument('-nu','--nctu',help='ct urban limit', required=True)
parser.add_argument('-pr','--popr', help='pop rural limit',required=True)
parser.add_argument('-nr','--nctr',help='ct rural limit', required=True)
parser.add_argument('-pop_perc','--pop_perc',help='urban rural population percentage limit', default = 0.5, required=False)
parser.add_argument('-o','--output', default= parent_path, required = False)
args = parser.parse_args()
 
## show values ##
pop_u = int(args.popu)
nct_u = int(args.nctu)
print ("pop urban: %s" % pop_u )
print ("nct urban: %s" % nct_u )

## show values ##
pop_r = int(args.popr)
nct_r = int(args.nctr)
print ("pop rural: %s" % pop_r )
print ("nct rural: %s" % nct_r )

t2 = 2
perc_limit = float(args.pop_perc)
print("the rural population limit is: {}".format(perc_limit))

data_path = os.getcwd() + "//data//"

if args.output not in os.listdir(os.getcwd()):
    os.mkdir(args.output)

leiden_folder = args.output + '/leiden/'
if 'leiden' not in os.listdir(args.output):
    os.mkdir(leiden_folder)

subfolder = str(pop_u) + '_' + str(nct_u) + '_' + str(pop_r) + '_' + str(nct_r) + "_t2_" + str(t2) + "_perc_" + str(perc_limit)
output = leiden_folder + subfolder
print(output)


if subfolder not in os.listdir(leiden_folder):
    os.mkdir(output)

os.chdir(output)


    


#############################
#start of the algorithm
#############################
#read the flow matrix for population all
flow = pd.read_csv(data_path + "wi_ct_flow_healthcare.csv")
flow = flow[flow['visitor_flows'] > 0]
flow = flow.rename(columns = {'ct_o':'geoid_o', 'ct_d':'geoid_d'})
ct_wi = list(set(list(flow['geoid_o'].unique()) + list(flow['geoid_d'].unique()))) ##get the unique values of CTs
#remove lakes with no population
for ct in [55025991702, 55025991703, 55079980000, 55009021100]:
    if ct in ct_wi:
        ct_wi.remove(ct)
n_ct = len(ct_wi)

flow_matrix = np.genfromtxt(data_path + 'health_wi_flowmx.csv', delimiter=',')

import random
random.seed(1234)

#build the graph
g = igraph.Graph.Adjacency((flow_matrix > 0).tolist())
g.es['weight'] = flow_matrix[flow_matrix.nonzero()]
g.vs['label'] = ct_wi  
g_un = g.as_undirected(combine_edges = "sum")

cluster_walk = g_un.community_leiden(weights = "weight",objective_function='modularity')#.as_clustering()
print("\n1st round Modularity", cluster_walk.modularity)

#prepare the shp for visualization
import pyproj
shp = data_path + "shp\\Wisconsin_censustract.shp"
map_df = gpd.read_file(shp)
map_df.to_crs(pyproj.CRS.from_epsg(4326), inplace=True)
map_df = map_df[['ct','pop','geometry']]
map_df['ct'] = map_df['ct'].astype(str).str[0:11]

#prepare the dataframe
iter_num = 1
clu_col = "clusterid" + str(iter_num)

result_df = pd.DataFrame(list(zip(ct_wi, cluster_walk.membership)), columns = ['ct',clu_col])
result_df['ct'] = result_df['ct'].astype(str)

#add population
result_df = pd.merge(result_df, map_df[['ct','pop']], on = ['ct'], how = 'left')


############
#add rural/urban
rural = pd.read_csv(data_path + "non-metro-counties-and-cts.csv", encoding='latin-1', dtype = {'CT':'str','CTY FIPS':'str'})
rural = rural[rural.ST == 'WI']

rural_cy = []
rural_ct = []
for i, row in rural.iterrows():
    if math.isnan(float(row['CT'])):
        rural_cy.append(row['CTY FIPS'])
    else:
        rural_ct.append(row['CT'])

result_df['county'] = result_df['ct'].astype(str).str[0:5]
result_df['rural'] = False

print(result_df.head())
print(result_df[result_df.ct.isin(rural_ct)])

result_df.loc[result_df.ct.isin(rural_ct),'rural'] = True
result_df.loc[result_df.county.isin(rural_cy),'rural'] = True
result_df['r_pop'] = result_df['pop']
result_df['u_pop'] = result_df['pop']
result_df.loc[result_df.rural == True, 'u_pop'] = 0
result_df.loc[result_df.rural == False, 'r_pop'] = 0

################################
#large list
large_list, startid = summary_clusters(result_df, map_df, clu_col, pop_u, nct_u, pop_r, nct_r, savefig = True, title = 'first_round', ratio_thre = perc_limit)
print('\n1st round large list:', large_list)
print("\nThe start id of next round is:", startid)

while len(large_list) > 0:
    iter_num += 1
    old_col = clu_col
    clu_col = "clusterid" + str(iter_num)
    get_sub_clusters(g_un, large_list, result_df, old_col, clu_col)
    result_df.loc[result_df[clu_col] == "", clu_col] = result_df[result_df[clu_col] == ""][old_col]
    large_list, startid = summary_clusters(result_df, map_df, clu_col, pop_u, nct_u, pop_r, nct_r, startid, ratio_thre = perc_limit)
    print(f'\n{str(iter_num)} round large list:', large_list)
    print(f"\nThe start id of next round is: {startid}")

summary_clusters(result_df, map_df, clu_col, pop_u, nct_u, pop_r, nct_r, plot = True, savefig = True, title = 'before_spatial', ratio_thre = perc_limit)

#******************************************
#spatial adjacency 
neighbors = pd.read_csv(data_path + "polygonNeighbors.csv")
neighbors = neighbors.drop(columns = "OBJECTID")
neighbors.columns = ["ct_source","ct_nb", "length", "node"]
neighbors['ct_source'] = neighbors['ct_source'].astype(str).str[0:11]
neighbors['ct_nb'] = neighbors['ct_nb'].astype(str).str[0:11]
t1 = 50
neighbors = neighbors[neighbors['length']>t1]
spatial_matrix = np.zeros((n_ct,n_ct))

for i,row in neighbors.iterrows():
    s = int(row['ct_source'])
    nb = int(row['ct_nb'])
    if (s in ct_wi) and (nb in ct_wi) and (s != nb):
        spatial_matrix[ct_wi.index(s), ct_wi.index(nb)] = row['length']

g_s = igraph.Graph.Adjacency((spatial_matrix > 0).tolist(), mode = "undirected")
g_s.es['weight'] = spatial_matrix[spatial_matrix.nonzero()]
g_s.vs['label'] = ct_wi  

#*********************************
#cut and merge
print("\ncut and merge")


#cut the clusters until there no cut
sep_c_total = []
new_c_total = []

old_col = clu_col
iter_num += 1
clu_col = "clusterid" + str(iter_num)

result_df[clu_col] = ""
sep_c, new_c, cut_flag = cut_separate_cluster(result_df, g_s, old_col, clu_col)

sep_c_total.extend(sep_c)
new_c_total.extend(new_c)

while cut_flag:
    nclu = sep_c + new_c
    sep_c, new_c, cut_flag = cut_separate_cluster(result_df, g_s, clu_col, clu_col, nclu)
    new_c_total.extend(new_c)

result_df.loc[result_df[clu_col] == "", clu_col] = result_df[result_df[clu_col] == ""][old_col]    
print("clusters that were cut:",sep_c_total)
print("new clusters:", new_c_total)

###############################
#merge
old_col = clu_col
iter_num += 1
clu_col = "clusterid" + str(iter_num)

result_df[clu_col] = result_df[old_col]
while True:    
    #find small clusters        
    count_df = result_df[[clu_col,'ct']].groupby(clu_col).count().reset_index().sort_values("ct")
    small_cluster = list(count_df[count_df.ct <= t2][clu_col])
    print("small clusters:",small_cluster)
    
    if len(small_cluster) == 0:
        print("\n")
        print("**********************************************")
        print("finish cut and merge!")
        break
    else:    
        print("**********************************************")
        print(f"there are clusters with size smaller than {t2}, will continue and merge them.")
        
        result_df[old_col] = result_df[clu_col] #update clusterid4 as the original one
        
        #map those small clusters
        summary_clusters(result_df[result_df[old_col].isin(small_cluster)], map_df, old_col, pop = False, how = "inner", ratio_thre = perc_limit)

        #enforce spatial continuity 
        merge_cluster(result_df, small_cluster,old_col, clu_col, neighbors, g_un)    
        summary_clusters(result_df, map_df, clu_col, plot = False, ratio_thre = perc_limit)

print("current modularity:", g_un.modularity(list(result_df[clu_col].astype(int)), weights = "weight"))

summary_clusters(result_df, map_df, clu_col, savefig = True, title = "final_result", ratio_thre = perc_limit)

#output the result
result_df.to_csv("leiden_cluster_result.csv", index = False)

et = time.time()

# get the execution time
elapsed_time = et - st
print('Execution time:', elapsed_time, 'seconds')
