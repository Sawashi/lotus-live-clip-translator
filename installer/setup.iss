; Inno Setup script for Live Translate Overlay
; Build with: iscc setup.iss
; For large bundles, uses disk spanning to stay under 2GB per part

#define MyAppName "Live Translate Overlay"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "LotusTranslator"
#define MyAppURL "https://github.com/lotus-translate"
#define MyAppExeName "LiveTranslateOverlay.exe"
#define MyAppAssocName MyAppName + " File"

[Setup]
AppId={{LOTUS-TRANSLATE-2026-A1B2C3D4E5F6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=LiveTranslateOverlay_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
DiskSpanning=yes
DiskSliceSize=2000000000  ; 2GB per disk
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes
SetupLogging=yes
ShowLanguageDialog=no

; Minimum Windows version: Windows 10
MinVersion=10.0.10240

; Branding images
SetupIconFile=..\assets\icon.ico
WizardSmallImageFile=..\assets\logo.jpg
WizardImageFile=..\assets\thumbnail.jpg
WizardImageStretch=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Files]
; Main executable
Source: "..\dist\LiveTranslateOverlay\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Configuration files
Source: "..\config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\languages.json"; DestDir: "{app}"; Flags: ignoreversion

; Model files (all bundled)
Source: "..\models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs

; All other supporting files from PyInstaller build
Source: "..\dist\LiveTranslateOverlay\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Installer helper scripts
Source: "..\installer\bootstrap_setup.py"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "..\installer\preinstall_check.py"; DestDir: "{app}\installer"; Flags: ignoreversion
Source: "..\installer\cuda_setup.bat"; DestDir: "{app}\installer"; Flags: ignoreversion

; VC++ Redistributable (bundled for offline install)
Source: "..\installer\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall; Check: Not VCInstalled

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Install VC++ Redist if needed (before app launch)
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Visual C++ Redistributable..."; Flags: skipifdoesntexist; Check: Not VCInstalled
; Launch app after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent shellexec

[UninstallRun]
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden

[Code]
var
  LogFile: string;

function Not VCInstalled: Boolean;
var
  Success: Boolean;
  Msg: String;
begin
  // Check if VC++ 2015-2022 Redist is installed
  Success := RegKeyExists(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64');
  if not Success then
    Success := RegKeyExists(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64');
  Result := not Success;
end;

procedure InitializeWizard;
begin
  LogFile := ExpandConstant('{localappdata}\LiveTranslateOverlay\logs\install.log');
  CreateDir(ExpandConstant('{localappdata}\LiveTranslateOverlay'));
  CreateDir(ExpandConstant('{localappdata}\LiveTranslateOverlay\logs'));
  Log('Installation started at ' + GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    CreateDir(ExpandConstant('{app}\logs'));
    CreateDir(ExpandConstant('{app}\installer'));
    Log('Installation completed successfully');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    Log('Uninstallation completed');
  end;
end;