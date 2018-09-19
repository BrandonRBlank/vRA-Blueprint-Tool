# --------------------------------------------------------------
# vRABlueprintTool.py
# Cyber Range Tool to download and upload vRA Blueprints
#   using CloudClient
# 
# Last modified: 5-June-2018
# --------------------------------------------------------------

import json
import os
import time
import subprocess
import fileinput
import threading
from tkinter import Tk, Label, Entry, RIGHT, RAISED, BOTH, StringVar, Text, Scrollbar, END
from tkinter.ttk import Style, Frame, Button


class Window(Tk, Frame):
    def __init__(self):
        Tk.__init__(self)

        self.style = Style()
        self.title("vRABlueprintTool")
        self.style.theme_use("default")

        container = Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (ConnectPage, MainPage, DownloadPage, UploadPage):
            pageName = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[pageName] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("ConnectPage")

    def show_frame(self, pageName):
        frame = self.frames[pageName]
        frame.tkraise()


class MainPage(Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.controller = controller

        frame = Frame(self, relief=RAISED, borderwidth=1)
        frame.pack(fill=BOTH, expand=True)

        self.label = Label(frame, text="vRABlueprintTool Main Page")
        self.label.pack(pady=10)

        self.toConnectPage = Button(frame, text="vRA Login Credentials", width=25,
                                    command=lambda: controller.show_frame("ConnectPage"))
        self.toDownloadPage = Button(frame, text="Blueprint Download", width=25,
                                     command=lambda: controller.show_frame("DownloadPage"))
        self.toUploadPage = Button(frame, text="Blueprint Upload", width=25,
                                   command=lambda: controller.show_frame("UploadPage"))

        self.toConnectPage.pack(padx=5, pady=5)
        self.toDownloadPage.pack(padx=5, pady=5)
        self.toUploadPage.pack(padx=5, pady=5)


class LicensePage(Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.controller = controller

        self.acceptButton = Button(self, text="Accept", command=lambda: self.accept_license(self.controller))
        self.acceptButton.pack(padx=5, pady=5)

    def accept_license(self, controller):
        pass


class ConnectPage(Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.controller = controller
        self.errorLoop = 0

        frame = Frame(self, relief=RAISED, borderwidth=1)
        frame.pack(fill=BOTH, expand=True)

        self.credentials = self.get_credentials()

        self.server_entry = Entry(frame, width=30, textvariable=StringVar(frame, value=self.credentials['server'][:-1]))
        self.tenant_entry = Entry(frame, width=30, textvariable=StringVar(frame, value=self.credentials['tenant'][:-1]))
        self.username_entry = Entry(frame, width=30, textvariable=StringVar(frame, value=self.credentials['username'][:-1]))
        self.password_entry = Entry(frame, width=30, textvariable=StringVar(frame, value=self.credentials['password'][:-1]))

        self.server_label = Label(frame, text="vRA Server:")
        self.tenant_label = Label(frame, text="vRA Tenant:")
        self.username_label = Label(frame, text="vRA Username:")
        self.password_label = Label(frame, text="vRA Password:")

        self.okButton = Button(self, text="SAVE", command=lambda: self.set_credentials(self.controller))

        self.server_label.pack(padx=5, pady=5)
        self.server_entry.pack(padx=5, pady=5)
        self.tenant_label.pack(padx=5, pady=5)
        self.tenant_entry.pack(padx=5, pady=5)
        self.username_label.pack(padx=5, pady=5)
        self.username_entry.pack(padx=5, pady=5)
        self.password_label.pack(padx=5, pady=5)
        self.password_entry.pack(padx=5, pady=5)
        self.okButton.pack(side=RIGHT)

    def set_credentials(self, controller):
        # While in 'fileinput' block, all prints write to new line to file
        for line in fileinput.input("../CloudClient.properties", inplace=True):
            if "vra_server=" in line:
                print("vra_server={}".format(self.server_entry.get()))
                continue
            if "vra_tenant=" in line:
                print("vra_tenant={}".format(self.tenant_entry.get()))
                continue
            if "vra_username=" in line:
                print("vra_username={}".format(self.username_entry.get()))
                continue
            if "vra_password=" in line:
                print("vra_password={}".format(self.password_entry.get()))
                continue

            # If no conditions met, simple writes old file line to new file
            print(line[:-1])

        controller.show_frame("MainPage")

    def get_credentials(self):
        credentials = {}
        self.cloud_client_setup()
        with open("../CloudClient.properties", 'r') as file:
            for line in file.readlines():
                if "vra_server=" in line:
                    credentials['server'] = line[11:]
                if "vra_tenant=" in line:
                    credentials['tenant'] = line[11:]
                if "vra_username=" in line:
                    credentials['username'] = line[13:]
                if "vra_password=" in line:
                    credentials['password'] = line[13:]
                else:
                    file.close()
        return credentials

    # Sets up Cloud Client for first time
    def cloud_client_setup(self):
        path = os.path.expanduser('~\.cloudclient\cloudclient.config')
        newPath = os.path.expanduser('~\.cloudclient\cloudclient_temp.config')
        generateConfig = "cloudclient.bat login autologinfile"

        if os.path.exists(path):
            self.set_config(path, newPath)
        else:
            print("Performing First Time Setup...")
            os.system(generateConfig)
            self.set_config(path, newPath)

    # Sets Cloud Client config file page size
    @staticmethod
    def set_config(path, newPath, size=2500):
        with open(path, 'r') as inFile:
            with open(newPath, 'w') as outFile:
                for i, line in enumerate(inFile):
                    if line == "default.page.size = 25\n":
                        outFile.write("default.page.size = {}\n".format(size))
                    else:
                        outFile.write(line)
        os.remove(path)
        os.rename(newPath, path)


class DownloadPage(Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.controller = controller
        self.outputState = False
        self.sem = threading.Semaphore()
        self.lock = 1

        frame1 = Frame(self, relief=RAISED, borderwidth=1)
        frame1.pack(fill=BOTH, expand=True)
        frame2 = Frame(self, relief=RAISED, borderwidth=1)
        frame2.pack(fill=BOTH, expand=True)
        frame3 = Frame(self, relief=RAISED, borderwidth=1)
        frame3.pack(fill=BOTH, expand=True)
        frame4 = Frame(self, relief=RAISED, borderwidth=1)
        frame4.pack(fill=BOTH, expand=True)

        self.outputBox = Text(self, height=15, width=40)
        self.outputBox.tag_config('error', background="yellow", foreground="red")
        self.vsb = Scrollbar(self, orient="vertical", command=self.outputBox.yview)
        self.outputBox.configure(yscrollcommand=self.vsb.set, state="disabled")
        self.vsb.pack(side="right", fill="y")
        self.outputBox.pack(side="left", fill="both", expand=True)

        self.oneBPName_entry = Entry(frame2, width=35)
        self.listBPPath_entry = Entry(frame3, width=35)

        self.oneBPNAme_label = Label(frame2, text="Blueprint Name:")
        self.listBPPath_label = Label(frame3, text="Blueprint List File Path:")

        self.allButton = Button(frame1, text="Download All Blueprints", width=30)
        self.allButton.configure(command=self.threader_all)
        self.oneButton = Button(frame2, text="Download One Blueprint", width=30)
        self.oneButton.configure(command=self.threader_one)
        self.listButton = Button(frame3, text="Download Blueprints From List", width=30)
        self.listButton.configure(command=self.threader_list)
        self.returnButton = Button(frame4, text="Go Back", command=lambda: self.controller.show_frame("MainPage"))

        self.oneBPNAme_label.pack(padx=5, pady=5)
        self.listBPPath_label.pack(padx=5, pady=5)

        self.oneBPName_entry.pack(padx=5, pady=5)
        self.listBPPath_entry.pack(padx=5, pady=5)

        self.allButton.pack(padx=5, pady=5)
        self.oneButton.pack(padx=5, pady=5)
        self.listButton.pack(padx=5, pady=5)
        self.returnButton.pack(padx=5, pady=10)

    # Starts thread for background process (also keeps lock so only one option may run at a time)
    def threader_all(self):
        if self.lock == 1:
            self.lock = 0
            thread = threading.Thread(target=self.download_all_blueprints)
            thread.daemon = True
            thread.start()
        return

    def threader_one(self):
        if self.lock == 1:
            self.lock = 0
            thread = threading.Thread(target=self.download_one_blueprint)
            thread.daemon = True
            thread.start()
        return

    def threader_list(self):
        if self.lock == 1:
            self.lock = 0
            thread = threading.Thread(target=self.download_blueprints)
            thread.daemon = True
            thread.start()
        return

    def download_all_blueprints(self):
        """
        Downloads all published blueprints from vRA
        Creates:
            output.json 		-JSON file with all published blueprints info (name, id, type, etc.)
                                *used to get all blueprint names to add to a vRA package

            blueprintLog.txt	-TEXT file with blueprints' names
                                *used when uploading blueprints to sort into proper service categories

            pkg.json            -JSON file with all packages in vRA (name, info, etc.)
                                *used to get the pkgId to download (with all blueprints contained)

            .zip of blueprints	-ZIP file with all downloaded blueprints
        """

        packageName = "vRAScriptPackage"
        packageID = ""
        dirPath = "\'" + os.path.dirname(os.path.realpath(__file__)) + "\\"
        getList = "cloudclient.bat vra content list --format JSON --export {}output.json\'".format(dirPath)
        makePackage = "cloudclient.bat vra package create --name {} --ids ".format(packageName)
        getPkgID = "cloudclient.bat vra package list --format JSON --export {}pkg.json\'".format(dirPath)
        blueprintLog = []

        cloud_client_run(self, getList, "Getting list of all blueprints in vRA", newLog=True)

        show_output(self, "Saving list of all blueprints as \'output.json\'")
        data = json.load(open('output.json'))

        show_output(self, "Creating list of blueprints")
        start_output(self, "Creating list of blueprints to download")
        for blueprint in data:
            makePackage += blueprint['id'] + ","
            blueprintLog.append(blueprint['name'])
        close_output(self)

        show_output(self, "Saving list of blueprints names as \'blueprintLog.txt\'")
        with open("blueprintLog.txt", 'w') as f:
            for BP in blueprintLog:
                f.write(BP + "\n")
            f.close()

        cloud_client_run(self, makePackage[:-1], "Making package of useful blueprints from vRA")

        # vRA sometimes takes a second or two to create package and update list
        time.sleep(5)

        cloud_client_run(self, getPkgID, "Getting blueprint packages from vRA as \'pkg.json\'")

        # Gets package ID to download (Can't download with package name)
        start_output(self, "Sorting packages and retrieving one for download")
        data = json.load(open('pkg.json'))
        for pkg in data:
            if pkg['name'] == packageName:
                packageID = str(pkg['id'])
        close_output(self)

        dirPath = "\'" + os.path.dirname(os.path.realpath(__file__)) + "\'"
        BPDownload = "cloudclient.bat vra package export --path {} --pkgId {}".format(dirPath, packageID)
        deletePkg = "cloudclient.bat vra package delete --pkgId {}".format(packageID)

        cloud_client_run(self, BPDownload, "Downloading blueprints")

        cloud_client_run(self, deletePkg, "Deleting package in vRA")

        show_output(self, "\nDownload Complete")
        self.lock = 1
        return

    def download_one_blueprint(self):
        """
        Downloads single inputted blueprint
        Creates:
            output.json 		-JSON file with all published blueprints info (name, id, type, etc.)
                                *used to get all blueprint names to add to a vRA package

            blueprintLog.txt	-TEXT file with blueprints' names
                                *used when uploading blueprints to sort into proper service categories

            pkg.json            -JSON file with all packages in vRA (name, info, etc.)
                                *used to get the pkgId to download (with all blueprints contained)

            .zip of blueprints	-ZIP file with all downloaded blueprints
        """

        if len(self.oneBPName_entry.get()) == 0:
            self.lock = 1
            return

        dirPath = "\'" + os.path.dirname(os.path.realpath(__file__)) + "\\"
        getList = "cloudclient.bat vra content list --format JSON --export {}output.json\'".format(dirPath)
        BPID = None

        cloud_client_run(self, getList, "Getting list of all blueprints in vRA", newLog=True)

        show_output(self, "Saving list of all blueprints as \'output.json\'")
        data = json.load(open('output.json'))

        start_output(self, "Searching for {}".format(self.oneBPName_entry.get()))
        for BP in data:
            if BP['name'].lower() == self.oneBPName_entry.get().lower():
                BPID = BP['id']
        close_output(self)

        with open("blueprintLog.txt", 'w') as f:
            f.write(self.oneBPName_entry.get() + "\n")
            f.close()

        dirPath = "\'" + os.path.dirname(os.path.realpath(__file__)) + "\'"
        if BPID is not None:
            contentBP = "cloudclient.bat vra content export --path {} --id {}".format(dirPath, BPID)
            cloud_client_run(self, contentBP, "Downloading {}".format(self.oneBPName_entry.get()))
            show_output(self, "\nDownload Complete")
        else:
            show_output(self, "\"{}\" not found in vRA\n".format(self.oneBPName_entry.get()), error=True)

        self.lock = 1
        return

    def download_blueprints(self):
        """
        Downloads blueprints from a text file
        Creates:
            output.json 		-JSON file with all published blueprints info (name, id, type, etc.)
                                *used to get all blueprint names to add to a vRA package

            blueprintLog.txt	-TEXT file with blueprints' names
                                *used when uploading blueprints to sort into proper service categories

            pkg.json            -JSON file with all packages in vRA (name, info, etc.)
                                *used to get the pkgId to download (with all blueprints contained)

            .zip of blueprints	-ZIP file with all downloaded blueprints
        """

        if len(self.listBPPath_entry.get()) == 0:
            self.lock = 1
            return

        packageName = "vRAScriptPackage"
        packageID = ""
        dirPath = "\'" + os.path.dirname(os.path.realpath(__file__)) + "\\"
        getList = "cloudclient.bat vra content list --format JSON --export {}output.json\'".format(dirPath)
        makePackage = "cloudclient.bat vra package create --name {} --ids ".format(packageName)
        getPkgID = "cloudclient.bat vra package list --format JSON --export {}pkg.json\'".format(dirPath)
        blueprintLog = []

        show_output(self, "Reading in list")
        try:
            with open(self.listBPPath_entry.get(), 'r') as f:
                blueprintsToGet = f.read().splitlines()
                f.close()
            blueprintsToGet = [element.lower() for element in blueprintsToGet]
        except IOError:
            show_output(self, "File not found", error=True)
            self.lock = 1
            return

        cloud_client_run(self, getList, "Getting list of all blueprints in vRA", newLog=True)

        show_output(self, "Saving list of all blueprints as \'output.json\'")
        data = json.load(open('output.json'))

        start_output(self, "Creating package list of blueprints to download")
        for blueprint in data:
            if str(blueprint['name']).lower() in blueprintsToGet:
                blueprintsToGet.remove(str(blueprint['name']).lower())
                blueprintLog.append(blueprint['name'])
                makePackage += blueprint['id'] + ","
        close_output(self)

        cloud_client_run(self, makePackage[:-1], "Making package of useful blueprints from vRA")

        show_output(self, "Saving list of useful blueprints names as \'blueprintLog.txt\'")
        with open("blueprintLog.txt", 'w') as f:
            for BP in blueprintLog:
                f.write(BP + "\n")
            f.close()

        # vRA sometimes takes a second or two to create package and update list
        time.sleep(5)

        cloud_client_run(self, getPkgID, "Getting blueprint packages from vRA as \'pkg.json\'")

        start_output(self, "Sorting packages and retrieving one for download")
        data = json.load(open('pkg.json'))
        for pkg in data:
            if pkg['name'] == packageName:
                packageID = str(pkg['id'])
        close_output(self)

        path = "\'" + os.path.dirname(os.path.realpath(__file__)) + "\'"
        BPDownload = "cloudclient.bat vra package export --path {} --pkgId {}".format(path, packageID)
        deletePkg = "cloudclient.bat vra package delete --pkgId {}".format(packageID)

        cloud_client_run(self, BPDownload, "Downloading blueprints")

        cloud_client_run(self, deletePkg, "Deleting package in vRA")

        if len(blueprintsToGet) != 0:
            show_output(self, "Following blueprints either misspelled or are not in vRA:")
            for missing in blueprintsToGet:
                show_output(self, "-{}".format(str(missing)), error=True)

        show_output(self, "\nDownload Complete")
        self.lock = 1
        return


class UploadPage(Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.controller = controller
        self.outputState = False
        self.sem = threading.Semaphore()
        self.lock = 1

        frame1 = Frame(self, relief=RAISED, borderwidth=1)
        frame1.pack(fill=BOTH, expand=True)
        frame2 = Frame(self, relief=RAISED, borderwidth=1)
        frame2.pack(fill=BOTH, expand=True)

        self.outputBox = Text(self, height=15, width=40)
        self.outputBox.tag_config('error', background="yellow", foreground="red")
        self.vsb = Scrollbar(self, orient="vertical", command=self.outputBox.yview)
        self.outputBox.configure(yscrollcommand=self.vsb.set, state="disabled")
        self.vsb.pack(side="right", fill="y")
        self.outputBox.pack(side="left", fill="both", expand=True)

        self.filePath_entry = Entry(frame1, width=35)
        self.filePath_label = Label(frame1, text="Blueprints .zip File Path:")

        self.fileButton = Button(frame1, text="Upload Blueprints", width=30)
        self.fileButton.configure(command=self.threader_upload)
        self.returnButton = Button(frame2, text="Go Back", command=lambda: self.controller.show_frame("MainPage"))

        self.filePath_label.pack(padx=5, pady=5)
        self.filePath_entry.pack(padx=5, pady=5)

        self.fileButton.pack(padx=5, pady=5)
        self.returnButton.pack(padx=5, pady=10)

    def threader_upload(self):
        if self.lock == 1:
            self.lock = 0
            thread = threading.Thread(target=self.upload_blueprints)
            thread.daemon = True
            thread.start()
        return

    def upload_blueprints(self):
        """
        Uploads blueprints (downloaded with this tool) to vRA server
        Creates:
            services.json 		-JSON file with all Catalog Services info
                                *used to check fo service duplicates

            blueprintLog.txt	-TEXT file with blueprints' names
                                *used when uploading blueprints to sort into proper service categories
        """
        if len(self.filePath_entry.get()) == 0:
            self.lock = 1
            return

        blueprintID = []
        file = self.filePath_entry.get()

        show_output(self, "Reading blueprintLog.txt")
        try:
            with open("blueprintLog.txt", 'r') as f:
                blueprintID = f.read().splitlines()
        except IOError:
            show_output(self, "blueprintLog.txt not found, blueprints will not be sorted", error=True)

        if file[-4:] != ".zip":
            file += ".zip"

        zipPath = "\'" + os.path.dirname(os.path.realpath(__file__)) + "\\"
        importBlueprints = "cloudclient.bat vra content import --path {}\' --resolution SKIP --precheck WARN"\
            .format(zipPath + file)

        # TODO: Need to find a way to ensure all blueprints were imported
        uploadRep = int(len(blueprintID) / 25)
        if uploadRep == 0:
            uploadRep = 1
        for x in range(0, uploadRep):
            cloud_client_run(self, importBlueprints, "Importing Blueprints to vRA ({}/{})".format(x + 1, uploadRep),
                             newLog=True)
        close_output(self)

        show_output(self, "\nUpload Complete")
        self.lock = 1
        return


# Creates thread to generate output to GUI; acquires shared output semaphore
def start_output(self, text):
    outputThread = threading.Thread(target=open_output, args=(self, text))
    outputThread.daemon = True
    self.sem.acquire()
    outputThread.start()
    return


# Output loop; adds ellipses to output until background process is completed
def open_output(self, text):
    self.outputState = True
    output = [text, ".", ".", "."]
    while self.outputState:
        for i in range(5):
            if i == 4:
                self.outputBox.configure(state="normal")
                self.outputBox.delete("insert linestart", "insert lineend")
                self.outputBox.configure(state="disabled")
                continue
            self.outputBox.configure(state="normal")
            self.outputBox.insert(END, output[i])
            self.outputBox.configure(state="disabled")
            time.sleep(1)

    self.outputBox.configure(state="normal")
    self.outputBox.delete("insert linestart", "insert lineend")
    self.outputBox.insert(END, "{}...DONE\n".format(text))
    self.outputBox.see(END)
    self.outputBox.configure(state="disabled")
    self.sem.release()
    return


# Closes output loop
def close_output(self):
    self.outputState = False
    return


# Atomic output of single line (to GUI)
def show_output(self, text, error=False):
    self.sem.acquire()
    self.outputBox.configure(state="normal")
    if error:
        self.outputBox.insert(END, "{}\n".format(text), 'error')
        self.outputBox.see(END)
    else:
        self.outputBox.insert(END, "{}...DONE\n".format(text))
        self.outputBox.see(END)
    self.outputBox.configure(state="disabled")
    self.sem.release()
    return


# Checks if CloudClient process completed successfully
def proc_check(self, data):
    if "Authentication Error" in data[-1].decode("utf-8"):
        close_output(self)
        show_output(self, "\nERROR: Invalid login credentials\n", error=False)
        return False
    return True


# Runs Cloud Client commands and captures output
def cloud_client_run(self, command, output, newLog=False):
    start_output(self, output)
    rawCMD = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rawCMD = rawCMD.stdout.readlines()
    if not proc_check(self, rawCMD):
        return False
    close_output(self)

    if newLog:
        append_output_log(rawCMD, new=True)
    else:
        append_output_log(rawCMD)
    return True


# Output log (for Debugging)
def append_output_log(log, new=False):
    if new:
        with open("outputLog.txt", 'w') as f:
            for line in log:
                f.write("{}\n".format(line.decode("utf-8")))
            f.close()
    else:
        with open("outputLog.txt", 'a+') as f:
            for line in log:
                f.write("{}\n".format(line.decode("utf-8")))
            f.close()
    return


if __name__ == '__main__':
    app = Window()
    app.geometry("570x570")
    app.resizable(0, 0)
    app.mainloop()
