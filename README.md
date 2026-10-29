# JPRL 2025 pre Trimble – porastová mapa Slovenska (SHP + DXF)

Jednotky priestorového rozdelenia lesa (JPRL) za celé Slovensko, ročník 2025. Vrstvy sú spojené s opisom lesných porastov
a pripravené pre Trimble a GIS. Súbory sú rozdelené podľa lesných celkov (506 súborov), takže do prístroja nahráš len svoje územie.

**Zdroj:** Národné lesnícke centrum, data.slovensko.sk
([geometria JPRL 2025](https://data.slovensko.sk/datasety/2896fcca-3332-4d1a-a2bc-fd11c21ac538),
[opis lesných porastov](https://data.slovensko.sk/datasety/9d34d917-a383-4aa1-845f-cbe4ae92529c)).
Pri použití uvádzaj „Národné lesnícke centrum, data.slovensko.sk“.

## Stiahnutie

Všetko je v sekcii **[Releases](../../releases/latest)**:

| Súbor | Formát | Súradnicový systém | Na čo |
|---|---|---|---|
| `JPRL2025_SHP_JTSK03.zip` | Shapefile + atribúty | **S-JTSK [JTSK03]**, EPSG:8353 | Trimble s SKPOS, aktuálny štátny systém |
| `JPRL2025_SHP_SJTSK.zip` | Shapefile + atribúty | S-JTSK (pôvodný), EPSG:5514 | projekty a mapy v starom S-JTSK |
| `JPRL2025_SHP_ETRS89.zip` | Shapefile + atribúty | ETRS89 zem. šírka/dĺžka, EPSG:4258 | mapové aplikácie s GPS (TerraFlex, Catalyst, mobil) |
| `JPRL2025_DXF_JTSK03.zip` | DXF R12 | S-JTSK [JTSK03] | CAD, Trimble Access/Business Center |
| `JPRL2025_DXF_SJTSK.zip` | DXF R12 | S-JTSK (pôvodný) | CAD v starom S-JTSK |
| `ZOZNAM_LESNYCH_CELKOV.csv` | tabuľka | – | ktorý súbor je ktorý lesný celok, rozsah územia |

Súbor sa volá `JPRL2025_<kód LC>_<názov LC>`, napr. `JPRL2025_SL251_KRASNO_ZAPAD.shp`.

## Ktorú verziu vybrať – toto je najčastejšia príčina, prečo „to v teréne nesedí“

S-JTSK a JTSK03 vyzerajú rovnako (rovnaké Křovákovo zobrazenie, záporné súradnice), ale **líšia sa o 0,5 m v priemere
a až o 1,6 m**. Overené na všetkých 585 216 polygónoch. Ak má prístroj nastavený iný systém ako dáta, hranice sú posunuté
presne o toľko.

1. **Meriaš so SKPOS korekciami (RTK) a projekt v Trimble je v JTSK03** → použi **JTSK03**. JTSK03 je dnes záväzný
   štátny systém a SKPOS doň prepočítava oficiálnym kľúčom GKÚ.
2. **Porovnávaš so starými mapami alebo projektom v pôvodnom S-JTSK** (napr. staršie katastrálne podklady) → použi **S-JTSK**.
3. **Aplikácia ukazuje polohu na mape v zemepisných súradniciach a JTSK nastavené nemá** → použi **ETRS89**.

Nikdy nemiešaj vrstvy z rôznych variantov v jednom projekte.

### Ďalšie veci, ktoré v teréne spôsobujú posun

- **Trimble s „S-JTSK“ cez 7-prvkovú transformáciu z WGS84** (staršie predvolené nastavenie) má chybu 1–2 m a na každom mieste
  inú. Správne je JTSK03 cez kľúč GKÚ, a pre pôvodný S-JTSK navyše interpolačná tabuľka GKÚ (JTSK03 → JTSK).
- **GNSS bez korekcií (bez SKPOS)** má presnosť 2–5 m, pod korunami stromov aj horšie. Za takýto posun dáta nemôžu.
- **WGS84 a ETRS89 sa dnes líšia asi o 0,9 m** (posun Európy). Ak aplikácia berie ETRS89 dáta ako „WGS84“ a prijímač beží
  bez SKPOS, rozdiel je do 1 m.
- **DXF nemá v sebe súradnicový systém.** Pri importe ho treba v Trimble zvoliť ručne a rovnaký ako v projekte.
- **Orientácia osí:** súradnice sú v GIS orientácii East-North, teda záporné (X od −591 000 do −165 000,
  Y od −1 334 000 do −1 133 000). Ak projekt používa kladné geodetické Y/X (juhozápadná orientácia), dáta budú na úplne
  inom mieste. Pozná sa to na prvý pohľad, nie je to posun o meter.
- **Samotné hranice JPRL nie sú geodetické zameranie.** Zakresľujú sa pri obnove PSL, často z ortofotomáp, s presnosťou
  rádovo metrov. Ani dokonalý prevod nespraví z porastovej mapy centimetrovú.

## Ako boli dáta spracované a overené

- Základ je geometria NLC v **JTSK03** (EPSG:8353). Tú NLC vydáva ako primárnu. JTSK03 verzia je preto bez akejkoľvek
  transformácie, len bez prázdnej Z-súradnice.
- **S-JTSK** je prepočítaný oficiálnou interpolačnou tabuľkou GKÚ `sk_gku_JTSK03_to_JTSK.tif` (EPSG operácia
  „S-JTSK [JTSK03] to S-JTSK (1)“). Výsledok som porovnal s S-JTSK verziou, ktorú vydáva samo NLC
  (`JPRL_2025gpkg.zip`). Zhoda je **0,1 mm**, teda prakticky identická.
- **ETRS89** je prepočítaný kľúčom GKÚ (Burša–Wolf, 7 parametrov). Kontrolný spätný prepočet pôvodným kľúčom GKÚ z roku 2011
  (dX = −485,021 m, dY = −169,465 m, dZ = −483,839 m, ωX = 7,786342″, ωY = 4,397554″, ωZ = 4,102655″) sedí do **1,4 cm**.
- Prepočty používajú výhradne oficiálne operácie GKÚ. Program skontroluje, že nepoužil náhradnú približnú transformáciu.
  Tú by PROJ ticho použil, keby chýbala tabuľka, a výsledok by bol posunutý o meter.
- 2 926 neplatných geometrií zo zdroja (samopretínanie) je opravených, tvar sa nezmenil (Hausdorffova vzdialenosť
  voči zdroju 0,0 mm).
- Prekrytie s ortofotomapou ZBGIS: hranice lesných ciest sedia s cestami na snímke (`overenie/kontrola_ortofoto.jpg`).
- Úplnosť: každý z 585 328 polygónov je v každej variante práve raz. Každý obrys a popis z SHP je aj v DXF.
  Výsledky kontrol sú v `overenie/vysledky.txt`, kód v `build.py` a `verify.py`.

## DXF

DXF R12, jednotky metre, 2D. Vrstvy:

- `JPRL_POROSTY` – hranice porastov (zelená)
- `JPRL_INE_POZEMKY` – ostatné lesné pozemky: cesty, sklady, elektrovody… (sivá)
- `JPRL_OZNACENIE` – označenie porastu v strede plochy, výška textu 4 m. Porast: dielec + čiastková plocha +
  porastová skupina, napr. `1299c`, `2015a3`, `2404_3`. Ostatný lesný pozemok: `dielec/plocha`, napr. `5/62`.

Atribúty má len shapefile. DXF obsahuje iba čiary a popisy.

## Atribúty v shapefile

Kódovanie UTF-8 (súbor `.cpg`). Jeden riadok je jeden polygón. Pri viacetážových porastoch sú hodnoty z **hlavnej etáže**:
etáž 0, ak existuje, inak etáž 1–4 s najväčšou výmerou. Súhrny za všetky etáže sú v poliach `ET_POCET`, `VEK_MIN`,
`VEK_MAX` a `ZAS_SPOLU`.

| Pole | Význam |
|---|---|
| IDJPRL, IDPS, IDOLP | identifikátor JPRL, porastu (spojenie s opisom NLC), ostatného lesného pozemku |
| OZNAC | označenie (ako popis v DXF) |
| KPL, TxLC | kód a názov lesného celku |
| DC, CP, PS / DP, PC | dielec, čiastková plocha, porastová skupina / dielec a plocha ostatného lesného pozemku |
| DRUH_POZ | druh pozemku (Lesné porasty, Lesné cesty, Lesné sklady…) |
| RZP, RUP | rok začiatku a konca platnosti PSL |
| PLOCHA_HA | výmera polygónu v ha |
| ET_HL, ET_POCET | hlavná etáž, počet etáží |
| VEK | vek hlavnej etáže **k roku RZP** (tak ho vedie NLC) |
| VEK_AKT | vek prepočítaný na rok 2026 (VEK + 2026 − RZP). Pozor, porast vyťažený po schválení PSL tu je stále starý les |
| VEK_MIN, VEK_MAX | najnižší a najvyšší vek cez etáže |
| DREVINY | drevinové zloženie hlavnej etáže, napr. `BK 55, SM 30, JD 15` (%) |
| DR1–DR3, ZS1–ZS3 | tri hlavné dreviny a ich zastúpenie v % |
| ZASHA1 | zásoba hlavnej dreviny na 1 ha (m³) |
| ZAS_SPOLU | zásoba porastu spolu za všetky etáže a dreviny (m³) |
| KL, PK | kategória lesa (H hospodársky, O ochranný, U osobitného určenia), písmeno subkategórie |
| SOP, ZOP | stupeň ochrany prírody 1–5, zóna |
| NS, UEV, CHVU | chránené územie, územie európskeho významu, chránené vtáčie územie |
| ZK, RS | zakmenenie, rastový stupeň |
| HSLT, LT1 | hospodársky súbor lesných typov, hlavný lesný typ |
| EXPOZ, SKLON | expozícia, sklon |
| RD, OD, SOBH | rubná doba, obnovná doba, spôsob obhospodarovania |
| PHO | pásmo hygienickej ochrany |
| PRAVOPLAT | 1 = PSL schválený |
| POZNAMKA | slovný opis porastu z PSL (skrátený na 200 znakov) |

Kódy (dreviny, lesné typy…) podľa vyhlášky MPRV SR č. 297/2011 Z. z. Ten istý kód môže v rôznych stĺpcoch znamenať niečo iné.
Ostatné lesné pozemky nemajú opisné polia vyplnené.

Pozor, NLC uvádza opis ako UTF-8, ale v skutočnosti je v kódovaní Windows-1250. Tu je už správne prevedený.
