# V9.2 OFI Historical Provenance & Coverage Audit

## Purpose

Determine whether existing historical OFI / `volume_delta` sources are sufficiently complete, sparse, null-safe, and provenance-clear for future research use.

This audit does not approve OFI for production, paper trading, live trading, or alpha use.

## Inputs

- Bar dir: `/home/tokio/tm-trading-v92-phase1f/bars_750btc`
- OFI dir: `/home/tokio/tm-trading-v92-phase1f/ofi`

## Read-Only Guardrails

- Only reads parquet/csv/json/md files.
- Never regenerates OFI or bars.
- Writes only the markdown report.

## Executive Finding

Historical OFI files are unavailable in the requested location, so OFI joins remain blocked for today. Existing 750 BTC bars do contain `volume_delta`, but OFI provenance cannot yet be confirmed.

- OFI historical inventory state: `historical_ofi_file_inventory = unavailable`
- Volume-delta state: `volume_delta_available`
- OFI state: `ofi_unavailable`
- Join readiness: `blocked_no_historical_ofi_files`

## Bar File Inventory

| file_path | row_count | min_open_time | max_close_time | has_volume_delta | has_ofi_column | suspicious_flag_count | suspicious_reasons |
| --- | --- | --- | --- | --- | --- | --- | --- |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-22.parquet | 79 | 1590105600125 | 1590191999877 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-23.parquet | 59 | 1590192000158 | 1590278399810 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-24.parquet | 94 | 1590278400059 | 1590364799975 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-25.parquet | 84 | 1590364800024 | 1590451199346 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-26.parquet | 78 | 1590451200114 | 1590537599633 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-27.parquet | 92 | 1590537600013 | 1590623999528 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-28.parquet | 99 | 1590624000134 | 1590710399943 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-29.parquet | 77 | 1590710400158 | 1590796799973 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-30.parquet | 75 | 1590796800080 | 1590883199560 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-31.parquet | 65 | 1590883200013 | 1590969599903 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-06.parquet | 2007 | 1590969600099 | 1593561599741 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-07.parquet | 2011 | 1593561601160 | 1596239999996 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-08.parquet | 2522 | 1596240000056 | 1598918399808 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-09.parquet | 2308 | 1598918400390 | 1601510399917 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-10.parquet | 2124 | 1601510400463 | 1604188799701 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-11.parquet | 3610 | 1604188800010 | 1606780799747 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-12.parquet | 3328 | 1606780800040 | 1609459199993 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-01.parquet | 4588 | 1609459200058 | 1612137599983 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-02.parquet | 3358 | 1612137600018 | 1614556799971 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-03.parquet | 2799 | 1614556800046 | 1617235199832 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-04.parquet | 2658 | 1617235200084 | 1619827199953 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-05.parquet | 4715 | 1619827200133 | 1622505599978 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-06.parquet | 3870 | 1622505600055 | 1625097599881 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-07.parquet | 2372 | 1625097600041 | 1627775999971 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-08.parquet | 2181 | 1627776000011 | 1630454399980 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-09.parquet | 2038 | 1630454400009 | 1633046399999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-10.parquet | 2088 | 1633046400199 | 1635724799994 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-11.parquet | 1723 | 1635724800149 | 1638316799999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-12.parquet | 1645 | 1638316800000 | 1640995199999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-01.parquet | 1706 | 1640995200000 | 1643673599999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-02.parquet | 1672 | 1643673600000 | 1646092799999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-03.parquet | 2002 | 1646092800000 | 1648771199998 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-04.parquet | 1691 | 1648771200005 | 1651363199998 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-05.parquet | 3184 | 1651363200000 | 1654041599999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-06.parquet | 3755 | 1654041600002 | 1656633599998 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-07.parquet | 6645 | 1656633600003 | 1659311999999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-08.parquet | 7590 | 1659312000000 | 1661990399999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-09.parquet | 13119 | 1661990400000 | 1664582399998 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-10.parquet | 9999 | 1664582400000 | 1667260799994 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-11.parquet | 12171 | 1667260800000 | 1669852799999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-12.parquet | 7739 | 1669852800000 | 1672531199999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-01.parquet | 10637 | 1672531200001 | 1675209599999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-02.parquet | 11524 | 1675209600000 | 1677628799999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-03.parquet | 12689 | 1677628800000 | 1680307199999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-04.parquet | 2169 | 1680307200003 | 1682899199998 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-05.parquet | 1737 | 1682899200002 | 1685577599997 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-06.parquet | 1850 | 1685577600000 | 1688169599998 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-07.parquet | 1235 | 1688169600000 | 1690847999999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-08.parquet | 1368 | 1690848000000 | 1693526399999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-09.parquet | 1080 | 1693526400000 | 1696118399999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-10.parquet | 1522 | 1696118400000 | 1698796799998 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-11.parquet | 1408 | 1698796800001 | 1701388799999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-12.parquet | 1594 | 1701388800000 | 1704067199997 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-01.parquet | 1872 | 1704067200000 | 1706745599998 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-02.parquet | 1609 | 1706745600000 | 1709251199999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-03.parquet | 2276 | 1709251200000 | 1711929599999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-04.parquet | 1603 | 1711929600000 | 1714521599999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-05.parquet | 1261 | 1714521600000 | 1717199999997 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-06.parquet | 930 | 1717200000001 | 1719791999999 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-07.parquet | 1211 | 1719792000462 | 1722470399814 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-08.parquet | 1348 | 1722470400227 | 1725148799643 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-09.parquet | 979 | 1725148800266 | 1727740799892 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-10.parquet | 1009 | 1727740800020 | 1730419199787 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-11.parquet | 1792 | 1730419200187 | 1733011199987 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-12.parquet | 1360 | 1733011200101 | 1735689599951 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-01.parquet | 1153 | 1735689600010866 | 1738367999923100 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-02.parquet | 1082 | 1738368000182381 | 1740787199819554 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-03.parquet | 1128 | 1740787200184756 | 1743465599970596 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-04.parquet | 1059 | 1743465600003164 | 1746057599161596 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-05.parquet | 857 | 1746057600079126 | 1748735999571938 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | 571 | 1748736000286958 | 1751327999814353 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-07.parquet | 646 | 1751328000015562 | 1754006399974249 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-08.parquet | 629 | 1754006400328945 | 1756684799566595 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-09.parquet | 500 | 1756684800178247 | 1759276799498578 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-10.parquet | 961 | 1759276800181160 | 1761955199599399 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-11.parquet | 1047 | 1761955200098001 | 1764547199477471 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-12.parquet | 655 | 1764547200180386 | 1767225599440400 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-01.parquet | 656 | 1767225600039409 | 1769903999765674 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-02.parquet | 1118 | 1769904000006539 | 1772323199996711 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-03.parquet | 941 | 1772323200005709 | 1775001599618442 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-04.parquet | 632 | 1775001600062762 | 1777593598515440 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-01.parquet | 24 | 1777593600365107 | 1777679997897258 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-02.parquet | 9 | 1777680000096399 | 1777766398440237 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-03.parquet | 10 | 1777766400117041 | 1777852799991798 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-04.parquet | 35 | 1777852800060166 | 1777939197736186 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-05.parquet | 23 | 1777939200007297 | 1778025599996222 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-06.parquet | 26 | 1778025600076850 | 1778111998251555 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-07.parquet | 22 | 1778112000117277 | 1778198399224893 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-08.parquet | 22 | 1778198400018655 | 1778284798789124 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-09.parquet | 11 | 1778284800040998 | 1778371199658719 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-10.parquet | 17 | 1778371200125821 | 1778457599594603 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-11.parquet | 18 | 1778457600195725 | 1778543999370012 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-12.parquet | 17 | 1778544000122511 | 1778630399977309 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-13.parquet | 20 | 1778630400070101 | 1778716799257712 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-14.parquet | 27 | 1778716800112799 | 1778803199853148 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-15.parquet | 24 | 1778803200001463 | 1778889599595700 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-16.parquet | 17 | 1778889600059524 | 1778975998475438 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-17.parquet | 12 | 1778976000181551 | 1779062399758039 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-18.parquet | 25 | 1779062400115662 | 1779148799282474 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-19.parquet | 15 | 1779148800032471 | 1779235198527616 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-20.parquet | 16 | 1779235200183703 | 1779321599640499 | True | False | 0 | none |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-21.parquet | 16 | 1779321600096413 | 1779407999849615 | True | False | 0 | none |

