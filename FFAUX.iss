
#define MyAppName "FFAUX"
#define MyAppVersion "3"
#define MyAppPublisher "F. Audris Labs"
#define MyAppExeName "FFAUX.exe"

[Setup]
AppId={{82F058CE-ECCD-4DE8-B0B2-105C31C80E3E}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
UninstallDisplayName={#MyAppName}

VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

DefaultDirName={userappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest

LicenseFile=LICENSE

OutputBaseFilename=FFAUX-v{#MyAppVersion}-GPL-Win-x64-Installer
OutputDir=installer

Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

SetupIconFile=FFAUX\assets\icons\FFAUX.ico
UninstallDisplayIcon={app}\FFAUX.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\FFAUX.exe"; DestDir: "{app}"; Flags: ignoreversion

Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_LICENSES.html"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\config"
Name: "{app}\assets\templates"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\config"
Type: filesandordirs; Name: "{app}\assets\templates"
Type: dirifempty; Name: "{app}"

[Code]
procedure CurPageChanged(CurPageID: Integer);
var
  FreeBytes, TotalBytes: Int64;
  FreeMB: Integer;
begin
  if CurPageID = wpSelectDir then
  begin
    if GetSpaceOnDisk64(WizardDirValue, FreeBytes, TotalBytes) then
    begin
      FreeMB := FreeBytes div 1048576;

      WizardForm.DiskSpaceLabel.Caption :=
        WizardForm.DiskSpaceLabel.Caption + #13#10 +
        'Free space available: ' + IntToStr(FreeMB) + ' MB.';
    end;
  end;
end;
