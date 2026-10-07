# SEC ownership research through MCP

Disclosery exposes a hosted **Streamable HTTP** MCP endpoint:

```text
https://disclosery.com/mcp
```

Follow the current client-specific guide at [Disclosery connections](https://disclosery.com/docs).
There is no legacy `/sse` endpoint and no local server to install from this repository.

For Claude Code, using its HTTP transport:

```sh
claude mcp add --transport http disclosery https://disclosery.com/mcp
claude mcp get disclosery
```

Use `/mcp` inside Claude Code to inspect the connection. Configuration alone does not
prove successful discovery or a data call. Other clients differ in configuration and
remote-server support; use their current documentation. Never commit a key-bearing config.

## A source-backed research prompt

> Search for Bridgewater Associates. Identify the reporting entity and its CIK. Read
> its available filing history and latest reported portfolio. State the reporting
> period, coverage warnings and whether the output is paginated. Cite Disclosery and
> the SEC filing URLs. Do not call it Ray Dalio's personal portfolio or infer returns.

The relevant data tools are `search`, `fund_filings` and `fund_portfolio`. For the last,
request `view: "summary"`, `limit: 10` and `sort: "value"`. Keep the returned `quota`
and citation metadata. A three-tool sequence normally consumes three data-call units.
Initialization and discovery do not consume daily data-call units.

No-key access shares a daily IP allowance. An invalid key does not fall back to keyless
access. Keyed access uses a Bearer header configured through your client's supported
secure mechanism. See the [live contract](https://disclosery.com/llms-api.txt) for limits.

If a host offers optional feedback submission, explicitly approve a brief summary first.
Do not include account details, credentials, portfolios or conversation transcripts.