## Volume Delta Coverage

| file_path | volume_delta_null_count | volume_delta_zero_count | volume_delta_positive_count | volume_delta_negative_count | volume_delta_abs_sum | volume_sum | abs_volume_delta_over_volume_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-22.parquet | 0 | 0 | 34 | 45 | 7051.4908540000015 | 58943.13102399992 | 0.1196321052427439 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-23.parquet | 0 | 0 | 25 | 34 | 5810.087219999998 | 43526.296965999885 | 0.13348452831947746 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-24.parquet | 0 | 0 | 35 | 59 | 11538.343209999999 | 70379.86644999986 | 0.16394380654582819 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-25.parquet | 0 | 0 | 39 | 45 | 6794.6598150000045 | 62833.91094899984 | 0.10813682790674928 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-26.parquet | 0 | 0 | 35 | 43 | 7441.757082000002 | 58299.77013799987 | 0.1276464223509769 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-27.parquet | 0 | 0 | 36 | 56 | 10666.972747999991 | 68910.35551399982 | 0.15479491679349833 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-28.parquet | 0 | 0 | 49 | 50 | 11337.263886000006 | 74110.78766199981 | 0.15297724182485203 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-29.parquet | 0 | 0 | 28 | 49 | 7698.601287000004 | 57374.36296099984 | 0.13418190442015226 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-30.parquet | 0 | 0 | 43 | 32 | 8476.114476000004 | 55665.272539999874 | 0.1522693429715852 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-05-31.parquet | 0 | 0 | 16 | 49 | 5235.822732999997 | 48333.78640299984 | 0.10832635145412559 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-06.parquet | 0 | 0 | 780 | 1227 | 223189.61256799998 | 1504745.5179219972 | 0.14832382612856512 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-07.parquet | 0 | 0 | 756 | 1255 | 186006.14568400005 | 1507827.2149399954 | 0.12336038495723943 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-08.parquet | 0 | 0 | 840 | 1682 | 200494.019104 | 1891193.0071279965 | 0.10601457299616089 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-09.parquet | 0 | 0 | 791 | 1517 | 172926.382475 | 1730389.1601789964 | 0.09993496633850388 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-10.parquet | 0 | 0 | 877 | 1247 | 200497.257034 | 1592634.4199459974 | 0.12589032016575305 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-11.parquet | 0 | 0 | 1429 | 2181 | 357843.872469 | 2707064.911165 | 0.13218887770038731 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2020-12.parquet | 0 | 0 | 1419 | 1909 | 292618.348077 | 2495281.8562169913 | 0.11726865538173245 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-01.parquet | 0 | 0 | 2049 | 2539 | 409653.448477 | 3440864.7500189943 | 0.1190553765517051 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-02.parquet | 0 | 0 | 1570 | 1788 | 267819.719675 | 2518242.148516996 | 0.10635185334846382 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-03.parquet | 0 | 0 | 1248 | 1551 | 202813.023324 | 2098808.027431999 | 0.09663247932787465 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-04.parquet | 0 | 0 | 1090 | 1568 | 187535.39891699995 | 1993468.9380069973 | 0.09407490397341806 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-05.parquet | 0 | 0 | 1836 | 2879 | 357688.318741 | 3536245.2565729944 | 0.10114918304270526 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-06.parquet | 0 | 0 | 1716 | 2154 | 333102.25992499996 | 2901775.3059229963 | 0.11479257516772025 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-07.parquet | 0 | 0 | 1074 | 1298 | 199445.7510789999 | 1778463.2648369982 | 0.11214499338971712 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-08.parquet | 0 | 0 | 1068 | 1113 | 166764.34519300004 | 1635402.8742449991 | 0.10197141500683038 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-09.parquet | 0 | 0 | 856 | 1182 | 153048.38081800003 | 1527799.510768001 | 0.10017569696763746 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-10.parquet | 0 | 0 | 1019 | 1069 | 148319.15145899996 | 1565556.2926230053 | 0.09473894497303524 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-11.parquet | 0 | 0 | 725 | 998 | 122331.10445000001 | 1291900.1052480026 | 0.0946908386748033 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2021-12.parquet | 0 | 0 | 657 | 988 | 113709.2263380001 | 1233745.5243180017 | 0.0921658673500413 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-01.parquet | 0 | 0 | 767 | 939 | 123228.88185500001 | 1279407.4657210023 | 0.09631715083478516 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-02.parquet | 0 | 0 | 805 | 867 | 139055.32124000014 | 1253514.21906 | 0.11093238443220578 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-03.parquet | 0 | 0 | 919 | 1083 | 152777.1648900001 | 1501398.7959100003 | 0.10175655216068134 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-04.parquet | 0 | 0 | 757 | 934 | 114343.47446000003 | 1267655.6817800005 | 0.09020073518657896 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-05.parquet | 0 | 0 | 1411 | 1773 | 306096.364112 | 2387839.6808039946 | 0.12818966305515794 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-06.parquet | 0 | 0 | 1694 | 2061 | 328630.8096340002 | 2816058.473225996 | 0.1166988586204782 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-07.parquet | 0 | 0 | 3344 | 3301 | 377306.54358000006 | 4983278.588099999 | 0.07571451944930449 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-08.parquet | 0 | 0 | 3762 | 3828 | 391472.06929 | 5692462.415710006 | 0.06877025102697543 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-09.parquet | 0 | 0 | 6514 | 6605 | 758277.2309300002 | 9838930.536570001 | 0.07706907047585956 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-10.parquet | 0 | 0 | 4930 | 5069 | 521732.9754600001 | 7499121.815419993 | 0.069572543065935 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-11.parquet | 0 | 0 | 5797 | 6374 | 604441.5795430002 | 9127693.50906501 | 0.06622062615738682 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2022-12.parquet | 0 | 0 | 3552 | 4187 | 397522.7746700001 | 5803833.881869988 | 0.0684931344971436 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-01.parquet | 0 | 0 | 4998 | 5639 | 551919.3188100001 | 7977028.878010015 | 0.06918858227170971 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-02.parquet | 0 | 0 | 5555 | 5969 | 594015.8860300002 | 8642691.27165002 | 0.06873042983480232 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-03.parquet | 0 | 0 | 6407 | 6282 | 687713.57342 | 9516189.358459985 | 0.07226774788887697 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-04.parquet | 0 | 0 | 1068 | 1101 | 184407.23435999997 | 1626745.5585000066 | 0.11335960525384108 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-05.parquet | 0 | 0 | 684 | 1053 | 138362.54775000009 | 1302000.492210007 | 0.10626919772906107 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-06.parquet | 0 | 0 | 750 | 1100 | 160493.6113700001 | 1387207.4827500014 | 0.11569546255030098 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-07.parquet | 0 | 0 | 412 | 823 | 120282.22611000005 | 925773.8173100038 | 0.12992614811628708 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-08.parquet | 0 | 0 | 555 | 813 | 117669.36980999997 | 1025866.5502300041 | 0.11470241405533492 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-09.parquet | 0 | 0 | 443 | 637 | 96776.55645000002 | 809329.0489300048 | 0.11957627936121416 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-10.parquet | 0 | 0 | 635 | 887 | 138690.4887600001 | 1141403.679900004 | 0.12150871002286454 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-11.parquet | 0 | 0 | 581 | 827 | 113621.79125999998 | 1055690.5963800044 | 0.10762792777506269 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2023-12.parquet | 0 | 0 | 739 | 855 | 132398.15996000002 | 1195409.9760000021 | 0.11075544174645552 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-01.parquet | 0 | 0 | 981 | 891 | 157794.87493999995 | 1403408.8497800059 | 0.11243685328387049 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-02.parquet | 0 | 0 | 905 | 704 | 135022.4446900001 | 1206112.6954500074 | 0.11194844826637237 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-03.parquet | 0 | 0 | 1156 | 1120 | 185675.70461800002 | 1706807.3813420061 | 0.10878538881874847 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-04.parquet | 0 | 0 | 710 | 893 | 141196.01244000005 | 1201500.9585200013 | 0.11751635438886716 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-05.parquet | 0 | 0 | 594 | 667 | 109459.52212000004 | 945031.0407200065 | 0.11582637755115885 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-06.parquet | 0 | 0 | 416 | 514 | 81545.99923999993 | 696818.1881800084 | 0.11702622093287586 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-07.parquet | 0 | 0 | 544 | 667 | 109091.77509999997 | 908004.3342600076 | 0.12014455326240929 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-08.parquet | 0 | 0 | 557 | 791 | 116129.17002000014 | 1010291.4739600106 | 0.11494620415315587 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-09.parquet | 0 | 0 | 431 | 548 | 88665.09667000016 | 734117.0757500017 | 0.12077786990503736 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-10.parquet | 0 | 0 | 467 | 542 | 111462.65669000002 | 756010.8634300092 | 0.1474352579859709 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-11.parquet | 0 | 0 | 848 | 944 | 178926.85042800003 | 1343559.2421959974 | 0.13317377068952374 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2024-12.parquet | 0 | 0 | 591 | 769 | 129651.81930100001 | 1019450.0657730037 | 0.1271781950425309 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-01.parquet | 0 | 0 | 486 | 667 | 101137.53040200003 | 864534.7383220062 | 0.11698492370393353 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-02.parquet | 0 | 0 | 389 | 693 | 115832.59000000003 | 810850.1813000022 | 0.14285325781674055 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-03.parquet | 0 | 0 | 467 | 661 | 122275.9972099999 | 845293.5310099982 | 0.14465507273419984 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-04.parquet | 0 | 0 | 500 | 559 | 125212.12216999989 | 793597.0017899952 | 0.15777796776900377 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-05.parquet | 0 | 0 | 400 | 457 | 98321.94398500008 | 642216.5461250057 | 0.15309780568291678 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-06.parquet | 0 | 0 | 214 | 357 | 64842.160920000046 | 427546.463360006 | 0.15166108593301858 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-07.parquet | 0 | 0 | 287 | 359 | 71700.34315700005 | 484315.65101700206 | 0.14804465436216718 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-08.parquet | 0 | 0 | 252 | 377 | 64639.347056000086 | 471366.94293600315 | 0.13713169331175623 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-09.parquet | 0 | 0 | 196 | 304 | 50296.566590000104 | 374551.9940700042 | 0.13428460503830508 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-10.parquet | 0 | 0 | 396 | 565 | 100333.53446600033 | 720300.28500601 | 0.13929403688235828 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-11.parquet | 0 | 0 | 439 | 608 | 114955.74508000012 | 784853.6617800047 | 0.1464677438330183 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2025-12.parquet | 0 | 0 | 255 | 400 | 70774.06598000007 | 491084.34878000256 | 0.14411794258119526 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-01.parquet | 0 | 0 | 295 | 361 | 76471.23838000001 | 491752.73296000203 | 0.1555075005271399 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-02.parquet | 0 | 0 | 490 | 628 | 129662.8360499999 | 837919.8643899914 | 0.1547437190123126 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-03.parquet | 0 | 0 | 447 | 494 | 102549.15749999997 | 705639.8840399892 | 0.14532789290888273 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-04.parquet | 0 | 0 | 335 | 297 | 66471.17349999995 | 473256.4698199936 | 0.14045486483319017 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-01.parquet | 0 | 0 | 11 | 13 | 2648.329599999995 | 17315.465019999836 | 0.15294591262441418 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-02.parquet | 0 | 0 | 6 | 3 | 700.6061999999966 | 6150.876419999962 | 0.11390347523841178 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-03.parquet | 0 | 0 | 3 | 7 | 1704.908379999999 | 7425.792899999932 | 0.22959277251053076 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-04.parquet | 0 | 0 | 20 | 15 | 3846.2722299999923 | 26042.961349999554 | 0.14768951112389753 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-05.parquet | 0 | 0 | 12 | 11 | 2144.6627899999994 | 16947.179949999787 | 0.12654983285287097 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-06.parquet | 0 | 0 | 15 | 11 | 2910.3700600000016 | 18798.773959999733 | 0.1548170144602368 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-07.parquet | 0 | 0 | 6 | 16 | 1799.3362999999972 | 16154.803379999757 | 0.11138088515689655 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-08.parquet | 0 | 0 | 11 | 11 | 2320.1422099999995 | 16001.31008999978 | 0.14499701567873505 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-09.parquet | 0 | 0 | 8 | 3 | 978.399929999998 | 7548.421769999926 | 0.12961648935523215 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-10.parquet | 0 | 0 | 12 | 5 | 1368.8179399999992 | 12034.318819999839 | 0.11374286824819367 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-11.parquet | 0 | 0 | 6 | 12 | 1188.3434600000016 | 12951.760559999813 | 0.09175150007560198 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-12.parquet | 0 | 0 | 6 | 11 | 1681.766359999996 | 12386.256759999855 | 0.13577680429095318 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-13.parquet | 0 | 0 | 9 | 11 | 1951.2931499999997 | 14810.056429999862 | 0.13175460601536804 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-14.parquet | 0 | 0 | 16 | 11 | 3256.987829999993 | 19727.86806999977 | 0.1650957832059362 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-15.parquet | 0 | 0 | 10 | 14 | 2204.283269999998 | 17351.27078999983 | 0.1270387222168423 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-16.parquet | 0 | 0 | 6 | 11 | 2121.5043999999957 | 12132.861919999921 | 0.1748560573744673 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-17.parquet | 0 | 0 | 6 | 6 | 1485.8478999999975 | 8442.702199999945 | 0.1759919827564221 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-18.parquet | 0 | 0 | 10 | 15 | 2253.3500600000025 | 18745.51677999981 | 0.12020741206794436 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-19.parquet | 0 | 0 | 9 | 6 | 1080.2646399999994 | 11024.85977999988 | 0.09798443350360789 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-20.parquet | 0 | 0 | 8 | 8 | 1238.6569300000015 | 11296.263069999915 | 0.10965191960601274 |
| /home/tokio/tm-trading-v92-phase1f/bars_750btc/BTCUSDT_tier2_750btc_2026-05-21.parquet | 0 | 0 | 9 | 7 | 1418.0208100000025 | 11318.25840999993 | 0.12528613136692038 |

