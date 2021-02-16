''' Outlier detection functions
'''

from itertools import groupby
import pandas as pd
from sklearn.decomposition import PCA
from scipy.cluster.hierarchy import dendrogram, linkage,fcluster
import matplotlib.pyplot as plt
import numpy as np
import ray
from ..masks import mask_create

def outlier_dect(actors,config_dict):

    print("Detecting outlier images...")
    samples  = ray.get([a.do.remote(subsample,config_dict['outlier']) for a in actors])

    # Center, scale and fit PCA transform
    X = np.concatenate(samples).astype(np.float32)
    X /=X.mean(axis=1)[:,np.newaxis]
    X /=X.std(axis=1,ddof=1)[:,np.newaxis]

    pca = PCA(n_components=5)
    pca.fit(X)
    pca_df=  pd.DataFrame(pca.transform(X))

    line_names=  ray.get([a.do.remote(lambda x:x.base_name) for a in actors])

    lines = []
    for i,s in enumerate(samples):
        lines+= [i for x in s]
    pca_df['line'] = lines

    mean = pca_df.groupby(by ='line').mean()

    linked = linkage(mean, 'ward')

    if config_dict['outlier']['threshold'] == 'auto':
        threshold =0.7* max(linked[:,2])
    else:
        threshold = config_dict['outlier']['threshold']

    if config_dict['outlier']['dendrogram']:
        fig = plt.figure(figsize=(4, 4))
        ax = fig.add_subplot(111)
        _ =dendrogram(linked,
                    orientation='left',
                    labels=line_names,
                    distance_sort='descending',
                    show_leaf_counts=False,ax=ax)
        ax.vlines(threshold,ax.get_ylim()[0],ax.get_ylim()[1],color='r',ls ='--')
        plt.savefig("%soutlier_dendrogram.png" % config_dict['export']['output_dir'],
                    bbox_inches='tight', dpi = 300)

    clusters = fcluster(linked,threshold,criterion='distance')
    pairs = [[a,b] for (a,b) in zip(clusters,line_names)]
    pairs.sort(key =lambda x :x[0])

    for key,group in groupby(pairs,key =lambda x :x[0]):
        print('Group: %s' % key)
        for line in group:
            print(line[1])

    # This should return a binary list with
    return clusters

def subsample(hy_obj,outlier_dict):
    ''' Subsample pixels for PCA'''

    print("Subsampling %s" % hy_obj.base_name)
    hy_obj.gen_mask(mask_create,'outlier',outlier_dict['mask'])
    idx = np.array(np.where(hy_obj.mask['outlier'])).T
    idxRand= idx[np.random.choice(range(len(idx)),
                                  int(len(idx)*(1-outlier_dict['sample_perc'])),
                                  replace = False)].T
    hy_obj.mask['outlier'][idxRand[0],idxRand[1]] = False
    X = []
    for band_num,band in enumerate(hy_obj.bad_bands):
        if ~band:
            X.append(hy_obj.get_band(band_num,mask='outlier'))
    return  np.array(X).T
