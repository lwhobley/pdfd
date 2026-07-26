; Inno Setup 6 script - PDF'D
; Compile with: iscc installer\setup.iss

#define MyAppName      "PDF'D"
#define MyAppVersion   "0.1.0"
#define MyAppPublisher "PDF'D"
#define MyAppExeName   "PDFD.exe"
#define MyDistDir      "..\dist\PDFD"

[Setup]
AppId={{7F4B2E3A-1C6D-4A8F-9E2B-3D5C7A0F1B4E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/pdfd
AppSupportURL=https://github.com/pdfd/issues
AppUpdatesURL=https://github.com/pdfd/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=PDFD-{#MyAppVersion}-win64-setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.10240
SetupIconFile=..\pdf_forge\assets\icons\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableWelcomePage=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
  Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"; \
  Flags: unchecked

[Files]
Source: "{#MyDistDir}\*"; \
  DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; \
  Filename: "{app}\{#MyAppExeName}"; \
  WorkingDir: "{app}"; \
  IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; \
  Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; \
  Filename: "{app}\{#MyAppExeName}"; \
  WorkingDir: "{app}"; \
  Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(MyAppName,'&','&&')}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: registry; \
  Root: HKCU; \
  Subkey: "Software\PDFD\PDFD"
