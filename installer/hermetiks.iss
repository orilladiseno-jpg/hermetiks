; HERMETIKS Soundboard installer (Inno Setup 6). Build with:  py tools/build.py
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "HERMETIKS Soundboard"
#define Publisher "Orilla Estudio Creativo"
#define Collective "HERMETIKS COLLECTIVE"
#define AppURL "https://hermetiks.orilladiseno.cl"
#define AppExe "Hermetiks.exe"

[Setup]
AppId={{6F0B2C1E-7A55-4D5B-9B7A-3C8E5D0A4F21}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#Publisher} - {#Collective}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
AppCopyright=Copyright (c) 2026 {#Publisher}, part of {#Collective}, Chile
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#Publisher}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
DefaultDirName={autopf}\Hermetiks Soundboard
DefaultGroupName=HERMETIKS
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
SetupIconFile=..\hermetiks\resources\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardImageFile=wizard-large.bmp
WizardSmallImageFile=wizard-small.bmp
Compression=lzma2/max
SolidCompression=yes
OutputDir=..\dist
OutputBaseFilename=Hermetiks-Setup-{#AppVersion}
CloseApplications=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: "info-en.txt"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"; InfoBeforeFile: "info-es.txt"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"; InfoBeforeFile: "info-pt.txt"

[CustomMessages]
en.StartWithWindows=Start HERMETIKS with Windows
es.StartWithWindows=Iniciar HERMETIKS con Windows
pt.StartWithWindows=Iniciar o HERMETIKS com o Windows
en.RemoveUserData=Also delete your HERMETIKS settings and imported sounds?
es.RemoveUserData=¿Eliminar también tus ajustes y sonidos importados de HERMETIKS?
pt.RemoveUserData=Excluir também as suas configurações e sons importados do HERMETIKS?

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "{cm:StartWithWindows}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\Hermetiks\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; DestName: "THIRD_PARTY_NOTICES.txt"; Flags: ignoreversion
Source: "..\PRIVACY.md"; DestDir: "{app}"; DestName: "PRIVACY.txt"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Hermetiks"; \
  ValueData: """{app}\{#AppExe}"" --min"; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent) then
    if MsgBox(CustomMessage('RemoveUserData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      DelTree(ExpandConstant('{userappdata}\Hermetiks'), True, True, True);
end;
