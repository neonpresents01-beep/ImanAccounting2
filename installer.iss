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
AppUpdatesURL={#MyAppURL}

; ═══════════════════════════════════════════════
; مسیر نصب
; ═══════════════════════════════════════════════
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=no
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
ShowLanguageDialog=auto

; ═══════════════════════════════════════════════
; دسترسی
; ═══════════════════════════════════════════════
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; ═══════════════════════════════════════════════
; نسخه ویندوز
; ═══════════════════════════════════════════════
MinVersion=6.1sp1

; ═══════════════════════════════════════════════
; سایر
; ═══════════════════════════════════════════════
AppMutex=ImanAccountMutex
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "farsi"; MessagesFile: "compiler:Languages\Farsi.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
farsi.WelcomeLabel1=به نصب {#MyAppName} خوش آمدید
farsi.WelcomeLabel2=این برنامه {#MyAppName} نسخه {#MyAppVersion} را نصب می‌کند.
farsi.CreateDesktopIcon=ایجاد آیکون روی دسکتاپ
farsi.LaunchApp=اجرای ImanAccount
farsi.AdditionalIcons=آیکون‌های اضافی
farsi.DataDirPageTitle=انتخاب محل ذخیره داده‌ها
farsi.DataDirPageDesc=داده‌های شما (دیتابیس، لاگ، بکاپ) کجا ذخیره شوند؟

[Files]
; ═══════════════════════════════════════════════
; فایل‌های اصلی برنامه (OneDir)
; ═══════════════════════════════════════════════
Source: "dist\ImanAccount\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; ═══════════════════════════════════════════════
; منوی استارت
; ═══════════════════════════════════════════════
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Icon.ico"
Name: "{group}\حذف {#MyAppName}"; Filename: "{uninstallexe}"

; ═══════════════════════════════════════════════
; دسکتاپ
; ═══════════════════════════════════════════════
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\Icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

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

// ═══════════════════════════════════════════════
// صفحه انتخاب مسیر داده
// ═══════════════════════════════════════════════
procedure InitializeWizard();
begin
  DataDirPage := CreateInputDirPage(wpSelectDir,
    ExpandConstant('{cm:DataDirPageTitle}'),
    ExpandConstant('{cm:DataDirPageDesc}'),
    'مسیر پیش‌فرض: %APPDATA%\ImanAccount',
    False,
    'پوشه جدید');
  
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
    RegWriteStringValue(HKCU, 'Software\ImanAccount', 'InstallDate', GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':'));
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
  S := '📦 اطلاعات نصب:' + NewLine;
  S := S + Space + '• نسخه: {#MyAppVersion}' + NewLine;
  S := S + Space + '• پوشه نصب: {app}' + NewLine;
  S := S + NewLine;
  
  if DataDirPage.Values[0] <> '' then
  begin
    S := S + '📁 مسیر داده‌ها:' + NewLine;
    S := S + Space + '• ' + DataDirPage.Values[0] + NewLine;
    S := S + NewLine;
  end;
  
  S := S + '📞 پشتیبانی: {#MySupportPhone}' + NewLine;
  S := S + '📧 ایمیل: {#MySupportEmail}' + NewLine;
  
  Result := S;
end;