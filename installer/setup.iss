; Inno Setup script for Live Translate Overlay
; Build with: iscc setup.iss

#define MyAppName "Live Translate Overlay"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "LiveTranslateOverlay"
#define MyAppURL "https://github.com/livetranslateoverlay"
#define MyAppExeName "LiveTranslateOverlay.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=..\dist
OutputBaseFilename=LiveTranslateOverlay_Setup_{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes

; Minimum Windows version: Windows 10
MinVersion=10.0.10240

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: "installmodels"; Description: "Download translation language packages (requires internet)"; GroupDescription: "Optional downloads:"; Flags: unchecked

[Files]
; Main executable
Source: "..\dist\LiveTranslateOverlay\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Configuration files
Source: "..\config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\languages.json"; DestDir: "{app}"; Flags: ignoreversion

; faster-whisper model files (bundled)
Source: "..\models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs

; All other supporting files
Source: "..\dist\LiveTranslateOverlay\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent shellexec

[Code]
var
  ModelDownloadPage: TOutputProgressWizardPage;
  DownloadSuccessful: Boolean;

procedure InitializeWizard;
begin
  DownloadSuccessful := False;
end;

function GetAppDataDir: string;
begin
  Result := ExpandConstant('{localappdata}\LiveTranslateOverlay');
end;

function GetModelDir: string;
begin
  Result := ExpandConstant('{app}\models');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create log directory
    CreateDir(GetAppDataDir + '\logs');
    
    // If translation packages task is selected, attempt download
    if IsTaskSelected('installmodels') then
    begin
      // This would run a post-install script to download Argos packages
      // For a production installer, bundle these or run a Python helper
      Log('Translation package download task selected - would download on first launch');
    end;
  end;
end;