; installer.iss
; ============================================================
; ImanAccount Installer v3.0 (OneFile)
; ============================================================

#define MyAppName "ImanAccount"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ImanAI"
#define MyAppURL "https://imanai.ir"
#define MyAppExeName "ImanAccount.exe"

[Setup]
AppId={{8F5B3D9A-4E2C-4F1B-9A8D-1C7E6B2A5D3F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=ImanAccount_Setup_v{#MyAppVersion}
SetupIconFile=Icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
MinVersion=6.1sp1
AppMutex=ImanAccountMutex
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.CreateDesktopIcon=Create a &desktop shortcut
english.LaunchApp=Launch ImanAccount

[Files]
; ═══════════════════════════════════════════════
; OneFile: فقط یه فایل exe
; ═══════════════════════════════════════════════
Source: "dist\ImanAccount.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM {#MyAppExeName} 2>nul"; Flags: runhidden

[UninstallDelete]
Type: files; Name: "{app}\Icon.ico"