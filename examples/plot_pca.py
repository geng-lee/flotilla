"""
Visualize principal component analysis dimensionality reduction
================================================================

"""
import flotilla
study = flotilla.embark(flotilla._shalek2013)
study.plot_pca(plot_violins=False)