; Inno Setup script for Live Translate Overlay
; External mode — copies files from setup.exe directory at install time.
; Place this .exe alongside the dist/LiveTranslateOverlay/ folder
; (or rename dist/ to LiveTranslateOverlay/ for distribution).

#define MyAppName "Lotus Translator"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "LotusTranslator"
#define MyAppURL "https://github.com/lotus-translate"
#define MyAppExeName "LiveTranslateOverlay.exe"

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
Compression=none
SolidCompression=no
DiskSpanning=no
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes
SetupLogging=yes
ShowLanguageDialog=no
MinVersion=10.0.10240
SetupIconFile=..\assets\icon.ico
WizardSmallImageFile=..\assets\logo.jpg
WizardImageFile=..\assets\thumbnail.jpg
WizardImageStretch=no

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