# Lokal helse og treningsanalyse

`local-health` er en valgfri modul for treningstrender uten Splunk, server eller
betalbar API. Modulen er av som standard.

## Dataflyt

1. Brukeren eksporterer Apple Health-data fra Helse-appen på iPhone.
2. `export.zip` pakkes ut lokalt, og `export.xml` gis eksplisitt til ClawKit.
3. ClawKit streamer utvalgte workouts og numeriske målinger til privat SQLite.
4. Modulen skriver `training-summary.md` og `training-summary.json` med modus
   `0600` under modulens private statekatalog.
5. Bare Markdown-sammendraget legges i agentkonteksten. Rå XML, SQLite og
   import-ID sendes ikke til Claude eller OpenAI.

Eksportfilen endres eller slettes aldri av ClawKit. Importen dedupliserer både
hele eksportfiler og individuelle events.

## Aktivering

Legg modulen inn i `config/runtime.env`:

```dotenv
CLAWKIT_MODULES=local-health
```

Restart deretter tjenesten og kontroller status:

```sh
clawkit service restart
clawkit training status
```

Aktivering er et eksplisitt samtykke til at det genererte sammendraget kan
sendes til valgt agentleverandør når assistenten svarer. Deaktivering gjøres ved
å fjerne `local-health` fra `CLAWKIT_MODULES` og restarte tjenesten. Lokale data
slettes ikke automatisk.

## Import og sammendrag

```sh
clawkit training import /absolutt/sti/til/export.xml
clawkit training summarize
clawkit training status
```

Import krever en absolutt, vanlig fil. Symlinker, ugyldig XML, omvendte
tidsintervaller og eksport over størrelsesgrensen avvises. Databasen inneholder
workouts og et begrenset sett numeriske Health-målinger som aktivitet,
distanse, puls, HRV, hvilepuls, steg, kroppsmasse og VO2 max.

## Agentanalyse

Den medfølgende `training-analysis`-skillen bruker bare
`<clawkit_module_context>`. Den skiller observasjon fra tolkning, sier fra om
manglende data og behandler puls, HRV, hvilepuls, VO2 max og kroppsmasse som
trender, ikke diagnoser.

## Backup og sletting

Helsemodulens database og sammendrag inngår ikke i en ClawKit-release eller
supportpakke. Brukeren må selv velge eventuell kryptert lokal backup. Full
sletting er en eksplisitt handling mot modulens private statekatalog og skjer
aldri ved vanlig avinstallasjon eller deaktivering.
