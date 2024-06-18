# Auto-RSA-HPSA
Automatic Delineation of Rational Service Areas and Health Professional Shortage Areas in GIS based on Human Movements and Health Resources

### Abstract

How people travel to receive health services is essential for understanding healthcare shortages. The Rational Service Areas (RSAs) are defined to represent local healthcare markets and used as the basic units to evaluate whether people have access to health resources. Therefore, finding an appropriate way to develop RSAs is important for understanding the utilization of health resources and supporting accurate resource allocation to the health professional shortage areas (HPSAs). Existing RSAs are usually developed based on the local knowledge of public health needs and are created through time-intensive manual work by health service officials. In this research, a travel data-driven and spatially-constrained community detection method based on human mobility flow is proposed to automate the process of establishing the statewide RSAs and further identifying HPSAs based on healthcare criteria in a GIS software. The proposed method considers the difference between rural and urban populations by assigning different parameters and delineates RSAs with the goal of reducing health resource inequalities faced by rural areas. Using the data in the State of Wisconsin, our experiment shows that the proposed RSA delineation method outperforms other baselines including the traditional Dartmouth method in the aspects of RSA compactness, region size balances, and health shortage scores. Furthermore, the whole process of delineating RSAs and identifying HPSAs is automated using Python toolboxes in ArcGIS to support future analyses and practices in a timely and repeatable manner. 

![workflow](https://github.com/GeoDS/Auto-RSA-HPSA/assets/46972608/dcb740f2-50b1-45a8-a6ef-b7619feaf2f7)

### References
If you find our code or ideas useful for your research, please cite our paper:


### Implementation

run the algorithm

```
python run_walktrap.py -pu 40000 -nu 10 -pr 20000 -nr 3 -o results >walktrap_out.txt
python run_leiden.py -pu 70000 -nu 18 -pr 40000 -nr 6 -o results >leiden_out.txt
python run_louvain.py -pu 70000 -nu 18 -pr 40000 -nr 6 -o results >louvain_out.txt
```