## Historical OFI File Inventory

historical_ofi_file_inventory = unavailable

## OFI Coverage

- bar_min_time: `None`
- bar_max_time: `None`
- ofi_min_time: `None`
- ofi_max_time: `None`
- overlap_start: `None`
- overlap_end: `None`
- ofi_covers_bar_range: `False`
- coverage_gap_summary: `unavailable`

## Resync / Sequence Gap Coverage

Historical OFI files are unavailable, so resync / sequence-gap coverage cannot be validated.

## Join Readiness

- join_readiness: `blocked_no_historical_ofi_files`
- ofi_state: `ofi_unavailable`
- volume_delta_state: `volume_delta_available`

## Data Policy Helper Check

- join_ofi_to_bars_preserve_coverage importable: `True`
- join_ofi_to_bars_preserve_coverage callable: `True`
- preserves_coverage: `True`

## Suspicious Files

No heuristic suspicious files were found.

## What Is Safe

- Existing 750 BTC bars expose `volume_delta` and can be audited for signed-flow coverage.
- `join_ofi_to_bars_preserve_coverage` is present and importable when dependencies are available.
- This report is read-only and can support future research triage.

## What Is Not Safe

- Treating OFI as production, paper, live, or alpha-approved.
- Assuming historical OFI provenance is complete when the OFI inventory is unavailable or incomplete.
- Assuming resync/sequence-gap handling exists downstream when it has not been verified.

## Required Next Step

Run a read-only source-inventory check on any historical L2 / OFI archive manifests, then validate downstream consumer wiring before considering any broader use.

## Audit Summary

- bar_file_count: `102`
- ofi_file_count: `0`
- historical_ofi_file_inventory: `unavailable`
- join_readiness: `blocked_no_historical_ofi_files`
- This audit does not approve OFI for production, paper trading, live trading, or alpha use.