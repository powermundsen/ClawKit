# Endringslogg

Alle vesentlige endringer dokumenteres her. Formatet følger prinsippene i
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), og versjoner følger
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Hver release skal skille mellom funksjoner, sikkerhet, personvern, migrering og
kompatibilitetsbrudd. `release-manifest.json` er den maskinlesbare kontrakten.

## [Unreleased]

### Added

- Telegram-kommandoen `/stop` avbryter aktiv providerprosess, tømmer både
  minne- og diskkøen og lukker Claude- og Codex-sesjonene uten resume.
- Egen kapabilitetsgrense (`router/capabilities.py`) for provideragentene:
  Claude får bare lokale filverktøy (`Read`, `Edit`, `Write`, `Glob`, `Grep`)
  og Codex kjører bare i `read-only`/`workspace-write`-sandbox. Adapterne
  validerer grensen ved konstruksjon, så en konfigurasjon med et verktøy eller
  en sandbox som kan nå utenfor instansen feiler ved oppstart, ikke ved første
  agentkall. Testet i `tests/test_capabilities.py`.
- GitHub Actions-CI på macOS/Linux og Python 3.10/3.12, issue-/PR-maler,
  `CODEOWNERS`, MIT-lisens og en releaseworkflow som bygger draft, laster opp
  alle assets og først deretter publiserer.
- Offentlig distribusjon fra én ny, sanitert rotcommit. Tidligere privat
  utviklingshistorikk beholdes separat og eksponeres ikke.
- Releaseartefakter med maskinlesbart manifest, samlet `SHA256SUMS` og en
  sperre som krever eksplisitt bekreftet GitHub release immutability.
- `clawkit update check|download|install` for stabil GitHub Release-discovery,
  manifestvisning, checksumverifisert nedlasting og kontrollert installasjon
  gjennom eksisterende health-, backup- og rollbackflyt.
- Ukentlig updatevarsel med berørte moduler, persondataeffekt og migreringer.
  Sjekken installerer aldri automatisk.
- Felles skill-discovery for Claude `.claude/skills/` og Codex
  `.agents/skills/`, med én kanonisk kilde, administrerte symlinker,
  kollisjonskontroll og health check.
- Avskrudd modulgrensesnitt for konfigurasjon, planlagte lokale jobber,
  agentkontekst, varsler og health check.
- Valgfri `local-health`-modul med privat SQLite, streamingimport av Apple
  Health XML, eventdeduplisering og lokale Markdown-/JSON-sammendrag.
- Bundled `training-analysis`-skill med tydelig grense mellom
  treningsrefleksjon og medisinsk rådgivning.
- `clawkit logs` for filtrert lokal driftsmetadata og `clawkit support-bundle`
  for en privat, sanitert diagnostikkpakke uten config eller helsedata.
- Arbeidskopi- og historikkskann for private stier, credentials, private nett,
  runtimefiler og reserverte private identifikatorer.

### Changed

- Lokal JSONL-audit roteres ved 5 MiB og beholder fem private segmenter.
- Supportpakker krever en ny absolutt fil i en eksisterende katalog og endrer
  aldri rettighetene på katalogen brukeren valgte.
- GitHub asset-redirects er allowlistet, og Authorization-header fjernes før
  nedlasting fra GitHubs separate assetdomene.

### Fixed

- `install.sh` sammenligner nå en gjenoppbygd payload mot en allerede
  installert utgivelse med samme versjonsnummer via innholdshash
  (`release.payload_matches_release`). En omkjøring med endret kode under
  samme versjon feiler tydelig i stedet for å beholde den gamle utgivelsen
  stille. En uendret payload installeres fortsatt på nytt uten feil.
- `clawkit training` uten underkommando velger nå `status` som dokumentert.
- Nedlastede releasearkiv checksumverifiseres før kommandoen omtaler dem som
  verifisert.

### Privacy

- Helseeksport, SQLite, sammendrag og modulstate ligger utenfor Git og
  releasebackup. Bare det begrensede Markdown-sammendraget kan injiseres i
  agentkonteksten etter eksplisitt modulaktivering.
