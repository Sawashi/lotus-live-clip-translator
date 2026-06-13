; Inno Setup script for Lotus Translator
; External mode — copies files from setup.exe directory at install time.
; With Python pre-check and auto-download via Windows URLDownloadToFile API.

#define MyAppName "Lotus Translator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "LotusTranslator"
#define MyAppURL "https://github.com/lotus-translate"
#define MyAppExeName "LiveTranslateOverlay.exe"
#define PythonVersion "3.10.11"
#define PythonInstaller "python-3.10.11-amd64.exe"

[Setup]
AppId={{LOTUS-TRANSLATE-2026-A1B2C3D4E5F6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName=C:\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=LiveTranslateOverlay_Setup_v{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
DiskSpanning=yes
WizardStyle=modern
PrivilegesRequired=none
DisableProgramGroupPage=yes
SetupLogging=yes
ShowLanguageDialog=no
MinVersion=10.0.10240
SetupIconFile=..\assets\icon.ico
WizardSmallImageFile=..\assets\logo.jpg
WizardImageFile=..\assets\thumbnail.jpg
WizardImageStretch=no
AppendDefaultDirName=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Files]
; Copy everything from LiveTranslateOverlay folder beside this setup.exe
Source: "{src}\LiveTranslateOverlay\*"; DestDir: "{app}"; Flags: external recursesubdirs createallsubdirs uninsremovereadonly

; Grant write permission so app can update models/cache at runtime
[Dirs]
Name: "{app}"; Permissions: users-modify

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Grant Users full mod on entire app dir (recursive) — models/cache need writes
Filename: "{sys}\icacls.exe"; Parameters: """{app}"" /grant ""Users:(OI)(CI)M"" /T /Q"; Flags: runhidden waituntilterminated; StatusMsg: "Setting permissions..."
; Launch app after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent shellexec

[UninstallRun]
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden

[Code]
var
  LogFile: string;
  PythonDownloadPage: TWizardPage;
  PythonChecked: Boolean;

const
  PythonRegKey = 'SOFTWARE\Python\PythonCore\3.10\InstallPath';
  PythonRegKey64 = 'SOFTWARE\Python\PythonCore\3.10\InstallPath';

function IsPythonInstalled(): Boolean;
var
  InstallPath: string;
begin
  Result := False;
  // Check 64-bit Python 3.10
  if RegQueryStringValue(HKLM64, PythonRegKey64, '', InstallPath) then
  begin
    if FileExists(InstallPath + 'python.exe') then
    begin
      Result := True;
      Log('Python 3.10 found at: ' + InstallPath);
      Exit;
    end;
  end;
  // Check 32-bit Python 3.10
  if RegQueryStringValue(HKLM32, PythonRegKey, '', InstallPath) then
  begin
    if FileExists(InstallPath + 'python.exe') then
    begin
      Result := True;
      Log('Python 3.10 (32-bit) found at: ' + InstallPath);
      Exit;
    end;
  end;
  // Check current user hive
  if RegQueryStringValue(HKCU64, PythonRegKey64, '', InstallPath) then
  begin
    if FileExists(InstallPath + 'python.exe') then
    begin
      Result := True;
      Log('Python 3.10 found (HKCU): ' + InstallPath);
      Exit;
    end;
  end;
  Log('Python 3.10 not found in registry');
end;

function URLDownloadToFile(pCaller: LongWord; szURL: string; szFileName: string; dwReserved: LongWord; lpfnCB: LongWord): Integer;
  external 'URLDownloadToFileW@urlmon.dll stdcall';

function DownloadFile(Url, FileName: string): Boolean;
var
  RetVal: Integer;
begin
  Result := False;
  Log('Downloading: ' + Url);
  Log('Saving to: ' + FileName);
  try
    RetVal := URLDownloadToFile(0, Url, FileName, 0, 0);
    if RetVal = 0 then
    begin
      Result := True;
      Log('Download completed successfully');
    end
    else
    begin
      Log('URLDownloadToFile returned: ' + IntToStr(RetVal));
    end;
  except
    Log('Download exception occurred');
  end;
end;

function DownloadPython(): Boolean;
var
  DownloadUrl: string;
  TempPath: string;
  ResultCode: Integer;
begin
  Result := False;
  DownloadUrl := 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe';
  TempPath := ExpandConstant('{tmp}\{#PythonInstaller}');

  Log('Downloading Python from: ' + DownloadUrl);
  Log('Saving to: ' + TempPath);

  if not DownloadFile(DownloadUrl, TempPath) then
  begin
    Log('Failed to download Python installer');
    MsgBox('Failed to download Python installer. Please install Python 3.10 manually from python.org', mbError, MB_OK);
    Exit;
  end;

  Log('Python installer downloaded successfully');

  // Run the installer silently with minimal options
  if Exec(TempPath, '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0',
         '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      Log('Python installation completed successfully');
      Result := True;
    end
    else
    begin
      Log('Python installer returned error code: ' + IntToStr(ResultCode));
      MsgBox('Python installation returned error code ' + IntToStr(ResultCode) +
             '. You may need to install it manually.', mbError, MB_OK);
    end;
  end
  else
  begin
    Log('Failed to execute Python installer');
    MsgBox('Failed to start Python installer. Please install Python 3.10 manually.', mbError, MB_OK);
  end;
end;

procedure InitializeWizard;
begin
  LogFile := ExpandConstant('{localappdata}\LiveTranslateOverlay\logs\install.log');
  CreateDir(ExpandConstant('{localappdata}\LiveTranslateOverlay'));
  CreateDir(ExpandConstant('{localappdata}\LiveTranslateOverlay\logs'));
  Log('Installation started at ' + GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':'));

  // Check Python
  if IsPythonInstalled() then
  begin
    Log('Python 3.10 detected — skipping download');
    PythonChecked := True;
    Exit;
  end;

  Log('Python 3.10 NOT detected');

  // Create custom page offering to download Python
  PythonDownloadPage := CreateOutputMsgPage(
    wpWelcome,
    'Python 3.10 Required',
    'Lotus Translator needs Python 3.10 to run',
    'Python 3.10 was not found on your system.'#13#10 +
    'Lotus Translator requires Python 3.10 to function.'#13#10#13#10 +
    'The installer can download and install it for you now.'#13#10#13#10 +
    'Click "Next" to download and install Python 3.10 automatically.'#13#10 +
    'Or click "Cancel" to abort and install Python manually.'
  );
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  // Handle the Python check page
  if (CurPageID = PythonDownloadPage.ID) then
  begin
    Log('User proceeding with Python download');
    try
      if DownloadPython then
      begin
        PythonChecked := True;
        Log('Python download/install completed');
      end
      else
      begin
        Log('Python download/install failed');
        MsgBox('Python installation failed. You can install Python 3.10 manually and run the installer again.',
               mbError, MB_OK);
        Result := False;
      end;
    except
      Log('Python download/install raised exception');
      MsgBox('Python download/install failed. Please install Python 3.10 manually.',
             mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    CreateDir(ExpandConstant('{app}\logs'));
    Log('Installation completed successfully');

    // Write install marker
    SaveStringToFile(ExpandConstant('{app}\install_log.txt'),
      'Installed: ' + GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':') + #13#10 +
      'Python checked: ' + IntToStr(Ord(PythonChecked)) + #13#10 +
      'Path: ' + ExpandConstant('{app}'),
      False);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Log('Uninstallation completed');
  end;
end;