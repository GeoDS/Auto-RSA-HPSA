import pandas as pd
import numpy as np
import igraph
import math

import matplotlib.pyplot as plt
from matplotlib import colors
import geopandas as gpd

from collections import Counter

import random
random.seed(1234)

def summary_clusters(result_df, map_df, col, pop_u = 30000, ct_u = 5, pop_r = 20000, ct_r = 1,startid = 0, plot = True, pop = True, how = "left", savefig = False, title = None, self_color = False, legend = 'HPSA',ratio_thre = 0.5):
    result_df[col] = result_df[col].astype(str)
    result_df['ct'] = result_df['ct'].astype(str)
    df = pd.merge(map_df[['ct','geometry']], result_df, on = 'ct', how = how)
    n = df[col].nunique()
    
    if plot == True:
        fig, ax = plt.subplots(1, 1, figsize = (14,10))
        missing_kwds = None
        if self_color == False:
            new_cmap = rand_cmap(100, type='bright', first_color_black=True, last_color_black=False)
            df.plot(column = col,cmap = new_cmap,ax = ax, categorical=True , legend=True,  legend_kwds={'loc':'upper left','bbox_to_anchor':(1.02, 1), 'title': 'Cluster ID', 'ncol': n//30 + 1}, alpha = 0.7, edgecolor = "lightgray",missing_kwds = missing_kwds)     
        else:
            cmap = colors.ListedColormap(['lightgray', 'red'])
            df.plot(column = col,cmap = cmap,ax = ax, categorical=True , legend=True,  legend_kwds={'loc':'upper left','bbox_to_anchor':(1.02, 1), 'title': legend, 'ncol': 1}, alpha = 0.7, edgecolor = "lightgray", missing_kwds = missing_kwds) 
        if savefig == True:
            plt.savefig(title + '.jpg', dpi = 300)
            
    if pop == True:
        pop_df = df.groupby(col).agg({'pop':['sum'],'ct':['count'],'r_pop':['sum'],'u_pop':['sum']}).reset_index()
        pop_df.columns = [col, 'pop','ct_count','r_pop','u_pop']
        ####add the two limit as columns
        pop_df['poplimit'] = pop_u
        pop_df['ctlimit'] = ct_u
        ####decide r_pop/total_pop ratio
        pop_df['r_ratio'] = pop_df['r_pop']/(pop_df['pop'])
        pop_df.loc[pop_df['r_ratio']>ratio_thre,'poplimit'] = pop_r
        pop_df.loc[pop_df['r_ratio']>ratio_thre,'ctlimit'] = ct_r
        
        #####
        pop_df['above_min'] = pop_df['pop'] > pop_df['poplimit']
        pop_df['needs_split'] = (pop_df['above_min'] == True)&(pop_df['ct_count']>pop_df['ctlimit'])
        print(pop_df.sort_values("pop"))
        
    if pop == True:
        list_all = list(pop_df[pop_df['needs_split'] == True][col])
        list_res = [i for i in list_all if int(i) >= startid]
        max_id = max(pop_df[col].astype(int))
        return list_res, max_id + 1

    
def get_sub_clusters(g_un, large_list, result_df, old_column, new_column): #generate subgraph from the original undirected graph
    result_df[new_column] = ""
    
    max_id = max(result_df[old_column].astype(int))
    for c in large_list:
        print(c)
        g = g_un.induced_subgraph(list(result_df[result_df[old_column] == c].index))
        
        vcount = g.vcount()
        if vcount < 50:
            step = 2
        elif vcount < 100:
            step = 3
        else:
            step = 4
        
        g_cluster = g.community_multilevel(weights = "weight")#.as_clustering()
        
        print("Cluster", c, "has",vcount, "vertices , new modularity:", g_cluster.modularity)
        
        if len(Counter(g_cluster.membership)) == 1 or g_cluster.modularity < 0:
            print(Counter(g_cluster.membership))
            print(g_cluster.modularity)
            print("The cluster is not split and will be the same.")
        else:
            for i in range(vcount):
                result_df.loc[result_df['ct'] == str(g.vs[i].attributes()['label']), new_column] = g_cluster.membership[i] + max_id + 1
            print(Counter(g_cluster.membership))

            max_id += max(g_cluster.membership) + 1      

def cut_separate_cluster(result_df, g_s, old_col, new_col, nclu = None):
    print('start')
    cut_flag = False
    max_c = max(result_df[result_df[old_col] != ""][old_col].astype(int))
    print("the current max cluster is: ")
    print(max_c)
    ls = []
    new_c = []
    if nclu is None:
        nclu = list(result_df[old_col].unique())
    for c in nclu:
        try:
            g_c = g_s.induced_subgraph(list(result_df[result_df[old_col] == c].index))
            if g_c.vcount() <= 1: #ignore the clusters that have fewer than 3 CTs
                continue
            cut = g_c.mincut()
            if cut.value < 1:
                print("Find spatial non-contiguous cluster: ", c)
                cut_flag = True
                ls.append(c)
                for partition in cut.partition:
                    print("generate new cluster:", max_c+1)
                    for v in partition:
                        result_df.loc[result_df["ct"] == str(g_c.vs[v].attributes()['label']), new_col] = str(max_c + 1)
                    new_c.append(str(max_c + 1))
                    max_c += 1
        except:
            print(c)
            print(g_c.vcount())
    
    return ls, new_c, cut_flag


def merge_cluster(result_df, small_cluster, old_col, new_col, neighbors, g_un):
    new_cluster_ls = []
    for c in small_cluster:
        print("current cluster: ",c)
        #get all cts and the neighbor cts
        sub_ct = list(result_df[result_df[new_col] == c].ct)
        if len(sub_ct) == 0:
            continue
        nbs = []
        for ct in sub_ct:
            nbs += list(neighbors[neighbors['ct_source'] == ct].ct_nb)
        nbs = list(set(nbs)-set(sub_ct))
        nbs_clu = list(result_df[result_df['ct'].isin(nbs)][new_col].unique())
        
        print("cts under it: ",sub_ct)
        print("neighbor cts: ",nbs)
        print("cluster ids of neighbors",nbs_clu)
        
        #orphan
        if len(nbs) == 0:
            print("find one ct with no neighbors.")
            print(sub_ct)
        
        #enclosed, merge it directly with the neighbor
        if len(nbs) == 1:
            change_cluster(sub_ct, nbs_clu[0], result_df, new_col)
        
        #enclaved
        if len(nbs) > 1:           
            m_ls = []
            for c in nbs_clu:
                change_cluster(sub_ct, c, result_df, new_col)
                m_ls.append(g_un.modularity(list(result_df[new_col].astype(int)), weights = "weight"))
            print("new modularity list: ", m_ls)
            
            #move the the one obtaining max modularity, but not over the population limit
            while True:
                new_c = nbs_clu[m_ls.index(max(m_ls))]
                new_cluster_ls.append(new_c)
                change_cluster(sub_ct, new_c,result_df, new_col) 
            
                if result_df[result_df[new_col] == new_c]['pop'].sum() < 250000:
                    break
                elif len(nbs_clu) > 1:
                    nbs_clu.remove(new_c)
                    m_ls.remove(max(m_ls))
                    continue
                else:
                    print("there is a cluster with pop larger than 250000.")
                    break

            print(result_df[result_df['ct'].isin(sub_ct)])
            #also control population
        
def change_cluster(cts, c, result_df, col): #ct1: to be changed, c: clusterid
    for ct1 in cts:
        result_df.loc[result_df.ct == ct1, col] = c        
        

def rand_cmap(nlabels, type='bright', first_color_black=True, last_color_black=False, verbose=False):
    """
    Creates a random colormap to be used together with matplotlib. Useful for segmentation tasks
    :param nlabels: Number of labels (size of colormap)
    :param type: 'bright' for strong colors, 'soft' for pastel colors
    :param first_color_black: Option to use first color as black, True or False
    :param last_color_black: Option to use last color as black, True or False
    :param verbose: Prints the number of labels and shows the colormap. True or False
    :return: colormap for matplotlib
    """
    from matplotlib.colors import LinearSegmentedColormap
    import colorsys
    import numpy as np


    if type not in ('bright', 'soft'):
        print ('Please choose "bright" or "soft" for type')
        return

    if verbose:
        print('Number of labels: ' + str(nlabels))

    # Generate color map for bright colors, based on hsv
    np.random.seed(20210817)
    if type == 'bright':
        randHSVcolors = [(np.random.uniform(low=0.0, high=1),
                          np.random.uniform(low=0.2, high=1),
                          np.random.uniform(low=0.9, high=1)) for i in range(nlabels)]

        # Convert HSV list to RGB
        randRGBcolors = []
        for HSVcolor in randHSVcolors:
            randRGBcolors.append(colorsys.hsv_to_rgb(HSVcolor[0], HSVcolor[1], HSVcolor[2]))

        if first_color_black:
            randRGBcolors[0] = [0, 0, 0]

        if last_color_black:
            randRGBcolors[-1] = [0, 0, 0]

        random_colormap = LinearSegmentedColormap.from_list('new_map', randRGBcolors, N=nlabels)
        
    return random_colormap

def estimate_HPSA(result_df, fte):
    clu_col = result_df.columns[-1]
    cols = ['ct','SUM_fte']
    fte = fte[cols]
    
    cluster_df = result_df[['ct',clu_col,'pop']].merge(fte, on = ['ct']).groupby(clu_col).sum().reset_index()
    cluster_df['ct'] = cluster_df['ct'].astype(str)
    cluster_df['ratio'] = cluster_df['pop']/cluster_df['SUM_fte']
    
    cluster_df['HPSA'] = False
    for i, row in cluster_df.iterrows():
        if row['ratio'] == math.inf and row['pop'] > 500:
            cluster_df.loc[i, 'HPSA'] = True
        if row['ratio'] != math.inf and row['ratio'] > 3500:
            cluster_df.loc[i, 'HPSA'] = True
    print(f"There are in total {len(cluster_df)} clusters.")
    print(f"The estimated HPSA is {len(cluster_df[cluster_df['HPSA'] == True])}")
    
    return cluster_df