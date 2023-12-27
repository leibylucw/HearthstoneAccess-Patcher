import ctypes
import os
import requests
import shutil
import subprocess
import sys
import zipfile
import concurrent.futures


def search_directory(start_path, target):
    try:
        for root, dirs, files in os.walk(start_path):
            if target in dirs:
                return os.path.join(root, target)
    except Exception as e:
        print(f"Error during directory search: {e}")
    return None


def find_hearthstone_directory():
    target = "Hearthstone"
    start_path = "C:\\"

    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_dir = {executor.submit(search_directory, os.path.join(start_path, d), target): d for d in os.listdir(start_path) if os.path.isdir(os.path.join(start_path, d))}

            for future in concurrent.futures.as_completed(future_to_dir):
                result = future.result()
                if result is not None:
                    return result
    except Exception as e:
        print(f"Error in concurrent directory search: {e}")
    return None

def determine_patch_destination():
    try:
        hearthstone_default_dir = "C:\\Program Files (x86)\\Hearthstone"
        if os.path.exists(hearthstone_default_dir):
            return hearthstone_default_dir

        hearthstone_dir_env = get_hearthstone_dir_from_environment()
        if hearthstone_dir_env and os.path.exists(hearthstone_dir_env):
            return hearthstone_dir_env

        return find_hearthstone_directory()
    except Exception as e:
        print(f"Error determining patch destination: {e}")
        return None


def set_hearthstone_dir_from_environment(hearthstone_dir):
    try:
        subprocess.run(f'setx HEARTHSTONE_HOME "{hearthstone_dir}"', shell=True)
    except Exception as e:
        print(f"Error setting Hearthstone directory in environment: {e}")


def get_hearthstone_dir_from_environment():
    try:
        return os.environ.get('HEARTHSTONE_HOME')
    except Exception as e:
        print(f"Error getting Hearthstone directory from environment: {e}")
        return None


def download_patch(destination):
    try:
        print("Downloading patch, please wait...")
        patch_url = "https://hearthstoneaccess.com/files/pre_patch.zip"
        with requests.get(patch_url, stream=True) as response:
            response.raise_for_status()
            with open(destination, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
    except Exception as e:
        print("Patch Download Error: could not download patch.")
        print("Here are some potential causes:")
        print("1. There may be something in your network that is interfering with the download.")
        print("2. The HearthstoneAccess site could currently be down.")
        print(f"Python Error downloading patch: {e}")
        exit_patcher()


def unzip_patch(hearthstone_dir):
    try:
        with zipfile.ZipFile(os.path.join(hearthstone_dir, 'temp.zip'), 'r') as zipped_patch:
            zipped_patch.extractall(hearthstone_dir)
    except Exception as e:
        print("Unzip Patch Error: Could not patch your game.")
        print("Here are some potential causes:")
        print(
            "1. Make sure Hearthstone is not running while attempting to use the patcher.")
        print("2. The patcher may not have privileges to modify files in the Hearthstone installation folder. Perhaps run it as an administrator.")
        print("3. Unlikely, but you may not have enough space on your disk drive.")
        print(f"Python Error unzipping patch: {e}")
        exit_patcher()


def patch(hearthstone_dir):
    try:
        print("Patching Hearthstone, please wait...")
        source = os.path.join(hearthstone_dir, 'patch')
        destination = hearthstone_dir

        for src_dir, dirs, files in os.walk(source):
            dst_dir = src_dir.replace(source, destination, 1)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            for file_ in files:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if os.path.exists(dst_file):
                    # in case of the src and dst are the same file
                    if os.path.samefile(src_file, dst_file):
                        continue
                    os.remove(dst_file)
                shutil.move(src_file, dst_dir)
        print("Successfully patched!")

    except Exception as e:
        print(f"Error applying patch: {e}")


def cleanup(hearthstone_dir):
    try:
        os.remove(hearthstone_dir + '\\temp.zip')
        shutil.rmtree(hearthstone_dir + '\\patch')

    except Exception as e:
        print("Cleanup Patch Error: Could not remove leftover patch files.")
        print("Here are some potential causes:")
        print("1. The patcher may not have privileges to modify files in the Hearthstone installation folder. Perhaps run it as an administrator.")
        print("2. Unlikely, but another program could be trying to modify the Hearthstone installation folder.")
        print(f"PythonError during cleanup: {e}")
        exit_patcher()


def move_patch_readme(hearthstone_dir):
    try:
        print("Do you want the readme with all the latest changes placed on your desktop?")
        want_readme = input(
            "Type y for yes, or any other character and press enter.")

        if not want_readme == "y":
            print("Okay, skipping readme.")
            os.remove(hearthstone_dir + '\\prepatch_readme.txt')
            return

        patch_readme_path = os.path.expanduser('~') + '\\Desktop'
        patch_readme_name = '\\prepatch_readme.txt'
        patch_readme_file = patch_readme_path + patch_readme_name

        if os.path.exists(patch_readme_file):
            os.remove(patch_readme_file)

        shutil.move(hearthstone_dir + patch_readme_name, patch_readme_file)

        print("Check your desktop for the patch's readme.")
        print("It is called prepatch_readme.txt")

    except Exception as e:
        print(
            "Make Readme Available Error: Could not move the patch readme to your desktop.")
        print("Here are some potential causes:")
        print("1. The patcher may not have privileges to modify files in the Hearthstone installation folder. Perhaps run it as an administrator.")
        print("2. Unlikely, but another program could be trying to modify the Hearthstone installation folder.")
        print("It should still be available in the Hearthstone installation directory.")
        print(f"Python Error moving patch readme: {e}")
        exit_patcher()


def exit_patcher():
    print("Press enter to exit...")
    input()
    sys.exit()


if __name__ == "__main__":
    ctypes.windll.kernel32.SetConsoleTitleW("HearthstoneAccess Beta Patcher")

    hearthstone_dir = determine_patch_destination()
    destination = hearthstone_dir + '\\temp.zip'
        
    download_patch(destination)
    unzip_patch(hearthstone_dir)
    patch(hearthstone_dir)
    cleanup(hearthstone_dir)
    move_patch_readme(hearthstone_dir)

    exit_patcher()
