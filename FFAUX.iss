; Bundled with FFmpeg Shared

; BUILD:
;   1. Build dist\FFAUX.exe with PyInstaller first.
;   2. Ensure FFAUX\bin\ffmpeg.exe and FFAUX\bin\ffprobe.exe exist.
;   3. Compile this file with Inno Setup.

#define MyAppName "FFAUX"
#define MyAppVersion "1.0.2"
#define MyAppPublisher "F. Audris Labs"
#define MyAppExeName "FFAUX.exe"

[Setup]
AppId={{82F058CE-ECCD-4DE8-B0B2-105C31C80E3E}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
UninstallDisplayName={#MyAppName}

; Metadata executable
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}

; Compile in x64 architectures
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Install per-user to avoid Program Files permission restrictions.
DefaultDirName={userappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest

LicenseFile=LICENSE

OutputBaseFilename=FFAUX-v1.0.2-GPL-Win-x64-Bundled-Installer
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
; Main application (PyInstaller output remains in the project-root dist folder)
Source: "dist\FFAUX.exe"; DestDir: "{app}"; Flags: ignoreversion

; License files
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_LICENSES.html"; DestDir: "{app}"; Flags: ignoreversion

; FFmpeg executables
Source: "FFAUX\bin\ffmpeg.exe"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "FFAUX\bin\ffprobe.exe"; DestDir: "{app}\bin"; Flags: ignoreversion

; FFmpeg libraries
Source: "FFAUX\bin\swresample-6.dll"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "FFAUX\bin\avutil-60.dll"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "FFAUX\bin\avdevice-62.dll"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "FFAUX\bin\swscale-9.dll"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "FFAUX\bin\avformat-62.dll"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "FFAUX\bin\avfilter-11.dll"; DestDir: "{app}\bin"; Flags: ignoreversion
Source: "FFAUX\bin\avcodec-62.dll"; DestDir: "{app}\bin"; Flags: ignoreversion

[Dirs]
; User-writable folders created during installation.
Name: "{app}\bin"
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
