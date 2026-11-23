---
title: Asset Context - <organisation / lab name>
category: asset-context
source: <who maintains this, e.g. SOC team wiki>
---

# Asset context

<!-- Copy this file to asset_context.md, fill it in, and re-run ingestion.
     The risk engine has an "asset context" factor and the AI analyst can
     only reason about criticality if this information is retrievable.
     One paragraph per host is ideal for chunking. -->

## <hostname> (<ip address>)
Role: <jump host / web server / domain controller / database / workstation>.
Criticality: <critical / high / medium / low>. Internet-facing: <yes / no>.
Owner: <team or person>. Operating system: <e.g. Ubuntu 22.04, Windows Server 2022>.
Exposed services: <e.g. SSH 22 (key-only), HTTPS 443>.
Notes: <what would be at risk if this host were compromised; any known
maintenance windows; whether it holds credentials for other systems>.

## <hostname> (<ip address>)
Role: ...
