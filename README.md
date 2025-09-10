## About IDP-Scanner
IDP-Scanner provides UI-based functionality to scan the XML files of <a href="https://github.com/papyri/idp.data">idp.data</a> 
for potential issues. An integrated XML editor allows you to directly correct any issues line by line. You can export
your sessions to let a co-worker continue your work or to externally work with the data provided by IDP-Scanner.

## Running IDP-Scanner
### Requirements
- **OS**: Windows, Linux, macOS
- **Python**: Python 3.9 or newer is required
- **GitHub**: Local directory containing your fork
  (<a href="https://docs.github.com/en/desktop/adding-and-cloning-repositories/cloning-and-forking-repositories-from-github-desktop">Guide: Forking with GitHub Desktop</a>)
of the <a href="https://github.com/papyri/idp.data">idp.data repository</a>
### Installation
**Recommended**:
- Clone this repository or download files from a release version
- Run "pip install -r requirements.txt"
- Execute main.py (Windows: "py main.py", Linux/macOS: "python main.py")

**For users on Windows who do not have any experience with Python**:
- Download IDP-Scanner.exe
- Run IDP-Scanner.exe

## User Interface (UI) - Quick Guide
### Main Menu
- When starting IDP-Scanner, you will see the **Main Menu** page.
- *(Optional)* Expand **Session Management** to be able to export your last session or import a session (which can be a
session shared by a co-worker or a session you exported yourself)
- Click on the **IDP.DATA DIRECTORY button** to choose the
directory containing your fork of the <a href="https://github.com/papyri/idp.data">idp.data repository</a>. 
- Set a **Target** (Complete Scan / DCLP / DDbDP) that will determine which files will be scanned for issues. 
- *(Optional)* Expand the **Expert Settings** to further limit your target corpus either by applying a filter or limiting 
the processing range.
- Choose an **xml:lang Preset** that fits your intentions (*Exclude Latin*: XML files containing Latin as xml:lang will
be excluded; *Greek Only*: XML files which do not contain Greek as the only defined xml language will be excluded). 
Usually, *Exclude Latin* is the best choice.
- Click the **"Scan" button** to start scanning your target corpus.

### Scanning
- Please be patient while XML files are being scanned for issues. 
- This may take a while and depends on factors such as your CPU, the size of your target corpus and the file size of 
files in your corpus.

### Issue View
- Click on the **"Back to Main Menu" button** on the top left to return to the main menu. All **Potential Issues** of 
the line shown in the **XML Editor** are listed beneath it. 
- You can correct an issue directly in the **XML Editor**. 
- While editing, press CTRL+S to save any changes you made or press CTRL+O to open the whole XML file in the default editor 
of your OS. To set the theme of the editor, click on the **wheel button** and choose your preferred style in the dropdown
menu **Editor Theme**.
- In the bottom center, you can find a **button group** which allows you to navigate through issues, open the whole XML 
file, apply a filter or save any changes you made. Hover over each button to read a brief description of its purpose. 
Press the Page Down key on your keyboard or click the respective button to navigate to the next issue, press Page Up or 
click the respective button to go back to the previous issue.
- Next to the button group, you can use the **input field** to jump to an issue. To do that, write a number (or use the small
triangular buttons to increase or decrease the current number) before confirming with enter. A **circular progress
indicator** on the right shows how far you have progressed in your target corpus.

### Exiting
- Close the program by clicking the default "X" button of your OS on the top right of the application window. 
- Your progress and filter settings are automatically saved to .nicegui/storage-general.json. 
- After restarting the program,
you will be asked if you wish to continue your last session. Click the **"Yes" button** to do so. Be aware that your 
last session will be overwritten should you decide to start a new session. If you clicked the **"No" button** by 
mistake, simply restart the program.
- If you want to start a new session but also keep your current session, use the **"Export Session" button** in the 
**Main Menu** under **Session Management**.
