$ErrorActionPreference = "Continue"
$env:USE_TESTER = 'true'

try {
    Write-Host "Starting server..."
    $process = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8002" -PassThru -NoNewWindow -RedirectStandardOutput "server.log" -RedirectStandardError "server.err"
    Write-Host "Process started with PID: $($process.Id)"
    Start-Sleep -Seconds 5
    if (!$process.HasExited) {
        Write-Host "Server is running"
    } else {
        Write-Host "Server exited with code: $($process.ExitCode)"
    }
} catch {
    Write-Host "Error: $_"
}
