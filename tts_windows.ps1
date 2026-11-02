$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
try {
    Add-Type -AssemblyName System.Speech
    $request = [Console]::In.ReadToEnd() | ConvertFrom-Json
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    if ($request.action -eq 'voices') {
        $items = @($synth.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -like 'tr*' } | ForEach-Object { @{name=$_.VoiceInfo.Name; culture=$_.VoiceInfo.Culture.Name; gender=$_.VoiceInfo.Gender.ToString()} })
        @{ok=$true; voices=$items} | ConvertTo-Json -Depth 5 -Compress
    } elseif ($request.action -eq 'speak') {
        $voice = @($synth.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -like 'tr*' -and $_.VoiceInfo.Name -eq $request.voice }) | Select-Object -First 1
        if (-not $voice) { throw 'Turkce ses bulunamadi' }
        $synth.SelectVoice($voice.VoiceInfo.Name)
        $synth.Rate = -1
        $synth.SetOutputToWaveFile([string]$request.path)
        $synth.Speak([string]$request.text)
        $synth.SetOutputToNull()
        @{ok=$true} | ConvertTo-Json -Compress
    } else { throw 'Bilinmeyen istek' }
    $synth.Dispose()
} catch {
    @{ok=$false; error='Windows Turkce sesi kullanilamadi. Ses ve dil paketlerini kontrol et.'} | ConvertTo-Json -Compress
    exit 1
}
