import os
import shutil
import subprocess
import re

class Stitching():

    def __init__(self, base_path, pin1, pin2):

        self.base_path = base_path
        self.pin1 = pin1
        self.pin2 = pin2

    def prepare_stitch_folder(self):

        ############# creating reframed folder
        combo_dir = os.path.join(self.base_path, '1+2')
        self.combo_dir = combo_dir
        # If "reframed" exists, delete it completely
        if os.path.exists(combo_dir):
            shutil.rmtree(combo_dir)
        os.makedirs(combo_dir)

        print('trying to keep common images in both 1 and 2 folders in the 1+2 folders')
        ############## copying common images in both 1 and 2 to 1+2 folder

        subdirs = ['1', '2']

        safe_date_re = re.compile(r'_(\d{8})T\d{6}_')
        eof_valid_re = re.compile(r'_V(\d{8})T\d{6}_(\d{8})T\d{6}\.EOF$')

        # --- 2) Collect SAFE files by date for folders 1 and 2 ---

        safes_by_dir_and_date = {d: {} for d in subdirs}

        for d in subdirs:
            folder = os.path.join(self.base_path, d)
            for name in os.listdir(folder):
                if not name.endswith('.SAFE'):
                    continue
                m = safe_date_re.search(name)
                if not m:
                    print(f"WARNING: could not parse date from SAFE: {name}")
                    continue
                date = m.group(1)  # 'YYYYMMDD'
                safes_by_dir_and_date[d].setdefault(date, []).append(os.path.join(folder, name))

        dates_1 = set(safes_by_dir_and_date['1'].keys())
        dates_2 = set(safes_by_dir_and_date['2'].keys())
        common_dates = sorted(dates_1 & dates_2)


        # --- 3) Collect EOF files and map them to dates (from folder '1' primarily) ---

        eof_by_date = {}  # date -> list of EOF full paths

        def add_eofs_from_folder(folder):
            for name in os.listdir(folder):
                if not name.endswith('.EOF'):
                    continue
                m = eof_valid_re.search(name)
                if not m:
                    print(f"Error: could not parse validity from EOF: {name}")
                    continue
                start_date, end_date = m.group(1), m.group(2)  # YYYYMMDD strings
                full_path = os.path.join(folder, name)
                # This EOF is valid for all dates in [start_date, end_date] (inclusive)
                for date in common_dates:
                    if start_date <= date <= end_date:
                        eof_by_date.setdefault(date, set()).add(full_path)

        # Prefer EOFs from folder '1', fall back to '2' if needed
        add_eofs_from_folder(os.path.join(self.base_path, '1'))
        add_eofs_from_folder(os.path.join(self.base_path, '2'))

        # --- 4) Create symlinks for SAFE and EOF files in 1+2 and build SAFE_filelist order ---

        linked_safe_paths = []       # full paths to symlinked SAFE dirs in 1+2, in desired order
        linked_eof_sources = set()   # unique EOF source paths that we symlink

        for date in common_dates:
            # Order: folder 1 first, then folder 2
            for d in subdirs:
                safes = safes_by_dir_and_date[d].get(date, [])
                for src in sorted(safes):  # sort by filename within each folder
                    dst = os.path.join(combo_dir, os.path.basename(src))
                    if os.path.exists(dst):
                        os.remove(dst)  # overwrite if exists
                    os.symlink(src, dst)
                    linked_safe_paths.append(os.path.abspath(dst))

            # Pick one EOF for this date (if available)
            eof_candidates = sorted(eof_by_date.get(date, []))
            if eof_candidates:
                eof_src = eof_candidates[0]  # pick the first one
                linked_eof_sources.add(eof_src)

        for eof_src in sorted(linked_eof_sources):
            dst = os.path.join(combo_dir, os.path.basename(eof_src))
            if os.path.exists(dst):
                os.remove(dst)
            os.symlink(eof_src, dst)

        self.linked_safe_paths = linked_safe_paths

    def create_SAFEfilelist(self):
        # --- 5) Create SAFE_filelist inside 1+2 ---

        safe_filelist_path = os.path.join(self.combo_dir, 'SAFE_filelist')

        with open(safe_filelist_path, 'w') as f:
            for path in self.linked_safe_paths:
                f.write(path + '\n')


    def write_pins_files(self):

        ############## creating pins.ll

        # note that pins must be in the direction of flight so if the data is ascending pin1 must be below point
        # pin1 = [44.48, 40.31] #lon, lat
        # pin2 = [44.27, 39.58] #lon, lat

        pins = [
            f"{self.pin1[0]} {self.pin1[1]}",
            f"{self.pin2[0]} {self.pin2[1]}"
        ]

        pins_file = os.path.join(self.combo_dir, "pins.ll")

        with open(pins_file, "w") as f:
            f.write("\n".join(pins) + "\n")


    def do_stitching(self):
        
        print('starting to stitch...')

        cmd = "organize_files_tops_linux.csh SAFE_filelist pins.ll 2"
        subprocess.run(cmd, shell=True, cwd = self.combo_dir, check=True, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print('stitch completely done...')


        # 1. Find the directory inside base_path that starts with 'F'
        F_dirs = [d for d in os.listdir(self.combo_dir)
                if d.startswith('F') and os.path.isdir(os.path.join(self.combo_dir, d))]
        F_path = os.path.join(self.combo_dir, sorted(F_dirs)[-1])

        eof_files = [f for f in os.listdir(self.combo_dir) if f.endswith('.EOF')]

        for eof in eof_files:
            src = os.path.join(self.combo_dir, eof)
            dst = os.path.join(F_path, eof)

            # Remove old link if exists
            if os.path.exists(dst):
                os.remove(dst)

            os.symlink(src, dst)

        print('F****_**** is ready to be the main base_path')
        return F_path
