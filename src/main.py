import argparse
from clipping import Clipping
from stitching_several_frames import Stitching
from directorymanager import get_IW_numbers_inbase, create_required_directories, create_symboliklink_EOF, create_symboliklink_Tif
from downloadDEM_singleframe import DEMdownloader_singleframe
from downloadDEM_multiframe import DEMdownloader_multiframe
from create_baselinetable import Create_baselinetable_of_S1_data
from select_master_image_Coregistration import Master_selection
from coregistration import Coregistration
from intf_pairs import intf_pairs
from intf_computation import Intf_compute
from merge_subswaths import merge
from create_landmask import Landmask
from phase_unwrapping import PhaseUnwrapping
import os
import shutil
import io
from corr_grd_backup_preparation import Corr
from automatic_point_referencing import Automatic_PointReferencing
from automatic_average_referencing import Average_Referencing
from point_referencing import Referencing
from SBAS import SBASadjustment
from SBAS_outputs import SBASoutputs
import time

def main(condition_for_running):
    if condition_for_running:

       # Argument parser object
        parser = argparse.ArgumentParser(description = 'Processing inputs from the command line...')

        parser.add_argument('--base_path', type = str, required = True, help = 'Directory of your S1 timeseries data, which is a directory of .SAFE and .EOF files.')
        parser.add_argument('--work_path', type = str, required = True, help = 'The directory in which the processed files will be kept.')
        # parser.add_argument('--IW_number', type = int, nargs='+', required = True, help = 'List of IW numbers, e.g., 1 2 3 or 1 2')
        parser.add_argument('--temporal_baseline', type=int, required=True, help='Temporal baseline of interferograms')
        parser.add_argument('--spatial_baseline', type=int, required=True, help='Spatial baseline of interferograms')
        parser.add_argument('--filter_intf_pairs', type=eval, required=True, choices=[True, False], help='Do you want to filter the number of connections in intf network?')

        # Additional integer argument (optional, depending on --filter_intf_pairs)
        parser.add_argument('--TH_number_of_connections', type=int, help='Number of connections for filtering of intf pairs')

        parser.add_argument('--filter_wavelength_value', type=int, required=True, help='Wavelength value for filtering intfs')
        parser.add_argument('--range_dec_value', type=int, required=True, help='Range decimation value for intf computation')
        parser.add_argument('--azimuth_dec_value', type=int, required=True, help='Azimuth decimation value for intf computation')
        parser.add_argument('--n_jobs_for_intf', type=int, required=True, help='Number of jobs for parallel computation of interferograms')
        parser.add_argument('--n_jobs_for_merging', type=int, required=True, help='Number of jobs for parallel merging of subswaths')

        parser.add_argument('--n_jobs_for_unwrapping', type=int, required=True, help='Number of jobs for parallel phase unwrapping')

        # Parse the command line arguments
        args = parser.parse_args()

        # Conditional check
        if args.filter_intf_pairs:
            if args.TH_number_of_connections is None:
                parser.error("--TH_number_of_connections is required when --filter_intf_pairs is True.")
        else:
            if args.TH_number_of_connections is not None:
                print("Warning: --TH_number_of_connections is ignored when --filter_intf_pairs is False.")

        base_path = args.base_path
        base_path_orignial = args.base_path
        work_path = args.work_path
        # IW_number = args.IW_number
        temporal_baseline = args.temporal_baseline
        spatial_baseline = args.spatial_baseline
        filter_intf_pairs = args.filter_intf_pairs
        TH_number_of_connections = args.TH_number_of_connections
        filter_wavelength_value = args.filter_wavelength_value
        range_dec_value = args.range_dec_value
        azimuth_dec_value = args.azimuth_dec_value
        n_jobs_for_intf = args.n_jobs_for_intf
        n_jobs_for_merging = args.n_jobs_for_merging
        n_jobs_for_unwrapping = args.n_jobs_for_unwrapping


        print('')
        print('#####################################  DefoEye  #####################################')
        print('')

        print('')
        print('#####################################  stitching/clipping  #####################################')
        print('')

        print('')
        print('There are three possible cases when working with software about your input data:')
        print('1- You want to work on a single frame without clipping (base path should contain both .SAFE and .EOF files)')
        print('2- You want to work on a single frame with clipping (base path should contain both .SAFE and .EOF files)')
        print('3- You want to work on several frames and stitch them together (must be the same-along track/ across track is not supported)')
        print('     For 3, base path should contain two folders with names of 1 and 2 (1 is the first image aquired in the satellite direction)')
        print('     with each folder having all .SAFE and .EOF files')
        print('')
        print('If you say no to the upcoming two questions, it means: case#1: You want to work on a single frame without clipping')
        print('')

        print('Do you want to stitch several frames together or not? answer must be: "yes, y, true, no, n, false"')
        user_answer_stitching = input()

        if user_answer_stitching in ["yes", "y", "true"]:

                print('You need to import the coordinates of two pins. Pin1 is the first pin in the flight direction. So, for example if it is ascending, pin1 is the below one.')
                print('Please enter the pin1 point Lat:')
                pin1_lat = input()
                print('Please enter the pin1 point Lon:')
                pin1_lon = input()
                print('Please enter the pin2 point Lat:')
                pin2_lat = input()
                print('Please enter the pin2 point Lon:')
                pin2_lon = input()

                pin1 = [float(pin1_lon), float(pin1_lat)]
                pin2 = [float(pin2_lon), float(pin2_lat)]

                stitcher = Stitching(base_path, pin1, pin2)
                stitcher.prepare_stitch_folder()
                stitcher.create_SAFEfilelist()
                stitcher.write_pins_files()
                base_path = stitcher.do_stitching()


        else:
            print('Do you want to clip your single frame? answer must be: "yes, y, true, no, n, false"')
            user_answer_clipping = input()

            if user_answer_clipping in ["yes", "y", "true"]:
                
                print('You need to import the coordinates of two pins. Pin1 is the first pin in the flight direction. So, for example if it is ascending, pin1 is the below one.')
                print('Please enter the pin1 point Lat:')
                pin1_lat = input()
                print('Please enter the pin1 point Lon:')
                pin1_lon = input()
                print('Please enter the pin2 point Lat:')
                pin2_lat = input()
                print('Please enter the pin2 point Lon:')
                pin2_lon = input()

                pin1 = [float(pin1_lon), float(pin1_lat)]
                pin2 = [float(pin2_lon), float(pin2_lat)]

                clipper = Clipping(base_path, pin1, pin2)
                clipper.write_pins_files()
                clipper.create_SAFEfilelist()
                base_path = clipper.do_clipping()

        print('')
        print('#####################################  Directory Management')
        print('')

        print('Creating required directories and symbolik links...')
        IW_number = get_IW_numbers_inbase(base_path)
        create_required_directories(work_path, IW_number)
        create_symboliklink_EOF(base_path, work_path)
        create_symboliklink_Tif(base_path, work_path, IW_number)

        # Instantiate the DEMProcessor class and process the data

        print('DEM download start...')

        if user_answer_stitching in ["yes", "y", "true"]:

            print('')
            print('Downloading DEM for multiple frames')
            print('')

            dem_processor = DEMdownloader_multiframe(base_path_orignial, work_path)
            dem_processor.process()

        else: # for clipped/nonclipped cases, DEM must come from the full xml files to prevent from partial coverage
            
            print('')
            print('Downloading DEM for a single frame')
            print('')

            dem_processor = DEMdownloader_singleframe(base_path_orignial, work_path) #base_path_orignial because if you are clipping sinces, that might be a problem in download dem and dem does not cover all of your area
            dem_processor.process()

        print('')
        print('#####################################  Baseline Table Formation')
        print('')

        print('Computing baseline information of all images across different IWs...')

        coregistration_stage = Create_baselinetable_of_S1_data(work_path, IW_number)
        coregistration_stage.create_datain_file()
        coregistration_stage.create_baselinetable_file()

        print('')
        print('#####################################  Master Date Selection')
        print('')

        master_selection = Master_selection(work_path, IW_number)
        master_selection.giving_options()
        master_selection.get_master_from_user()

        print('')
        print('#####################################  Coregistration')
        print('')

        print('Coregistration of all images across all IWs to the master date image...')

        start_time = time.time()

        coregistration = Coregistration(work_path, IW_number)
        coregistration.coregistration()

        end_time = time.time()

        elapsed_seconds = end_time - start_time
        elapsed_minutes = elapsed_seconds / 60.0

        print(f' ### Execution time for Image Alignment: {elapsed_minutes:.2f} minutes.')

        print('')
        print('#####################################  Interferogram Computation')
        print('')

        intfs= intf_pairs(work_path, IW_number, temporal_baseline, spatial_baseline, filter_intf_pairs, TH_number_of_connections)
        intfs.create_intfin_file()
        intfs.initial_intf_pairs()
        intfs.filter_intf_network()
        intfs.copy_intfin_to_Ffolders()

        start_time = time.time()

        intfcompute = Intf_compute(work_path, IW_number, filter_wavelength_value, range_dec_value, azimuth_dec_value, n_jobs_for_intf)
        intfcompute.copy_batchtops_file()
        intfcompute.update_batchtops_test_firstintf()
        intfcompute.all_intf_computation()
        intfcompute.check_all_intf()

        end_time = time.time()

        elapsed_seconds = end_time - start_time
        elapsed_minutes = elapsed_seconds / 60.0

        print(f' ### Execution time for Interferogram Computation: {elapsed_minutes:.2f} minutes.')


        print('')
        print('#####################################  Merging IWs')
        print('')

        start_time = time.time()

        merging = merge(work_path, IW_number, n_jobs_for_merging)
        merging.create_merge_requirementfiles()
        merging.merge_first()
        merging.merge_otherintfs()
        merging.create_pdf_of_merged()
        merging.check_merging()

        end_time = time.time()

        elapsed_seconds = end_time - start_time
        elapsed_minutes = elapsed_seconds / 60.0

        print(f' ### Execution time for Mering: {elapsed_minutes:.2f} minutes.')

        print('')
        print('#####################################  Phase Unwrapping')
        print('')

        landmask = Landmask(work_path)
        landmask.create_land_mask()

        print('')
        print('###################################################  For the first run, it is great to run untill here')
        print('')

        print('It is a good idea to backup your merge folder for future if you want to change anything. Do you want to back it up? If you have done it before, write no. answer must be: "yes, y, true, no, n, false"')
        user_answer_copymerge = input()

        #Backup merge
        if user_answer_copymerge in ["yes", "y", "true"]:
            src = os.path.join(work_path, "merge")
            dst = os.path.join(work_path, "merge_BC")

            print()
            print("Copying merge started...")

            # shutil.copytree is blocking; next line runs only after copy finishes or errors
            shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=False)

            print("Copying merge finished...")
            print()

        print('Please insert TH1 for unwrapping (recommended: 0.01):')
        TH1_unwrapping = input()

        print('Please insert TH2 for unwrapping (recommended: 1):')
        TH2_unwrapping = input()

        print('You can go to the merge directory and have a look at corr.pdf files to insert regioncut boundary:')

        regioncut = input("Enter the regioncut in the format {first_column}/{last_column}/{first_row}/{last_row}: ")
        first_column, last_column, first_row, last_row = regioncut.split("/")

        # Saving regioncut
        outfile = os.path.join(work_path, "regioncuts_{}_{}.txt".format(TH1_unwrapping, TH2_unwrapping))
        with io.open(outfile, "a", encoding="utf-8") as f:
            f.write(regioncut.strip() + "\n")

        start_time = time.time()

        phaseunwrap = PhaseUnwrapping(work_path, TH1_unwrapping, TH2_unwrapping, first_column, last_column, first_row, last_row, n_jobs_for_unwrapping)
        phaseunwrap.create_unwrapcsh()
        phaseunwrap.parallel_unwrapping()

        end_time = time.time()

        elapsed_seconds = end_time - start_time
        elapsed_minutes = elapsed_seconds / 60.0

        print(f' ### Execution time for Phase Unwrapping: {elapsed_minutes:.2f} minutes.')

        corr_prep = Corr(work_path, first_column, last_column, first_row, last_row)
        corr_prep.compute_mean_coherency_in_region()
        corr_prep.corr_backup()
        corr_prep.corr_cut_create_pdf()

        print('')
        print('#####################################  Referencing')
        print('')

        print('Do you want to consider a reference point? answer must be: "yes, y, true, no, n, false"')
        user_answer_referencing = input()

        if user_answer_referencing in ["yes", "y", "true"]:

            print('Do you want to use a single point lat and lon (insert 1) or average of the unwrapped intfs (insert 2) as the reference ?')
            user_method_referencing = input()

            if int(user_method_referencing)==1:
                # print('GMTSAR+ recommends you a reference point based on Coherency+Loop Closure Error')
                # print('Please enter the coherency threshold for considering reference point (recommended values: 0.1 or 0.2- if you do not want to consider coherency, insert 0):')
                # Th_coherency_referencepoint = input()
                # auto_referencing = Automatic_PointReferencing(work_path, float(Th_coherency_referencepoint))
                # print('Recommonding the reference point...')
                # auto_referencing.create_binary_mask()
                # auto_referencing.compute_StackInSAR()
                # auto_referencing.compute_loop_closure_and_write_outputs()
                # auto_referencing.recom_final_ref_point()
                # print('If you want to use the above reference point, insert its coordinates below. Otherwise, insert your interested coordinates:')
                print('Please enter the reference point Lat:')
                ref_lat = input()
                print('Please enter the reference point Lon:')
                ref_lon = input()
                print('Please enter the neighbourhood size (n) (it creates a 2n+1 grid around the reference point):')
                neighbourhoodsize = input()

                pointreferencing = Referencing(work_path, float(ref_lat), float(ref_lon), int(neighbourhoodsize))
                pointreferencing.referencing()

            elif int(user_method_referencing)==2:

                print('Referencing on the average of unwrapped interferograms')
                print('Please enter the coherency threshold for computing the average of each unwrapp intf (recommended values: 0.1):')
                Th_coherency_referenceaveraging = input()

                avg_referencing = Average_Referencing(work_path, float(Th_coherency_referenceaveraging))
                avg_referencing.average_referencing()
                
            else:

                print('Referencing was not considered...')

        print('')
        print('#####################################  SBAS')
        print('')

        print('Please insert smooth_factor for SBAS (recommended: 5):')
        smooth_factor = int(input())

        print('Please insert atm_factor for SBAS (recommended: 1):')
        atm_factor = int(input())

        sbas = SBASadjustment(work_path, smooth_factor, atm_factor)
        sbas.create_symboliclink_supermaster()
        sbas.create_symboliclink_intf_baseline()
        sbas.create_intftab_scenetab_files()
        sbas.symbolic_link_trans_guass()
        sbas.sbas_main()

        print('')
        print('#####################################  Export Management')
        print('')

        print('Please insert filter_wavelength_resolution for generating the final output files (recommended: 400 for az and range decimations of 20 and 5):')
        filter_wavelength_resolution = int(input())

        sbasoutputs = SBASoutputs(work_path, filter_wavelength_resolution)
        sbasoutputs.create_vel_llgrd()
        sbasoutputs.grds_to_grdll()
        sbasoutputs.grdll_to_geotif()

    else:
    
        # Argument parser object
        parser = argparse.ArgumentParser(description = 'Processing inputs from the command line...')

        parser.add_argument('--base_path', type = str, required = True, help = 'Directory of your S1 timeseries data, which is a directory of .SAFE and .EOF files.')
        parser.add_argument('--work_path', type = str, required = True, help = 'The directory in which the processed files will be kept.')
        # parser.add_argument('--IW_number', type = int, nargs='+', required = True, help = 'List of IW numbers, e.g., 1 2 3 or 1 2')
        parser.add_argument('--temporal_baseline', type=int, required=True, help='Temporal baseline of interferograms')
        parser.add_argument('--spatial_baseline', type=int, required=True, help='Spatial baseline of interferograms')
        parser.add_argument('--filter_intf_pairs', type=eval, required=True, choices=[True, False], help='Do you want to filter the number of connections in intf network?')

        # Additional integer argument (optional, depending on --filter_intf_pairs)
        parser.add_argument('--TH_number_of_connections', type=int, help='Number of connections for filtering of intf pairs')

        parser.add_argument('--filter_wavelength_value', type=int, required=True, help='Wavelength value for filtering intfs')
        parser.add_argument('--range_dec_value', type=int, required=True, help='Range decimation value for intf computation')
        parser.add_argument('--azimuth_dec_value', type=int, required=True, help='Azimuth decimation value for intf computation')
        parser.add_argument('--n_jobs_for_intf', type=int, required=True, help='Number of jobs for parallel computation of interferograms')
        parser.add_argument('--n_jobs_for_merging', type=int, required=True, help='Number of jobs for parallel merging of subswaths')

        parser.add_argument('--n_jobs_for_unwrapping', type=int, required=True, help='Number of jobs for parallel phase unwrapping')

        # Parse the command line arguments
        args = parser.parse_args()

        # Conditional check
        if args.filter_intf_pairs:
            if args.TH_number_of_connections is None:
                parser.error("--TH_number_of_connections is required when --filter_intf_pairs is True.")
        else:
            if args.TH_number_of_connections is not None:
                print("Warning: --TH_number_of_connections is ignored when --filter_intf_pairs is False.")

        base_path = args.base_path
        work_path = args.work_path
        # IW_number = args.IW_number
        temporal_baseline = args.temporal_baseline
        spatial_baseline = args.spatial_baseline
        filter_intf_pairs = args.filter_intf_pairs
        TH_number_of_connections = args.TH_number_of_connections
        filter_wavelength_value = args.filter_wavelength_value
        range_dec_value = args.range_dec_value
        azimuth_dec_value = args.azimuth_dec_value
        n_jobs_for_intf = args.n_jobs_for_intf
        n_jobs_for_merging = args.n_jobs_for_merging
        n_jobs_for_unwrapping = args.n_jobs_for_unwrapping

        # print('base_path: ', type(base_path))
        # print('work_path: ', type(work_path))
        # print('IW_number: ', type(IW_number))

        # print('base_path: ', base_path)
        # print('work_path: ', work_path)
        # print('IW_number: ', IW_number)

        print('')
        print('#####################################  GMTSAR+  #####################################')
        print('')


        print('')
        print('#####################################  Directory Management')
        print('')

        print('Creating required directories and symbolik links...')
        IW_number = get_IW_numbers_inbase(base_path)
        create_required_directories(work_path, IW_number)
        create_symboliklink_EOF(base_path, work_path)
        create_symboliklink_Tif(base_path, work_path, IW_number)

        # Instantiate the DEMProcessor class and process the data

        print('DEM download start...')

        dem_processor = DEMdownloader(base_path, work_path)
        dem_processor.process()

        print('')
        print('#####################################  Baseline Table Formation')
        print('')

        print('Computing baseline information of all images across different IWs...')

        coregistration_stage = Create_baselinetable_of_S1_data(work_path, IW_number)
        coregistration_stage.create_datain_file()
        coregistration_stage.create_baselinetable_file()

        print('')
        print('#####################################  Master Date Selection')
        print('')

        master_selection = Master_selection(work_path, IW_number)
        master_selection.giving_options()
        master_selection.get_master_from_user()

        print('')
        print('#####################################  Coregistration')
        print('')

        print('Coregistration of all images across all IWs to the master date image...')

        start_time = time.time()

        coregistration = Coregistration(work_path, IW_number)
        coregistration.coregistration()

        end_time = time.time()

        elapsed_seconds = end_time - start_time
        elapsed_minutes = elapsed_seconds / 60.0

        print(f' ### Execution time for Image Alignment: {elapsed_minutes:.2f} minutes.')

        print('')
        print('#####################################  Interferogram Computation')
        print('')

        intfs= intf_pairs(work_path, IW_number, temporal_baseline, spatial_baseline, filter_intf_pairs, TH_number_of_connections)
        intfs.create_intfin_file()
        intfs.initial_intf_pairs()
        intfs.filter_intf_network()
        intfs.copy_intfin_to_Ffolders()

        start_time = time.time()

        intfcompute = Intf_compute(work_path, IW_number, filter_wavelength_value, range_dec_value, azimuth_dec_value, n_jobs_for_intf)
        intfcompute.copy_batchtops_file()
        intfcompute.update_batchtops_test_firstintf()
        intfcompute.all_intf_computation()
        intfcompute.check_all_intf()

        end_time = time.time()

        elapsed_seconds = end_time - start_time
        elapsed_minutes = elapsed_seconds / 60.0

        print(f' ### Execution time for Interferogram Computation: {elapsed_minutes:.2f} minutes.')


        print('')
        print('#####################################  Merging IWs')
        print('')

        start_time = time.time()

        merging = merge(work_path, IW_number, n_jobs_for_merging)
        merging.create_merge_requirementfiles()
        merging.merge_first()
        merging.merge_otherintfs()
        merging.create_pdf_of_merged()
        merging.check_merging()

        end_time = time.time()

        elapsed_seconds = end_time - start_time
        elapsed_minutes = elapsed_seconds / 60.0

        print(f' ### Execution time for Mering: {elapsed_minutes:.2f} minutes.')

        print('')
        print('#####################################  Phase Unwrapping')
        print('')

        landmask = Landmask(work_path)
        landmask.create_land_mask()

        print('')
        print('###################################################  For the first run, it is great to run untill here')
        print('')

        print('It is a good idea to backup your merge folder for future if you want to change anything. Do you want to back it up? If you have done it before, write no. answer must be: "yes, y, true, no, n, false"')
        user_answer_copymerge = input()

        #Backup merge
        if user_answer_copymerge in ["yes", "y", "true"]:
            src = os.path.join(work_path, "merge")
            dst = os.path.join(work_path, "merge_BC")

            print()
            print("Copying merge started...")

            # shutil.copytree is blocking; next line runs only after copy finishes or errors
            shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=False)

            print("Copying merge finished...")
            print()

        print('Please insert TH1 for unwrapping (recommended: 0.01):')
        TH1_unwrapping = input()

        print('Please insert TH2 for unwrapping (recommended: 1):')
        TH2_unwrapping = input()

        print('You can go to the merge directory and have a look at corr.pdf files to insert regioncut boundary:')

        regioncut = input("Enter the regioncut in the format {first_column}/{last_column}/{first_row}/{last_row}: ")
        first_column, last_column, first_row, last_row = regioncut.split("/")

        # Saving regioncut
        outfile = os.path.join(work_path, "regioncuts_{}_{}.txt".format(TH1_unwrapping, TH2_unwrapping))
        with io.open(outfile, "a", encoding="utf-8") as f:
            f.write(regioncut.strip() + "\n")

        start_time = time.time()

        phaseunwrap = PhaseUnwrapping(work_path, TH1_unwrapping, TH2_unwrapping, first_column, last_column, first_row, last_row, n_jobs_for_unwrapping)
        phaseunwrap.create_unwrapcsh()
        phaseunwrap.parallel_unwrapping()

        end_time = time.time()

        elapsed_seconds = end_time - start_time
        elapsed_minutes = elapsed_seconds / 60.0

        print(f' ### Execution time for Phase Unwrapping: {elapsed_minutes:.2f} minutes.')

        corr_prep = Corr(work_path, first_column, last_column, first_row, last_row)
        corr_prep.compute_mean_coherency_in_region()
        corr_prep.corr_backup()
        corr_prep.corr_cut_create_pdf()

        print('')
        print('#####################################  Referencing')
        print('')

        print('Do you want to consider a reference point? answer must be: "yes, y, true, no, n, false"')
        user_answer_referencing = input()

        if user_answer_referencing in ["yes", "y", "true"]:

            print('Do you want to use a single point lat and lon (insert 1) or average of the unwrapped intfs (insert 2) as the reference ?')
            user_method_referencing = input()

            if int(user_method_referencing)==1:
                print('GMTSAR+ recommends you a reference point based on Coherency+Loop Closure Error')
                print('Please enter the coherency threshold for considering reference point (recommended values: 0.1 or 0.2- if you do not want to consider coherency, insert 0):')
                Th_coherency_referencepoint = input()
                auto_referencing = Automatic_PointReferencing(work_path, float(Th_coherency_referencepoint))
                print('Recommonding the reference point...')
                auto_referencing.create_binary_mask()
                auto_referencing.compute_StackInSAR()
                auto_referencing.compute_loop_closure_and_write_outputs()
                auto_referencing.recom_final_ref_point()
                print('If you want to use the above reference point, insert its coordinates below. Otherwise, insert your interested coordinates:')
                print('Please enter the reference point Lat:')
                ref_lat = input()
                print('Please enter the reference point Lon:')
                ref_lon = input()
                print('Please enter the neighbourhood size (n) (it creates a 2n+1 grid around the reference point):')
                neighbourhoodsize = input()

                pointreferencing = Referencing(work_path, float(ref_lat), float(ref_lon), int(neighbourhoodsize))
                pointreferencing.referencing()

            elif int(user_method_referencing)==2:

                print('Referencing on the average of unwrapped interferograms')
                print('Please enter the coherency threshold for computing the average of each unwrapp intf (recommended values: 0.1):')
                Th_coherency_referenceaveraging = input()

                avg_referencing = Average_Referencing(work_path, float(Th_coherency_referenceaveraging))
                avg_referencing.average_referencing()
                
            else:

                print('Referencing was not considered...')

        print('')
        print('#####################################  SBAS')
        print('')

        print('Please insert smooth_factor for SBAS (recommended: 5):')
        smooth_factor = int(input())

        print('Please insert atm_factor for SBAS (recommended: 1):')
        atm_factor = int(input())

        sbas = SBASadjustment(work_path, smooth_factor, atm_factor)
        sbas.create_symboliclink_supermaster()
        sbas.create_symboliclink_intf_baseline()
        sbas.create_intftab_scenetab_files()
        sbas.symbolic_link_trans_guass()
        sbas.sbas_main()

        print('')
        print('#####################################  Export Management')
        print('')

        print('Please insert filter_wavelength_resolution for generating the final output files (recommended: 400 for az and range decimations of 20 and 5):')
        filter_wavelength_resolution = int(input())

        sbasoutputs = SBASoutputs(work_path, filter_wavelength_resolution)
        sbasoutputs.create_vel_llgrd()
        sbasoutputs.grds_to_grdll()
        sbasoutputs.grdll_to_geotif()


if __name__=='__main__':
    condition_for_running = True
    main(condition_for_running)