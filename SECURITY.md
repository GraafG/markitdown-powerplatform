# Security Policy

Thanks for helping keep this project and its users safe.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, report privately:

- Use **[GitHub Security Advisories](https://github.com/GraafG/markitdown-powerplatform/security/advisories/new)**
  ("Report a vulnerability"), or
- Contact the maintainer directly through their GitHub profile (**[@GraafG](https://github.com/GraafG)**).

Please include:

- A description of the issue and its impact
- Steps to reproduce (proof-of-concept if possible)
- Affected version / commit
- Any suggested remediation

You can expect an initial acknowledgement within a few business days. Please give us
reasonable time to investigate and ship a fix before any public disclosure.

## Scope

This repository contains an Azure Function and example Power Automate flows. Reports that
are in scope include (but are not limited to):

- Authentication / authorization bypass on the function endpoints
- Remote code execution or unsafe file handling in the converter
- Leakage of document content, tokens, or keys
- Dependency vulnerabilities that are exploitable in this context

Out of scope: issues in third-party services (Azure, Power Platform, microsoft/markitdown)
themselves — please report those to the respective vendors.

## Security model & hardening checklist

This project is designed to handle **other people's documents**, so treat the deployment as
a data-processing boundary. The defaults below are what we recommend for any real use.

### Authentication

- **`/api/convert` requires a function key** (`AuthLevel.FUNCTION`). Never expose it
  anonymously. The key is passed as `?code=<key>`.
- **`/api/health` is anonymous** by design — it returns only `ok` and no data.
- For production, layer two additional controls on top of the key:
  - **Layer A — restrict to Power Platform:** add Access Restrictions with the
    **region-specific** connector service tags so only managed-connector traffic reaches the function:
    ```bash
    az functionapp config access-restriction add -g <rg> -n <app> \
      --rule-name AllowPP-WE --action Allow --priority 100 \
      --service-tag AzureConnectors.WestEurope
    az functionapp config access-restriction add -g <rg> -n <app> \
      --rule-name AllowPP-NE --action Allow --priority 101 \
      --service-tag AzureConnectors.NorthEurope
    ```
    Use the pair(s) for your Power Platform geography. The generic `AzureConnectors` tag is not
    sufficient, and service tags are shared by all tenants' connector traffic — always combine this
    with Layer B.
  - **Layer B — Entra ID (Easy Auth):** enable App Service Authentication with the Microsoft
    identity provider, set **Require authentication** + **401** for unauthenticated requests,
    and call the function via **Active Directory OAuth** (HTTP action) or a **custom connector**
    configured with Microsoft Entra ID. The function stays at `AuthLevel.FUNCTION`, so Layer B is
    **additive**: a caller then needs **both** a valid token **and** the `?code=` key.

### Secrets

- **No secrets are stored in this repo.** Function keys, storage account names, and any
  endpoints live in Azure app settings — not in source.
- Rotate the function key if you suspect it leaked: regenerate it in the portal or with
  `az functionapp keys set`.

### Data handling

- Documents are processed **in memory / a temp file** and the temp file is **deleted** after
  conversion. Nothing is persisted by the function.
- Conversion happens entirely within your Azure tenant — no document content is sent to any
  third-party service.
- The function rejects files larger than `MAX_FILE_BYTES` (default `10485760`, 10 MiB decoded bytes).
  Raise this only after testing memory, timeout, and Power Automate request-size behavior for your
  plan.
- The function does **not** bypass document protection. Password-protected documents, Microsoft
  Purview sensitivity-label encryption, IRM/RMS-protected files, and similar encrypted/protected
  content cannot be converted unless the caller supplies an already-decrypted/unprotected copy.

### Transport & network

- All endpoints are HTTPS only.
- Consider restricting inbound access with **access restrictions / private endpoints** so
  only your Power Platform environment (or a known IP range) can reach the function. See the
  hardening guide below for the important caveats.

### Locking down to Power Platform (defense-in-depth)

You can layer two extra controls on top of the function key. **Layer B (identity) is the reliable
primary lock; Layer A (network) is fiddly with Power Automate — read the caveat.**

**Layer B — Entra ID (App Service Authentication / "Easy Auth") — recommended primary control.**
This is what this project enables. Requests must carry a valid Entra ID token; unauthenticated
calls get `401`.

```bash
APP=<your-func-app>; RG=<your-rg>; TENANT=<tenant-guid>
# 1. App registration for the API
APPID=$(az ad app create --display-name "$APP-api" --sign-in-audience AzureADMyOrg --query appId -o tsv)
az ad app update --id $APPID --identifier-uris "api://$APPID"
az ad sp create --id $APPID                       # service principal MUST exist for client-credentials
# 2. Enable Easy Auth v2, require auth, accept tokens from this app
az rest --method put \
  --uri "https://management.azure.com/subscriptions/<sub>/resourceGroups/$RG/providers/Microsoft.Web/sites/$APP/config/authsettingsV2?api-version=2022-03-01" \
  --body '{ "properties": {
      "platform": { "enabled": true },
      "globalValidation": { "requireAuthentication": true, "unauthenticatedClientAction": "Return401" },
      "identityProviders": { "azureActiveDirectory": {
        "enabled": true,
        "registration": { "openIdIssuer": "https://sts.windows.net/<tenant>/", "clientId": "<appId>" },
        "validation": {
          "allowedAudiences": ["api://<appId>", "<appId>"],
          "defaultAuthorizationPolicy": { "allowedApplications": ["<appId>"] }
        } } } } }'
```

In Power Automate, call the function from the **HTTP** action with **Authentication = Active
Directory OAuth** (Tenant, Audience `api://<appId>`, Client ID `<appId>`, the app's client secret) —
or wrap it in a **custom connector** using Microsoft Entra ID. Notes from getting this working:

- The calling app's **service principal must exist** in the tenant (`az ad sp create --id <appId>`),
  otherwise OAuth fails with `AADSTS7000229`.
- For **app-only** (client-credentials) tokens, Easy Auth rejects the call with `403` unless the
  client app id is in `defaultAuthorizationPolicy.allowedApplications`.
- The HTTP action's **Active Directory OAuth** uses the **v1** token endpoint, so the issuer must be
  `https://sts.windows.net/<tenant>/` (not the `/v2.0` issuer).
- After enabling/changing auth, allow a few minutes for Easy Auth's OIDC signing-key cache to settle —
  valid tokens can transiently return `401` right after a change.
- **Keep the function key in the URL.** Because `/api/convert` stays at `AuthLevel.FUNCTION`, Easy Auth
  validates the token *and* the host still checks the key — so the HTTP action must call
  `…/api/convert?code=<key>` **with** the Active Directory OAuth authentication block. Token-only
  (no `?code=`) returns `401`; key-only (no token) returns `401`. Example HTTP-action authentication:
  ```json
  "authentication": {
    "type": "ActiveDirectoryOAuth",
    "tenant": "<tenant-guid>",
    "audience": "api://<appId>",
    "clientId": "<appId>",
    "secret": "<client-secret>"
  }
  ```

**Layer A — restrict the network to Power Platform (defense-in-depth, fiddly).**
The intent is to only accept traffic that originates from Power Platform's connector network.

```bash
# Europe example: you must allow-list the REGION-SPECIFIC connector tags (NOT the generic one)
az functionapp config access-restriction add -g $RG -n $APP \
  --rule-name AllowPP-WE --action Allow --priority 100 --service-tag AzureConnectors.WestEurope
az functionapp config access-restriction add -g $RG -n $APP \
  --rule-name AllowPP-NE --action Allow --priority 101 --service-tag AzureConnectors.NorthEurope
```

Caveats learned the hard way (and well explained in
[this write-up](https://dev.to/andrewelans/whitelist-power-automate-ip-addresses-for-azure-firewall-2jkp)):

- **Use the region-specific tags, and allow-list *all* tags for your region.** For Europe that's
  **both** `AzureConnectors.WestEurope` **and** `AzureConnectors.NorthEurope`. The generic
  `AzureConnectors` tag is *not* sufficient.
  ([Microsoft's outbound-IP reference](https://learn.microsoft.com/en-us/connectors/common/outbound-ip-addresses#power-platform).)
- The **raw HTTP action** can egress from **Azure Logic Apps** IPs that aren't in the connector
  service tags at all — in testing it was blocked even with the connector tags allowed. The reliable
  way to keep traffic inside the connector network (covered by the tags above) is to call through a
  **custom connector**, not the raw HTTP action.
- Because of this, **don't rely on Layer A alone** — treat it as defense-in-depth behind Layer B.

### Dependencies

- Keep `markitdown` and `azure-functions` up to date.
- Enable Dependabot / GitHub security updates on your fork.