- Supportpakker utelater secrets, config, samtaler og rå helse-/treningsdata.

### Migration

- Ingen migreringer. `local-health` er av som standard og oppretter først
  state etter eksplisitt aktivering og bruk.

## [0.2.0] - 2026-07-28

### Added

- Grunnleggende dokumentasjon for formål, arkitektur, personvern, sikkerhet,
  installasjon og kontrollert oppgradering.
- Første referanseplattform definert som native macOS på både eldre Intel Mac
  og Apple Silicon. Lima/Linux-VM er valgfri isolasjon, ikke et krav.
- Filvis avhengighetsanalyse og foreslått allowlist for første saniterte
  kodeuttrekk.
- Python-packagegrunnlag med injiserbare XDG-stier, streng lesing av runtime-
  og secretskonfigurasjon, privat lokal JSONL-audit og sikker
  Telegram-formattering.
- Telegram-klient, vedvarende innboks og utboks, krasjgjenopptak, retry per
  svarbit, aktivitetssignal, Claude/Codex-router, sesjonskontinuitet og
  saniterte brukerfeil.
- Interaktivt instans- og Telegram-oppsett, abonnementskontroll, health check,
  LaunchAgent, systemd-brukertjeneste og kommandolinjeverktøy.
- Selvutpakkende installer med administrert Python, offisielle agent-CLI-er,
  releasebygging, verifisert lokal oppgradering og atomisk rollback.
- Godkjent og idempotent førstesamtale, varig kontekstinnlasting og lokal
  påminnelsesmotor.
- 147 isolerte tester for stier, config, audit, Telegram, router, prosesskontroll,
  installer, tjenester, releases og simulert ende-til-ende-flyt.

### Security

- Kontrakt for lokale hemmeligheter, read-only deploy key, eksplisitt
  godkjenning og sanitert logging.
- Private katalog- og filrettigheter, avvisning av symlinker og hemmeligheter
  samt allowlistede auditfelt er håndhevet i grunnpakken.
- Leverandørinstallasjoner kjører i tomt, allowlistet miljø med separate HOME-,
  XDG- og credentialkataloger. Simulert test verifiserer at global npm-,
  NVM- og API-konfigurasjon ikke arves.
- Agentprosesser får et separat allowlistet runtime-miljø uten bot-token,
  GitHub-token, API-nøkler, vilkårlige private variabler eller global `PATH`.
- Releasemanifest og releasearkiv avviser symlinker, traversering, ugyldige
  typer, for store filer og checksumavvik.
- Installeren skiller kilde fra runtime, avviser Git-arbeidskopier og umerkede
  ikke-tomme kataloger, og godtar aldri endret innhold i en eksisterende
  versjon.
- Oppgradering krever grønn health check før endring, tar backup og
  beskyttet-fil-hash, verifiserer den nye releasen etter restart og gjenoppretter
  forrige verifiserte release automatisk ved feil.
- Eksterne handlinger krever en konkret, separat eierbekreftelse.

### Privacy

- Strengt skille mellom versjonert plattformkode, personlig instans og lokal
  runtime-state.
- Onboardingen forklarer korrekt at meldinger går gjennom Telegram og valgt
  modellleverandør, og at en native agentprosess kan lese det OS-brukeren kan
  lese selv om ClawKit bare bruker filer utenfor instansen etter bestilling.
- Pakken utfører ingen filskriving, nettverkskall eller prosessstart ved import.
  Testene bruker midlertidige kataloger, falske leverandører og ingen ekte
  hjemmekatalog eller abonnementskall.

### Migration

- Ingen migreringer. 0.2.0 avviser manifest som deklarerer migrering.

### Breaking

- Runtime og kildekode kan ikke lenger dele Git-arbeidskopi. Bruk en separat,
  tom runtimekatalog.
- Den interne 0.1.0-kandidaten erstattes av 0.2.0. Det finnes ingen støttet
  produksjonsinstans som må migreres.
