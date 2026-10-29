; Converta setup wizard. Built by build.ps1, which passes /DAppVersion.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6F1E3B52-8C4D-4E8A-9B7A-2C5D1F0A9E31}
AppName=Converta
AppVersion={#AppVersion}
AppVerName=Converta {#AppVersion}
AppPublisher=Eren
DefaultDirName={autopf}\Converta
DefaultGroupName=Converta
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
SetupIconFile=..\assets\converta.ico
UninstallDisplayIcon={app}\Converta.exe
UninstallDisplayName=Converta
OutputDir=..\dist
OutputBaseFilename=Converta-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
german.RegisterMenu=Rechtsklick-Menü wird eingerichtet...
english.RegisterMenu=Setting up the right-click menu...
german.NoOffice=Für Word-, Excel- und PowerPoint-Umwandlungen wird Microsoft Office oder das kostenlose LibreOffice benötigt.%n%nAlle anderen Umwandlungen funktionieren sofort.%n%nLibreOffice jetzt herunterladen?
english.NoOffice=Converting Word, Excel and PowerPoint files needs Microsoft Office or the free LibreOffice.%n%nAll other conversions work right away.%n%nDownload LibreOffice now?
german.FinishedHint=Rechtsklicke eine Datei und wähle „Converta“ (unter „Weitere Optionen anzeigen“ oder mit Shift + Rechtsklick).
english.FinishedHint=Right-click a file and choose "Converta" (under "Show more options" or with Shift + right-click).

[InstallDelete]
; leftovers of older versions (bundled ffmpeg, previous program files)
Type: filesandordirs; Name: "{app}\bin"
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\build\pyinstaller\Converta\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[UninstallDelete]
; ffmpeg downloaded on first use, LibreOffice profile
Type: filesandordirs; Name: "{localappdata}\Converta"

[Run]
Filename: "{app}\Converta.exe"; Parameters: "--install --quiet"; StatusMsg: "{cm:RegisterMenu}"; Flags: runhidden waituntilterminated

[UninstallRun]
Filename: "{app}\Converta.exe"; Parameters: "--uninstall --quiet"; RunOnceId: "RemoveMenu"; Flags: runhidden waituntilterminated

[Code]
function OfficeAvailable: Boolean;
begin
  Result := RegKeyExists(HKCR, 'Word.Application\CLSID')
    or FileExists(ExpandConstant('{commonpf64}\LibreOffice\program\soffice.exe'))
    or FileExists(ExpandConstant('{commonpf32}\LibreOffice\program\soffice.exe'));
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption + #13#10#13#10 + CustomMessage('FinishedHint');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ErrorCode: Integer;
begin
  if (CurStep = ssDone) and not WizardSilent and not OfficeAvailable then
    if MsgBox(CustomMessage('NoOffice'), mbConfirmation, MB_YESNO) = IDYES then
      ShellExec('open', 'https://www.libreoffice.org/download/', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
end;
