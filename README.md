# OFAC SDN Crypto Address Parser & Monitoring Agent

Parsing cryptocurrency addresses from the U.S. Treasury OFAC SDN sanctions list — and running them through a daily monitoring agent that flags additions, removals and data-quality anomalies for human review.

## What this project does

OFAC publishes the SDN list in several formats. Crypto addresses are buried in the `Remarks` field as `Digital Currency Address - <CURRENCY> <ADDRESS>` patterns. This project:

1. Parses the **flat CSV** (`sdn.csv`) the naive way → finds **506 addresses**
2. Parses the **advanced XML** (`sdn_advanced.xml`) with streaming (`iterparse`) → finds **1,059 addresses** across **99 sanctioned entities** and **20 currency types**
3. Exports a minimal sanctions address dataset (`sdn_addresses.csv`) with 4 columns: `address, currency, entity, fixed_ref`
4. Filters the ETH subset (`sdn_eth_addresses.csv`, 120 addresses) for on-chain analysis in Dune Analytics
5. Wraps the parser in a **monitoring agent** that re-checks the source daily, diffs against the last snapshot, and writes a human-reviewable alert report

## Key finding: the flat CSV truncates your data

The flat `sdn.csv` truncates the `Remarks` field at **1,000 characters**. Entities with many designated addresses (exchanges and ransomware groups with dozens of addresses per entry) lose everything past the cut-off. Result: **52% of sanctioned crypto addresses are silently missing** if you rely on the CSV.

| Source | Addresses found |
|---|---|
| Flat CSV (`sdn.csv`) | 506 |
| Advanced XML (`sdn_advanced.xml`) | 1,059 |

The XML preserves the full structure via `<Feature>` elements with `FeatureTypeID` lookup (e.g. 344 = XBT, 348 = ETH). A 127 MB file parses in ~3.4 seconds using `xml.etree.ElementTree.iterparse` with `elem.clear()` to keep memory flat.

Bonus findings:

- The same address can appear under multiple currency labels → **address, not (address, currency), is the real primary key**
- 16 address groups are shared across distinct SDN entries → a primitive form of entity clustering

## Monitoring agent

The agent turns a one-off script into a daily pipeline:

```
OFAC SDN list ── fetch ──▶ download + hash, compare with last run
                              │ changed?
                              ▼
                          parse       streaming iterparse (reused from step2)
                              ▼
                          validate    address format + sanity count
                              ▼
                          store       SQLite snapshot with timestamp
                              ▼
                          diff        added / removed vs previous run
                              ▼
                          alert       P1 / P2 / INFO report
                              ▼
                       alerts/YYYY-MM-DD.md   ← a human reads this
```

**Design principle: alert ≠ auto-remediation.** The agent only *surfaces* things that need a human decision — it never mutates data on its own. The clearest example: an address that disappears from the list (a possible delisting) raises a `P1` alert, but the program does **not** silently delete it. Delisting requires human approval.

Alert levels:

| Level | Meaning | Example |
|---|---|---|
| `P1` | Needs human decision | bulk add (>100), possible delisting |
| `P2` | Data-quality flag | address fails format validation, known anomaly hit |
| `INFO` | Routine | ordinary additions, no change |

This is where the project's real value lives: the pipeline is automatable, but *"what does this anomaly actually mean, and what do we do about it"* is a judgment call that stays with a person.

## Known anomalies found in production data

The validation layer caught three real data-quality issues on the first run — three different root causes:

1. **LTC bech32 address rejected (regex bug, fixed).** A real OFAC LTC address in bech32 format (`ltc1...`, 43 chars) failed validation because my original regex only matched legacy P2PKH/P2SH prefixes. Fixed by adding the `ltc1` bech32 pattern.
2. **XMR address with length 64 (standard is 95).** Likely a payment ID or an OFAC data-entry issue — flagged for human review, registered in `KNOWN_ANOMALIES`.
3. **An address labeled XBT that starts with `T` and is 34 chars long.** Structurally it is a TRON (TRX) address — a suspected currency-label error in the OFAC source. Matching it with BTC rules would permanently miss it. Registered in `KNOWN_ANOMALIES`.

Known anomalies are deduplicated so they don't re-alert every run, but remain tracked.

## Files

| File | Description |
|---|---|
| `step1_crypto_stats.py` | Flat CSV parsing with regex — the naive baseline |
| `step2_advanced_xml.py` | Streaming XML parser — the production approach |
| `agent/` | The monitoring agent (`config`, `fetch`, `parse`, `store`, `alert`, `run`) |
| `check_*.py` | Five standalone validation scripts, one per agent step |
| `sdn_crypto_address_tutorial.ipynb` | Step-by-step tutorial notebook (17 cells, end-to-end verified) |
| `sdn_addresses.csv` | Full extracted dataset: 1,059 addresses |
| `sdn_eth_addresses.csv` | ETH subset used for on-chain monitoring |
| `alerts/` | Generated alert reports (work product) |
| `crypto_records.csv` / `currency_stats.csv` | Step 1 intermediate outputs |

Source data (`sdn.csv`, `sdn_advanced.xml`) and runtime artifacts (`data/`, `snapshots/`) are not included — download the latest from [OFAC](https://ofac.treasury.gov/specially-designated-nationals-list-sdn-list).

## Usage

```bash
pip install requests pandas

# One-off parse (original scripts)
python step1_crypto_stats.py     # requires sdn.csv in the same folder
python step2_advanced_xml.py     # requires sdn_advanced.xml

# Run the monitoring agent
python -m agent.run

# Step-by-step validation checks (see tutorial)
python check_config.py
python check_parse.py
python check_store.py
python check_alert.py
```

## Case study: sanctions ≠ frozen funds

The Lazarus Group ETH address `0x098B716B8Aaf21512996dC57EB0615e2383E2f96`, designated by OFAC in 2022, still held **101.81 ETH** when queried on-chain (Oct 2026). On-chain sanctions designations do not freeze assets — they create compliance obligations for intermediaries. This is why continuous on-chain monitoring of sanctioned addresses matters.

## Related work

The ETH subset is joined with on-chain data in Dune Analytics to monitor sanctioned-address activity: *OFAC Sanctioned Addresses On-Chain Activity* dashboard.
