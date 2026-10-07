# Disclosery examples

**SEC ownership disclosures → structured JSON API → MCP → research workflows.**

Small, readable recipes for finding a reporting organization, inspecting filing history,
and understanding a disclosed portfolio. These are example clients, not a trading
system or a mirror of Disclosery's database.

[Website](https://disclosery.com) · [API & MCP guide](https://disclosery.com/docs) ·
[API contract](https://disclosery.com/llms-api.txt) · [Data coverage](https://disclosery.com/data) ·
[Methods](https://disclosery.com/methods)

## Run your first query

With curl, make one keyless request:

```sh
curl --fail-with-body --get 'https://disclosery.com/api/v1/search' \
  --data-urlencode 'q=Bridgewater Associates' --data-urlencode 'limit=5'
```

Expect a JSON envelope with `tier`, `quota` and `data`. Search categories include funds,
stocks, groups, insiders and filings; curated investor profiles may also appear where
published. Inspect `data.funds` and choose the reporting entity explicitly. A person's
name does not identify an SEC reporting entity or a personal investment portfolio.

## Three research recipes

### 1. Find an organization and its filings

Python 3.10+ is enough; no package installation is needed:

```sh
python3 api/search_and_filings.py --search 'Bridgewater Associates'
python3 api/search_and_filings.py --cik 1350694
```

Each command makes **one** data call. The second reads up to ten locally imported filings;
it is not a guarantee that the filing history is exhaustive. CIK `1350694` is the
Bridgewater reporter in this example. Confirm the name and source links in your response.

### 2. Inspect a bounded quarterly portfolio

```sh
python3 api/portfolio.py 1350694 --limit 10
```

Omitting `--quarter` selects the latest *locally available* quarter. Read the response's
`quarter`, `period`, `quarters`, `summary`, `filings`, `paging` and warning metadata.
For an available quarter, repeat with `--quarter YYYYqN` using the actual period, such
as `2026q2` only if returned and allowed for your plan. Use `--page 2` explicitly to read
another page; there is no hidden loop consuming your allowance.

The [portfolio notebook](notebooks/reported_portfolio.ipynb) starts offline with invented
positions, then offers an opt-in live call. It demonstrates exact decimal parsing,
known-value concentration and disclosure limits without a dependency on pandas.

### 3. Connect an assistant

See [MCP connection and research recipes](mcp/README.md). The hosted endpoint is
`https://disclosery.com/mcp`; use Streamable HTTP and the site's client-specific guide.
Ask for reporting periods, warning flags and SEC citations, rather than unsupported
performance estimates.

## Authentication and quotas

Optional keyed use:

```sh
# Set your key locally with your shell or secret manager; never paste it into a URL.
export DISCLOSERY_API_KEY='YOUR_API_KEY'
python3 api/portfolio.py 1350694
```

Create and revoke keys at [account keys](https://disclosery.com/account/keys). The example
client sends `Authorization: Bearer …`. A keyless request normally has 20 daily data calls
per shared IP; a free key has 100, and a paid key 2,000. Operator overrides and the live
contract can change effective limits: use the returned quota, not a hardcoded counter.
Allowances reset at midnight UTC and are shared across API/MCP. Invalid keys are errors,
not anonymous fallbacks. Free/keyless portfolio history is limited to eight quarters;
CSV exports require a paid key and are outside these examples.

The client uses a 20-second timeout, refuses HTTP redirects, and makes no automatic retries. On HTTP errors it
reports status, error code and `Retry-After` without echoing authorization headers.
Never interpret a 404, 429 or 503 as an empty portfolio. Respect `paging.pages` and
`page_size`; bounded rows are not an entire holdings list.

`.env.example` documents variables; scripts do **not** automatically load dotenv files.
Only set `DISCLOSERY_ORIGIN` to an HTTPS origin you trust: your key is sent there.

## Data coverage and interpretation

- API requests read stored filings; they do not fetch EDGAR in real time. Consult
  [coverage](https://disclosery.com/data) before interpreting missing records.
- A 13F report is a period-specific disclosure of covered securities. It is not a
  complete balance sheet, all asset classes, short book, or current personal portfolio.
- `value_usd` is in dollars. `amount` uses the reported row's type/class; shares, options
  and principal amounts must stay distinct. Null means unavailable, not zero.
- JSON decimals are numbers. `api/client.py` parses fractional numbers with `Decimal`;
  its console display represents those values as strings to preserve precision.
- Keep source URLs, SEC URLs, filing period, amendments and warning flags together.
  A portfolio aggregate does not have the same provenance as an individual filing fact.
- No return, market timing or recommendation is inferred. Consult the
  [SEC's Form 13F guidance](https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f)
  and [Disclosery methods](https://disclosery.com/methods).

## Repository contents

| Path | Purpose |
|---|---|
| `api/` | Standard-library client, search/filings and bounded portfolio recipes |
| `mcp/` | Hosted connection and source-backed prompt |
| `notebooks/` | Offline-first reported-value analysis; optional one-call live mode |
| `fixtures/` | Invented data, explicitly synthetic and not API schema guarantees |

## Contributing and support

Questions and recipe requests: open a GitHub issue. Please read [CONTRIBUTING.md](CONTRIBUTING.md)
and [SECURITY.md](SECURITY.md) before posting outputs. Never post a key or private account
information. Public documentation remains the authoritative service contract.

## License

New example code, original documentation and synthetic fixtures are [MIT licensed](LICENSE).
That license does not grant rights to service data, external sources or third-party marks.
