# Facilitated InSAR analysis of Sentinel-1 remote sensing data
Python-based automation of InSAR processing chain

###### By: Alireza Taheri Dehkordi
-----------------------------------
For installation:

#### conda env create -f environment.yml
#### conda activate DefoEye
-----------------------------------


python main.py --base_path /media/atdehkordi/SSD8TB/Datadownload_PyGMTSAR/Skane/ --work_path /media/atdehkordi/SSD8TB/DefoEye/Skane2017_2025/ --temporal_baseline 37 --spatial_baseline 500 --filter_intf_pairs True --TH_number_of_connections 4 --filter_wavelength_value 200 --range_dec_value 20 --azimuth_dec_value 5 --n_jobs_for_intf 10 --n_jobs_for_merging 10 --n_jobs_for_unwrapping 5
