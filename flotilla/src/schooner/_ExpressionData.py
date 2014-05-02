from _Data import Data
import scipy
from scipy import sparse
import pandas as pd
from collections import defaultdict

import seaborn
from sklearn.preprocessing import StandardScaler

from flotilla.src.submarine import PCA_viz

from ..frigate import dropna_mean
from ..skiff import link_to_list
from ...project.project_params import min_cells, _default_group_id

seaborn.set_context('paper')


class ExpressionData(Data):
    _default_reducer_args = Data._default_reducer_args
    _default_group_id = _default_group_id
    ###
    # RAM HOGS:

    gene_lists = {}
    samplewise_reduction = defaultdict(dict)
    featurewise_reduction = defaultdict(dict)
    #
    ###

    def __init__(self, rpkm, sample_descriptors,
                 gene_descriptors = None,
                 var_cut=0.2, expr_cut=0.1, load_cargo=True, rename=True,
    ):

        self.rpkm = rpkm
        self.sparse_rpkm = rpkm[rpkm > expr_cut]
        rpkm_variant = pd.Index([i for i, j in (rpkm.var().dropna() > var_cut).iteritems() if j])
        self.gene_lists['variant'] = rpkm_variant
        self.gene_lists['default'] = self.gene_lists['variant']

        self.sample_descriptors = sample_descriptors
        self.gene_descriptors = gene_descriptors
        if load_cargo:
            from ..cargo import gene_lists, go
            self.gene_lists.update(gene_lists)
            self.gene_lists['default'] = self.gene_lists['confident_rbps']
            if rename:
                self.set_naming_fun(lambda x: go.geneNames(x))
        naming_fun = self.get_naming_fun()
        self.gene_lists.update({'all_genes':pd.Series(map(naming_fun, self.rpkm.columns),
                                                           index = self.rpkm.columns)})

    def get_reduced(self, gene_list_name='default',
                    group_id=_default_group_id, min_cells=min_cells,
                    reducer=PCA_viz,
                    featurewise=False,
                    reducer_args=_default_reducer_args,
                    standardize=True):
        if featurewise:
            rdc_dict = self.featurewise_reduction
        else:
            rdc_dict = self.samplewise_reduction
        try:
            return rdc_dict[gene_list_name][group_id]
        except:

            if gene_list_name not in self.gene_lists:
                self.gene_lists[gene_list_name] = link_to_list(gene_list_name)

            gene_list = self.gene_lists[gene_list_name]
            subset = self.sparse_rpkm.ix[self.sample_descriptors[group_id], gene_list.index]
            frequent = pd.Index([i for i, j in (subset.count() > min_cells).iteritems() if j])
            subset = subset[frequent]
            #fill na with mean for each event
            means = subset.apply(dropna_mean, axis=0)
            mf_subset = subset.fillna(means, ).fillna(0)

            #whiten, mean-center
            if standardize:
                data = StandardScaler().fit_transform(mf_subset)
            else:
                data = mf_subset
            naming_fun = self.get_naming_fun()
            ss = pd.DataFrame(data, index = mf_subset.index,
                              columns = mf_subset.columns).rename_axis(naming_fun, 1)

            #compute pca
            if featurewise:
                ss = ss.T
            rdc_obj = reducer(ss, **reducer_args)
            rdc_obj.means = means.rename_axis(naming_fun) #always the mean of input features... i.e. featurewise doesn't change this.


            #add mean gene_expression
            rdc_dict[gene_list_name][group_id] = rdc_obj
        return rdc_dict[gene_list_name][group_id]