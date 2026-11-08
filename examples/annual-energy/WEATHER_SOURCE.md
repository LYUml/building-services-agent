# Chicago TMY3 verification weather

Original filename: USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw, station 725300, Chicago O'Hare, Illinois, USA; TMY3. The original header identifies NREL TMY source data. This is not Hong Kong weather or historical 2025 data.

Source: the unmodified WeatherData asset in the official [EnergyPlus 25.2.0 release](https://github.com/NatLabRockies/EnergyPlus/releases/tag/v25.2.0), Windows x64 archive EnergyPlus-25.2.0-cf7368216c-Windows-x86_64, whose archive SHA256 was verified by the repository setup workflow: 4136901f7e1708f6536d84278e26ad88b414c7efc905febf6d49c2539a36f3cd.

Raw EPW: 1,648,753 bytes, SHA256 `c7d4efcf93ba316a1d874352e743df5cf137ba5c0e3459eb2dc4b5442d5b7f5c`.

Repository asset: deterministic gzip compression (mtime=0), 234,159 bytes, SHA256 `d14d55b3122fadc6607ca80e76993f555545b5c01df24a7c7912995dfcc1992c`. Decompression must produce the original bytes, including header/source/uncertainty fields. No meteorological values were changed. The raw source is retained through the compressed file rather than downloaded implicitly at runtime.

The EnergyPlus distribution notice is retained at [third_party/licenses/energyplus.txt](../../third_party/licenses/energyplus.txt); [attribution register](../../THIRD_PARTY.md). The example uses the attributed weather asset supplied with that distribution; meteorological applicability remains a separate review. The engine and SDK binaries remain external dependencies.
