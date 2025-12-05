import os
import shutil
import subprocess

class Clipping:

    def __init__(self, base_path, pin1, pin2):
        self.base_path = base_path
        self.pin1 = pin1
        self.pin2 = pin2

    def write_pins_files(self):

        pins = [
            f"{self.pin1[0]} {self.pin1[1]}",
            f"{self.pin2[0]} {self.pin2[1]}"
        ]

        pins_file = os.path.join(self.base_path, "pins.ll")

        with open(pins_file, "w") as f:
            f.write("\n".join(pins) + "\n")

    def create_SAFEfilelist(self):
        ############## creating SAFE_filelist
        # Collect all .SAFE entries directly in base_path
        safe_names = [
            name for name in os.listdir(self.base_path)
            if name.endswith('.SAFE')
        ]

        safe_names_sorted = sorted(safe_names)

        # Build absolute paths
        safe_paths_sorted = [
            os.path.abspath(os.path.join(self.base_path, name))
            for name in safe_names_sorted
        ]
        filelist_path = os.path.join(self.base_path, 'SAFE_filelist')
        # Write one full path per line
        with open(filelist_path, 'w') as f:
            for path in safe_paths_sorted:
                f.write(path + '\n')

    def do_clipping(self):
        print('starting to clip...')

        cmd = "organize_files_tops_linux.csh SAFE_filelist pins.ll 2"
        subprocess.run(cmd, shell=True, cwd = self.base_path, check=True, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print('clipping finished...')


        # 1. Find the directory inside base_path that starts with 'F'
        F_dirs = [d for d in os.listdir(self.base_path)
                if d.startswith('F') and os.path.isdir(os.path.join(self.base_path, d))]
        F_path = os.path.join(self.base_path, sorted(F_dirs)[-1])

        eof_files = [f for f in os.listdir(self.base_path) if f.endswith('.EOF')]

        for eof in eof_files:
            src = os.path.join(self.base_path, eof)
            dst = os.path.join(F_path, eof)

            # Remove old link if exists
            if os.path.exists(dst):
                os.remove(dst)

            os.symlink(src, dst)

        print('F****_**** is ready to be the main base_path')
        return F_path