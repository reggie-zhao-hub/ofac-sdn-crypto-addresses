# OFAC SDN Crypto Address Parser

Parsing cryptocurrency addresses from the U.S. Treasury OFAC Specially Designated Nationals (SDN) sanctions list — and why the flat CSV file silently loses more than half of them.

## What this project does

OFAC publishes the SDN list in several formats. Crypto addresses are buried in the `Remarks` field as `Digital Currency Address - <CURRENCY> <ADDRESS>` patterns. This project:

1. Parses the **flat CSV** (`sdn.csv`) the naive way → finds **506 addresses**
2. Parses the **advanced XML** (`sdn_advanced.xml`) with streaming (`iterparse`) → finds **1,059 addresses** across **99 sanctioned entities** and **20 currency types**
3. Exports a minimal sanctions address dataset (`sdn_addresses.csv`) with 4 columns: `address, currency, entity, fixed_ref`
4. Filters the ETH subset (`sdn_eth_addresses.csv`, 120 addresses) for on-chain analysis in Dune Analytics

## Key finding: the flat CSV truncates your data

The flat `sdn.csv` truncates the `Remarks` field at **1,000 characters**. Entities with many designated addresses (e.g. exchanges and ransomware groups with dozens of addresses per entry) lose everything past the cut-off. Result: **52% of sanctioned crypto addresses are silently missing** if you rely on the CSV.

| Source | Addresses found |
|---|---|
| Flat CSV (`sdn.csv`) | 506 |
| Advanced XML (`sdn_advanced.xml`) | 1,059 |

The XML preserves the full structure via `<Feature>` elements with `FeatureTypeID` lookup (e.g. 344 = XBT, 348 = ETH). A 127 MB file parses in ~3.4 seconds using `xml.etree.ElementTree.iterparse` with `elem.clear()` to keep memory flat.

Bonus findings:

- The same address can appear under multiple currency labels → **address, not (address, currency), is the real primary key**
- 16 address groups are shared across distinct SDN entries → a primitive form of entity clustering

## Files

| File | Description |
|---|---|
| `step1_crypto_stats.py` | Flat CSV parsing with regex — the naive baseline |
| `step2_advanced_xml.py` | Streaming XML parser — the production approach |
| `sdn_crypto_address_tutorial.ipynb` | Step-by-step tutorial notebook (17 cells, end-to-end verified) |
| `sdn_addresses.csv` | Full extracted dataset: 1,059 addresses |
| `sdn_eth_addresses.csv` | ETH subset used for on-chain monitoring |
| `crypto_records.csv` / `currency_stats.csv` | Step 1 intermediate outputs |

Source data (`sdn.csv`, `sdn_advanced.xml`) is not included — download the latest versions from [OFAC](https://ofac.treasury.gov/specially-designated-nationals-list-sdn-list).

## Usage

```bash
python step1_crypto_stats.py     # requires sdn.csv in the same folder
python step2_advanced_xml.py     # requires sdn_advanced.xml
```

## Case study: sanctions ≠ frozen funds

The Lazarus Group ETH address `0x098B716B8Aaf21512996dC57EB0615e2383E2f96`, designated by OFAC in 2022, still held **101.81 ETH** when queried on-chain (Oct 2026). On-chain sanctions designations do not freeze assets — they create compliance obligations for intermediaries. This is why continuous on-chain monitoring of sanctioned addresses matters.

## Related work

The ETH subset is joined with on-chain data in Dune Analytics to monitor sanctioned-address activity: *OFAC Sanctioned Addresses On-Chain Activity* dashboard.
