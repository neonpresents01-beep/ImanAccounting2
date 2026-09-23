; installer.iss
; ============================================================
; ImanAccount Installer
; نسخه 1.0.0
; ============================================================

#define MyAppName "ImanAccount"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ImanAI"
#define MyAppURL "https://imanai.ir"
#define MyAppExeName "ImanAccount.exe"
#define MySupportPhone "09937060447"
#define MySupportEmail "support@imanai.ir"

[Setup]
AppId={{8F5B3D9A-4E2C-4F1B-9A8D-1C7E6B2A5D3F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=ImanAccount_Setup_v{#MyAppVersion}
SetupIconFile=Icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=6.1sp1
AppMutex=ImanAccountMutex
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.WelcomeLabel1=Welcome to {#MyAppName} Setup
english.WelcomeLabel2=This will install {#MyAppName} version {#MyAppVersion} on your computer.
english.CreateDesktopIcon=Create a &desktop shortcut
english.LaunchApp=Launch ImanAccount

[Files]
Source: "dist\ImanAccount\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM {#MyAppExeName} 2>nul"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\fonts"
Type: filesandordirs; Name: "{app}\PyQt5"
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\Icon.ico"

[Code]
var
  DataDirPage: TInputDirWizardPage;

procedure InitializeWizard();
begin
  DataDirPage := CreateInputDirPage(wpSelectDir,
    'Select Data Directory',
    'Where should your data (database, logs, backups) be stored?',
    'Default: %APPDATA%\ImanAccount',
    False,
    'New Folder');
  
  DataDirPage.Add('');
  DataDirPage.Values[0] := ExpandConstant('{userappdata}\ImanAccount');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  DataDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    DataDir := DataDirPage.Values[0];
    
    RegWriteStringValue(HKCU, 'Software\ImanAccount', 'DataDir', DataDir);
    RegWriteStringValue(HKCU, 'Software\ImanAccount', 'Version', '{#MyAppVersion}');
    RegWriteStringValue(HKCU, 'Environment', 'IMANACCOUNT_DATA_DIR', DataDir);
    
    ForceDirectories(DataDir + '\logs');
    ForceDirectories(DataDir + '\backups');
  end;
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo,
  MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  S: String;
begin
  S := 'Installation Info:' + NewLine;
  S := S + Space + '- Version: {#MyAppVersion}' + NewLine;
  S := S + Space + '- Install to: {app}' + NewLine;
  S := S + NewLine;
  
  if DataDirPage.Values[0] <> '' then
  begin
    S := S + 'Data Directory:' + NewLine;
    S := S + Space + '- ' + DataDirPage.Values[0] + NewLine;
    S := S + NewLine;
  end;
  
  S := S + 'Support: {#MySupportEmail}' + NewLine;
  
  Result := S;
end;