import os
import rasterio
import numpy as np
import subprocess
from rasterio.enums import Resampling
from scipy.signal import convolve2d
import shutil
from datetime import datetime, timedelta

class Automatic_PointReferencing():

    def __init__(self, path_work, Th_coherency_referencepoint):

        self.path_work = path_work
        self.Th_coherency_referencepoint = Th_coherency_referencepoint

    def create_loop_closure_directory(self):
        loop_closure_path = os.path.join(self.path_work, 'loop_closure')
        
        # Check if 'loop_closure' directory exists
        if os.path.exists(loop_closure_path):
            # Remove the directory and its contents
            shutil.rmtree(loop_closure_path)
        
        # Create a new 'loop_closure' directory
        os.makedirs(loop_closure_path)

    
    def create_binary_mask(self):

        for folder_name in os.listdir(self.path_work + 'merge/'):

            folder_path = os.path.join(self.path_work + 'merge/', folder_name)

            if os.path.isdir(folder_path):
                    
                grd_file_path = os.path.join(folder_path, 'unwrap.grd')

                with rasterio.open(grd_file_path) as src:
                            # Read the first band
                            array = src.read(1)
                            self.binary_mask = np.ones((array.shape[0], array.shape[1]))
                            break

        for folder_name in os.listdir(self.path_work + 'merge/'):

            folder_path = os.path.join(self.path_work + 'merge/', folder_name)

            if os.path.isdir(folder_path):
                    
                grd_file_path = os.path.join(folder_path, 'corr.grd')

                with rasterio.open(grd_file_path) as src:
                            # Read the first band
                            array = src.read(1)
                            self.binary_mask = np.where(array<self.Th_coherency_referencepoint, 0, 1) * self.binary_mask

    
    def compute_StackInSAR(self):
        
        print('computing StackInSAR...')

        StackInSAR_path = os.path.join(self.path_work, 'StackInSAR')
        
        # Check if 'loop_closure' directory exists
        if os.path.exists(StackInSAR_path):
            # Remove the directory and its contents
            shutil.rmtree(StackInSAR_path)
        
        # Create a new 'loop_closure' directory
        os.makedirs(StackInSAR_path)
        
        numerator = np.zeros_like(self.binary_mask)
        denominator = np.zeros_like(self.binary_mask)

        for folder_name in sorted(os.listdir(self.path_work + 'merge/')):

            folder_path = os.path.join(self.path_work + 'merge/', folder_name)

            if os.path.isdir(folder_path):
                
                # Split the folder name to get the two dates
                start_str, end_str = folder_name.split('_')

                if start_str.endswith('000'):
                    start_str = start_str[:-3] + '001'

                if end_str.endswith('000'):
                    end_str = end_str[:-3] + '001'

                # Convert the 'YYYYDDD' format to datetime objects
                start_date = datetime.strptime(start_str, '%Y%j')
                end_date = datetime.strptime(end_str, '%Y%j')

                # Calculate the difference in days between the two dates
                difference_in_days = (end_date - start_date).days
                difference_in_years = (round(difference_in_days / 12) * 12) / 365.25

                grd_file_path = os.path.join(folder_path, 'unwrap.grd')

                with rasterio.open(grd_file_path) as src:
                            # Read the first band
                            unwrap_phase = src.read(1)

                for i in range(self.binary_mask.shape[0]):
                    for j in range(self.binary_mask.shape[1]):
                            if self.binary_mask[i,j] == 1:
                                numerator[i,j] = numerator[i,j] + unwrap_phase[i,j] * difference_in_years
                                denominator[i,j] = denominator[i,j] + difference_in_years*difference_in_years

        with np.errstate(divide='ignore', invalid='ignore'):
            Stack_inSAR = np.where((numerator == 0) | (denominator == 0), 0, numerator / denominator)
            Stack_inSAR = np.where(Stack_inSAR == 0, np.nan, Stack_inSAR)
            wavelength = 0.0554658 * 1000 #(convert to mm)
            Stack_inSAR = (Stack_inSAR * wavelength) / (4 * np.pi)


        for folder_name in os.listdir(self.path_work + 'merge/'):

            folder_path = os.path.join(self.path_work + 'merge/', folder_name)

            if os.path.isdir(folder_path):
                    
                grd_file_path = os.path.join(folder_path, 'unwrap.grd')

                with rasterio.open(grd_file_path) as src:
                            
                            metadata = src.meta 
                            break

        # Update metadata for the new .grd file
        metadata.update({
            'driver': 'GTiff',  # Change driver to GTiff for writing .grd
            'dtype': Stack_inSAR.dtype,  # Set the correct dtype based on your array
            'count': 1,  # Specify the number of bands
        })

        new_grd_file = os.path.join(self.path_work, 'StackInSAR/StackInSAR.grd')

        # Write the new data to the new .grd file with the same metadata
        with rasterio.open(new_grd_file, 'w', **metadata) as dst:
            dst.write(Stack_inSAR, 1)  # Write the first band (1-based index)


        working_directory = self.path_work + 'StackInSAR/'

        source_file = os.path.join(self.path_work + 'merge/trans.dat')
        target_link = os.path.join(self.path_work + 'StackInSAR/trans.dat')
        # Create symbolic link for .SAFE files
        os.symlink(source_file, target_link)

        # Change to the working directory
        os.chdir(working_directory)

        # Get the list of `.grd` files matching the pattern 'disp_*.grd'
        grd_files = [f for f in os.listdir(working_directory) if f.endswith(".grd")]

        # Loop through each `.grd` file and run the `proj_ra2ll.csh` command
        for grd_file in grd_files:
            # Extract the base name without the file extension
            base_name = os.path.splitext(grd_file)[0]
            ll_grd_file = f"{base_name}_ll.grd"  # Generate the new `.grd` file name

            # Create the command string
            command = f"tcsh -c 'proj_ra2ll.csh trans.dat {grd_file} {ll_grd_file} 400'"

            result = subprocess.run(command, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        from rasterio.enums import Resampling

        def convert_grd_to_geotiff(input_grd, output_tiff): # Converts each grd file to exact tif file (grd file must have a coordinate system)
            # Define the CRS from the provided projection system
            crs = 'EPSG:4326'  # WGS 84

            with rasterio.open(input_grd) as src:
                transform = src.transform

                meta = src.meta.copy()
                meta.update({
                    'driver': 'GTiff',
                    'crs': crs,
                    'transform': transform
                })

                # Read and resample the data
                data = src.read(
                    out_shape=(
                        src.count,
                        int(src.height), int(src.width)
                    ),
                    resampling=Resampling.nearest
                )

                # Write the data to a new GeoTIFF file
                with rasterio.open(output_tiff, 'w', **meta) as dst:
                    dst.write(data)
                    
        for root, _, files in os.walk(working_directory):
            for file in files:
                if file.endswith("ll.grd"):
                    input_file = os.path.join(root, file)
                    output_file = os.path.splitext(input_file)[0] + ".tif"
                    convert_grd_to_geotiff(input_file, output_file)


        def apply_mean_filter_to_geotiff(geotiff_path, geotiff_outpath, n):
            # Step 1: Read the GeoTIFF file as a NumPy array
            with rasterio.open(geotiff_path) as src:
                array = src.read(1)  # Read the first band as a 2D array
                metadata = src.meta  # Get the metadata for later use

            # Step 2: Create an n x n kernel for the mean filter
            kernel = np.ones((n, n)) / (n * n)

            # Step 3: Apply 2D convolution with 'same' mode to preserve the original dimensions
            filtered_array = convolve2d(array, kernel, mode='same', boundary='symm')

            # (Optional) Save the filtered array back to a new GeoTIFF
            metadata.update(dtype='float32')  # Update metadata if necessary

            with rasterio.open(geotiff_outpath, 'w', **metadata) as dst:
                dst.write(filtered_array.astype(np.float32), 1)  # Write the filtered array
                
        n = 11  # Window size (e.g., 3x3 mean filter)

        # Define your file path and window size
        geotiff_path = os.path.join(self.path_work, 'StackInSAR/StackInSAR_ll.tif')
        geotiff_outpath = os.path.join(self.path_work, 'StackInSAR/StackInSAR_ll_convolve.tif')
        filtered_array = apply_mean_filter_to_geotiff(geotiff_path, geotiff_outpath, n)

        print('StackInSAR finished...')

    def compute_loop_closure_and_write_outputs(self):

        print('LoopClosure Starting...')


        loop_closure_path = os.path.join(self.path_work, 'loop_closure')
        
        # Check if 'loop_closure' directory exists
        if os.path.exists(loop_closure_path):
            # Remove the directory and its contents
            shutil.rmtree(loop_closure_path)
        
        # Create a new 'loop_closure' directory
        os.makedirs(loop_closure_path)

        
        intf_dates = []

        with open(self.path_work+'merge/intflist', 'r') as file:
            for line in file:
                intf_dates.append(line.strip())


        self.loops_dates = []
        # loops_average_phase = []
        # loops_RMS_phase = []

        self.loops_phase_pixelwise = np.zeros_like(self.binary_mask)

        for intf12 in intf_dates:

            if [ifg for ifg in intf_dates if ifg.startswith(intf12.split('_')[1])]:

                intf23_candidates = [ifg for ifg in intf_dates if ifg.startswith(intf12.split('_')[1])] 

                for intf23 in intf23_candidates:

                    if [ifg for ifg in intf_dates if ifg.startswith(intf12.split('_')[0]) and ifg.endswith(intf23.split('_')[1])]:

                        intf13 = [ifg for ifg in intf_dates if ifg.startswith(intf12.split('_')[0]) and ifg.endswith(intf23.split('_')[1])][0]

                        self.loops_dates.append([intf12, intf23, intf13])    

                        unwrap12_path = os.path.join(os.path.join(self.path_work + 'merge/', intf12), 'unwrap.grd')
                        with rasterio.open(unwrap12_path) as src:
                            unwrap12 = np.nan_to_num(src.read(1), nan=0) * self.binary_mask
                            unwrap12[unwrap12 == 0] = np.nan

                        unwrap23_path = os.path.join(os.path.join(self.path_work + 'merge/', intf23), 'unwrap.grd')
                        with rasterio.open(unwrap23_path) as src:
                            unwrap23 = np.nan_to_num(src.read(1), nan=0) * self.binary_mask
                            unwrap23[unwrap23 == 0] = np.nan

                        unwrap13_path = os.path.join(os.path.join(self.path_work + 'merge/', intf13), 'unwrap.grd')
                        with rasterio.open(unwrap13_path) as src:
                            unwrap13 = np.nan_to_num(src.read(1), nan=0) * self.binary_mask
                            unwrap13[unwrap13 == 0] = np.nan

                        # Image-wise computation for intf network filtering
                        # loops_average_phase.append(np.nanmean(unwrap12 + unwrap23 - unwrap13))
                        # loops_RMS_phase.append(np.sqrt(np.nanmean(np.square(unwrap12 + unwrap23 - unwrap13))))
                        
                        # Pixel-wise computation for reference point selection
                        self.loops_phase_pixelwise = self.loops_phase_pixelwise + np.square(unwrap12 + unwrap23 - unwrap13)

        self.loops_phase_pixelwise = np.sqrt(self.loops_phase_pixelwise / len(self.loops_dates))



        for folder_name in os.listdir(self.path_work + 'merge/'):

            folder_path = os.path.join(self.path_work + 'merge/', folder_name)

            if os.path.isdir(folder_path):
                    
                grd_file_path = os.path.join(folder_path, 'unwrap.grd')

                with rasterio.open(grd_file_path) as src:
                            
                            metadata = src.meta 
                            break

        # Update metadata for the new .grd file
        metadata.update({
            'driver': 'GTiff',  # Change driver to GTiff for writing .grd
            'dtype': self.loops_phase_pixelwise.dtype,  # Set the correct dtype based on your array
            'count': 1,  # Specify the number of bands
        })

        new_grd_file = os.path.join(self.path_work, 'loop_closure/loops_phase_pixelwise_RMS.grd')

        # Write the new data to the new .grd file with the same metadata
        with rasterio.open(new_grd_file, 'w', **metadata) as dst:
            dst.write(self.loops_phase_pixelwise, 1)  # Write the first band (1-based index)


        working_directory = self.path_work + 'loop_closure/'

        source_file = os.path.join(self.path_work + 'merge/trans.dat')
        target_link = os.path.join(self.path_work + 'loop_closure/trans.dat')
        # Create symbolic link for .SAFE files
        os.symlink(source_file, target_link)

        # Change to the working directory
        os.chdir(working_directory)

        # Get the list of `.grd` files matching the pattern 'disp_*.grd'
        grd_files = [f for f in os.listdir(working_directory) if f.endswith(".grd")]

        # Loop through each `.grd` file and run the `proj_ra2ll.csh` command
        for grd_file in grd_files:
            # Extract the base name without the file extension
            base_name = os.path.splitext(grd_file)[0]
            ll_grd_file = f"{base_name}_ll.grd"  # Generate the new `.grd` file name

            # Create the command string
            command = f"tcsh -c 'proj_ra2ll.csh trans.dat {grd_file} {ll_grd_file} 400'" # 400 is based on 20 and 5 values of decimation

            result = subprocess.run(command, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


        def convert_grd_to_geotiff(input_grd, output_tiff): # Converts each grd file to exact tif file (grd file must have a coordinate system)
            # Define the CRS from the provided projection system
            crs = 'EPSG:4326'  # WGS 84

            with rasterio.open(input_grd) as src:
                transform = src.transform

                meta = src.meta.copy()
                meta.update({
                    'driver': 'GTiff',
                    'crs': crs,
                    'transform': transform
                })

                # Read and resample the data
                data = src.read(
                    out_shape=(
                        src.count,
                        int(src.height), int(src.width)
                    ),
                    resampling=Resampling.nearest
                )

                # Write the data to a new GeoTIFF file
                with rasterio.open(output_tiff, 'w', **meta) as dst:
                    dst.write(data)
                    
        for root, _, files in os.walk(working_directory):
            for file in files:
                if file.endswith("ll.grd"):
                    input_file = os.path.join(root, file)
                    output_file = os.path.splitext(input_file)[0] + ".tif"
                    convert_grd_to_geotiff(input_file, output_file)
        

        def apply_mean_filter_to_geotiff(geotiff_path, geotiff_outpath, n):
            # Step 1: Read the GeoTIFF file as a NumPy array
            with rasterio.open(geotiff_path) as src:
                array = src.read(1)  # Read the first band as a 2D array
                metadata = src.meta  # Get the metadata for later use

            # Step 2: Create an n x n kernel for the mean filter
            kernel = np.ones((n, n)) / (n * n)

            # Step 3: Apply 2D convolution with 'same' mode to preserve the original dimensions
            filtered_array = convolve2d(array, kernel, mode='same', boundary='symm')

            # (Optional) Save the filtered array back to a new GeoTIFF
            metadata.update(dtype='float32')  # Update metadata if necessary

            with rasterio.open(geotiff_outpath, 'w', **metadata) as dst:
                dst.write(filtered_array.astype(np.float32), 1)  # Write the filtered array
                
        n = 11  # Window size (e.g., 3x3 mean filter)

        # Define your file path and window size
        geotiff_path = os.path.join(self.path_work, 'loop_closure/loops_phase_pixelwise_RMS_ll.tif')
        geotiff_outpath = os.path.join(self.path_work, 'loop_closure/loops_phase_pixelwise_RMS_ll_convolve.tif')
        filtered_array = apply_mean_filter_to_geotiff(geotiff_path, geotiff_outpath, n)

        print('LoopClosure Finishing...')

    def recom_final_ref_point(self):
         
        geotiff_path = os.path.join(self.path_work, 'StackInSAR/StackInSAR_ll_convolve.tif')

        with rasterio.open(geotiff_path) as src:
            Velocitymap = src.read(1)  # Read the first band as a 2D array

        Th_stability = 2 # Must be in milimeter

        mask = (Velocitymap >= -Th_stability) & (Velocitymap <= Th_stability)

        geotiff_path = os.path.join(self.path_work, 'loop_closure/loops_phase_pixelwise_RMS_ll_convolve.tif')

        with rasterio.open(geotiff_path) as src:
            loop_closure_values = src.read(1)  # Read the first band as a 2D array
            metadata = src.meta  # Get the metadata for later use
            transform = src.transform

        final_decision = np.zeros_like(loop_closure_values)
        final_decision[mask] = loop_closure_values[mask]

        final_decision[final_decision==0] = np.nan

        n = 11

        ref_point = np.zeros_like(final_decision)
        row = np.where(final_decision==np.nanmin(final_decision))[0][0]
        col = np.where(final_decision==np.nanmin(final_decision))[1][0]
        ref_point[row-n:row+n, col-n:col+n] = 1
        geotiff_outpath = os.path.join(self.path_work, 'loop_closure/ref_point.tif')

        with rasterio.open(geotiff_outpath, 'w', **metadata) as dst:
            dst.write(ref_point.astype(np.float32), 1)  # Write the filtered array

        def get_topn_min_values_with_coords(final_decision, transform, top_suggestions):
                
            # Flatten the array and get the indices of non-NaN values
            flat_data = final_decision.flatten()

            # Remove NaN values by masking them out
            non_nan_indices = np.where(~np.isnan(flat_data))[0]  # Indices of non-NaN values
            
            # Get the non-NaN values
            non_nan_data = flat_data[non_nan_indices]

            # Find the indices of the top N minimum values among the non-NaN data
            topn_indices_in_non_nan = np.argpartition(non_nan_data, top_suggestions)[:top_suggestions]

            # Get the actual top N minimum values from non-NaN data
            topn_values = non_nan_data[topn_indices_in_non_nan]

            # Map back the indices to the original data array
            topn_original_indices = non_nan_indices[topn_indices_in_non_nan]

            # Convert the flat indices back to 2D row, col indices
            topn_rows, topn_cols = np.unravel_index(topn_original_indices, final_decision.shape)

            # Convert the row, col indices to lat, lon coordinates
            topn_coords = [rasterio.transform.xy(transform, row, col) for row, col in zip(topn_rows, topn_cols)]

            # Combine the top N values with their corresponding coordinates
            topn_values_with_coords = [(value, (lon, lat)) for value, (lon, lat) in zip(topn_values, topn_coords)]
            
            # Sort based on the values (ascending order to keep minimum values first)
            topn_values_with_coords.sort(key=lambda x: x[0])
                
            return topn_values_with_coords

        top_suggestions = 1

        top5_referencepoints = get_topn_min_values_with_coords(final_decision, transform, top_suggestions)

        for value, coords in top5_referencepoints:
            lon, lat = coords  # Assuming coords is a tuple (lon, lat)
            print(f"Recommended Ref Point Coordinates based on Stability and loop closure quality check (lon and lat): ({lon:.5f}, {lat:.5f})")