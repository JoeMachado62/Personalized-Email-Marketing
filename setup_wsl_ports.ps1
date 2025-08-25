# PowerShell script to set up WSL2 port forwarding
# Run this in Windows PowerShell as Administrator

# Get WSL2 IP
$wslIP = (wsl hostname -I).Trim()
Write-Host "WSL2 IP: $wslIP"

# Remove existing port proxies
netsh interface portproxy delete v4tov4 listenport=3001 listenaddress=0.0.0.0
netsh interface portproxy delete v4tov4 listenport=8001 listenaddress=0.0.0.0

# Add port forwarding
netsh interface portproxy add v4tov4 listenport=3001 listenaddress=0.0.0.0 connectport=3001 connectaddress=$wslIP
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=0.0.0.0 connectport=8001 connectaddress=$wslIP

# Show current port proxies
Write-Host "Current port forwarding:"
netsh interface portproxy show all

Write-Host ""
Write-Host "Now try accessing from Windows:"
Write-Host "  Frontend: http://localhost:3001/unified.html"
Write-Host "  API:      http://localhost:8001/docs"