import wx
import os
import ctypes
import requests
import shutil
import zipfile
import subprocess


class PatchApp(wx.Frame):
    def __init__(self, parent, title):
        super(PatchApp, self).__init__(parent, title=title, size=(500, 300))
        self.InitUI()
        self.Centre()
        self.Show()

    def InitUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.patch_button = wx.Button(panel, label='Start Patch')
        self.close_button = wx.Button(panel, label='Close')
        self.status_label = wx.StaticText(panel, label="Status:")
        self.status_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE|wx.TE_READONLY)

        self.patch_button.Bind(wx.EVT_BUTTON, self.onPatchButton)
        self.close_button.Bind(wx.EVT_BUTTON, self.onCloseButton)

        hbox.Add(self.patch_button, flag=wx.LEFT|wx.BOTTOM, border=5)
        hbox.Add(self.close_button, flag=wx.LEFT|wx.BOTTOM, border=5)
        vbox.Add(self.status_text, proportion=1, flag=wx.EXPAND, border=5)

        vbox.Add(hbox, proportion=0, flag=wx.ALL|wx.EXPAND, border=10)
        panel.SetSizer(vbox)

    def onPatchButton(self, event):
        self.start_patching_process()

    def onCloseButton(self, event):
        self.Close()

    def determine_patch_destination(self):
        hearthstone_default_dir = "C:\\Program Files (x86)\\Hearthstone"
        hearthstone_default_dir_exists = os.path.exists(hearthstone_default_dir)
        hearthstone_dir_env_is_set = bool(self.get_hearthstone_dir_from_environment())

        if not hearthstone_default_dir_exists and not hearthstone_dir_env_is_set:
            hearthstone_dir = self.get_hearthstone_dir_from_user()

        elif not hearthstone_default_dir_exists and hearthstone_dir_env_is_set:
            hearthstone_dir = self.get_hearthstone_dir_from_environment()

        else:
            hearthstone_dir = hearthstone_default_dir

        return hearthstone_dir

    def get_hearthstone_dir_from_environment(self):
        process = subprocess.run(
            "powershell.exe [System.Environment]::GetEnvironmentVariable('HEARTHSTONE_HOME', 'User')",
            capture_output=True)
        hearthstone_dir = process.stdout.decode()
        return hearthstone_dir.strip()

    def get_hearthstone_dir_from_user(self):
        dlg = wx.DirDialog(self, "Choose your Hearthstone installation folder:", style=wx.DD_DEFAULT_STYLE)

        if dlg.ShowModal() == wx.ID_OK:
            hearthstone_dir = dlg.GetPath()
        else:
            hearthstone_dir = None

        dlg.Destroy()

        while hearthstone_dir is None or not os.path.exists(hearthstone_dir):
            dlg = wx.MessageDialog(self, "The patcher couldn't find your Hearthstone installation folder. Please choose it again.", "Invalid Folder", wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()

            dlg = wx.DirDialog(self, "Choose your Hearthstone installation folder:", style=wx.DD_DEFAULT_STYLE)
            if dlg.ShowModal() == wx.ID_OK:
                hearthstone_dir = dlg.GetPath()
            else:
                hearthstone_dir = None
            dlg.Destroy()

        process = subprocess.run(
            f"powershell.exe [System.Environment]::SetEnvironmentVariable('HEARTHSTONE_HOME', '{hearthstone_dir}', 'User')",
            capture_output=True)

        return hearthstone_dir

    def download_file_from_google_drive(self, id, destination):
        URL = "https://docs.google.com/uc?export=download"

        session = requests.Session()

        response = session.get(URL, params={'id': id}, stream=True)
        token = self.get_confirm_token(response)

        if token:
            params = {'id': id, 'confirm': token}
            response = session.get(URL, params=params, stream=True)
        self.save_response_content(response, destination)

    def get_confirm_token(self, response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value
        return None

    def save_response_content(self, response, destination):
        CHUNK_SIZE = 32768

        with open(destination, "wb") as f:
            for chunk in response.iter_content(CHUNK_SIZE):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

    def unzip_patch(self, hearthstone_dir):
        with zipfile.ZipFile(os.path.join(hearthstone_dir, 'temp.zip'), 'r') as zipped_patch:
            zipped_patch.extractall(hearthstone_dir)

    def patch(self, hearthstone_dir):
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

    def cleanup(self, hearthstone_dir):
        os.remove(hearthstone_dir + '\\temp.zip')
        shutil.rmtree(hearthstone_dir + '\\patch')

    def move_patch_readme(self, hearthstone_dir):
        dlg = wx.MessageDialog(self, "Do you want the readme with all the latest changes placed on your desktop?", "Readme", wx.YES_NO | wx.ICON_QUESTION)
        want_readme = dlg.ShowModal()
        dlg.Destroy()

        if want_readme == wx.ID_NO:
            os.remove(hearthstone_dir + '\\prepatch_readme.txt')
            return

        patch_readme_path = os.path.expanduser('~') + '\\Desktop'
        patch_readme_name = '\\prepatch_readme.txt'
        patch_readme_file = patch_readme_path + patch_readme_name

        if os.path.exists(patch_readme_file):
            os.remove(patch_readme_file)

        shutil.move(hearthstone_dir + patch_readme_name, patch_readme_file)

    def start_patching_process(self):
        ctypes.windll.kernel32.SetConsoleTitleW("HearthstoneAccess Beta Patcher")

        hearthstone_dir = self.determine_patch_destination()

        self.update_status("Downloading Patch")
        self.download_file_from_google_drive('1L6K6tVsXpFtPxUSgLTpxtNXVfN24Ym4l', hearthstone_dir + '\\temp.zip')
        self.update_status("Unzipping Patch")
        self.unzip_patch(hearthstone_dir)
        self.update_status("Patching")
        self.patch(hearthstone_dir)
        self.update_status("Cleaning up")
        self.cleanup(hearthstone_dir)
        self.move_patch_readme(hearthstone_dir)
        self.update_status("Patch Completed")

    def update_status(self, msg):
        self.status_text.AppendText(msg + "\n")
        self.Refresh()
        self.Update()

app = wx.App()
PatchApp(None, title='HearthstoneAccess Beta Patcher')
app.MainLoop()
