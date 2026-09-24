; installer.iss
; ============================================================
; ImanAccount Installer v3.0 (OneFile)
; English Only - GitHub Actions Compatible
; ============================================================

#define MyAppName "ImanAccount"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ImanAI"
#define MyAppURL "https://imanai.ir"
#define MyAppExeName "ImanAccount.exe"
#define MySupportEmail "support@imanai.ir"

[Setup]
; ═══════════════════════════════════════════════
; اطلاعات پایه
; ═══════════════════════════════════════════════
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

; ═══════════════════════════════════════════════
; خروجی
; ═══════════════════════════════════════════════
OutputDir=installer_output
OutputBaseFilename=ImanAccount_Setup_v{#MyAppVersion}
SetupIconFile=Icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}

; ═══════════════════════════════════════════════
; فشرده‌سازی
; ═══════════════════════════════════════════════
Compression=lzma2/max
SolidCompression=yes

; ═══════════════════════════════════════════════
; ظاهر
; ═══════════════════════════════════════════════
WizardStyle=modern
ShowLanguageDialog=no

; ═══════════════════════════════════════════════
; دسترسی
; ═══════════════════════════════════════════════
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; ═══════════════════════════════════════════════
; حداقل ویندوز
; ═══════════════════════════════════════════════
MinVersion=6.1sp1

; ═══════════════════════════════════════════════
; سایر
; ═══════════════════════════════════════════════
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
english.SelectDataDir=Select Data Directory
english.DataDirDesc=Where should your data (database, logs, backups) be stored?

[Files]
; ═══════════════════════════════════════════════
; OneFile: فقط فایل exe
; ═══════════════════════════════════════════════
Source: "dist\ImanAccount.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "Icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; ═══════════════════════════════════════════════
; منوی استارت
; ═══════════════════════════════════════════════
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Icon.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; ═══════════════════════════════════════════════
; دسکتاپ
; ═══════════════════════════════════════════════
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM {#MyAppExeName} 2>nul"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
; ═══════════════════════════════════════════════
; پاک کردن فایل‌ها
; ═══════════════════════════════════════════════
Type: files; Name: "{app}\Icon.ico"

[Code]
var
  DataDirPage: TInputDirWizardPage;

// ═══════════════════════════════════════════════
// صفحه انتخاب مسیر داده
// ═══════════════════════════════════════════════
procedure InitializeWizard();
begin
  DataDirPage := CreateInputDirPage(wpSelectDir,
    ExpandConstant('{cm:SelectDataDir}'),
    ExpandConstant('{cm:DataDirDesc}'),
    'Default: %APPDATA%\ImanAccount',
    False,
    'New Folder');
  
  DataDirPage.Add('');
  DataDirPage.Values[0] := ExpandConstant('{userappdata}\ImanAccount');
end;

// ═══════════════════════════════════════════════
// ذخیره مسیر در Registry
// ═══════════════════════════════════════════════
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

// ═══════════════════════════════════════════════
// خلاصه قبل از نصب
// ═══════════════════════════════════════════════
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo,
  MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  S: String;
begin
  S := 'Installation Summary:' + NewLine;
  S := S + Space + '- App: {#MyAppName} v{#MyAppVersion}' + NewLine;
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