# Fallen Grid — Monetization Spec (Google Play + AdMob)

> Status: **SPEC — ikke implementeret.** Arbejdsdokument for V7-linjen.
> Se `PLAN.md` for iterationer og `ads.example.js` for facade-koden.

## 1. Mål og principper

Spillet skal tjene penge via reklamer på Google Play **uden at ødelægge den balance,
V6-linjen har bygget op** (threat-skalering, økonomi-taper, medalje-mestring). Regler:

1. **Aldrig reklamer midt i gameplay.** Kun mellem runs (menu/victory/gameover-skærme).
2. **Rewarded video er altid et tilbud, aldrig et krav.** Spillet kan gennemføres 100%
   uden at se en eneste reklame.
3. **Reklamer må ikke kunne købe mestring.** Medaljer og ✦ perfekt-mærker kan aldrig
   opnås *pga.* en reklame-fordel (se afsnit 4).
4. **Respekter den tunede økonomi.** Rewarded-fordele er kalibreret mod V6.5-tallene
   (kill-taper, alloy ÷1.5) — de giver *bekvemmelighed og comeback*, ikke god-mode.
5. **Onboarding er hellig.** Ingen interstitials i spillerens første runs.
6. Design for en fremtidig **"Fjern reklamer"-IAP** fra dag ét (ét globalt flag).

## 2. Reklameformater

### 2.1 Interstitial (fuldskærm efter 2-3 baner)

| Parameter | Værdi | Begrundelse |
|---|---|---|
| Trigger | Efter **hver 3. afsluttede run** (sejr ELLER nederlag tæller) | Brugerens ønske: "efter to-tre baner"; 3 er den skånsomme ende |
| Tidspunkt | Når spilleren forlader resultat-skærmen (tap på Redeploy/Menu/Next Mission) — **aldrig oven i selve resultatet** | Resultatet (medalje! alloy!) må ikke overskygges |
| Min. interval | ≥ **240 s** siden sidste interstitial | Hurtige runs (2-min tab) må ikke give reklame-spam |
| Grace period | De første **3 runs nogensinde** (persisted) + de første **2 runs pr. session** er altid reklamefri | Onboarding + session-opstart skal føles god |
| Undtagelser | Ingen interstitial lige efter en **rewarded** video (samme skærm-flow); ingen under Daily-streak-flowet før resultatet er vist | Dobbelt-reklame føles som straf |
| Cap | Max **6/dag** | Blødt loft; nås sjældent i praksis |

### 2.2 Rewarded video ("se video for en fordel") — 3 slots

**R1 · Second Wind (genopliv)** — på gameover-skærmen
- Tilbud: se video → genoptag run'et med **50% af core** gendannet.
- Én gang pr. run. Vises ikke i **Daily Op** (streak-integritet).
- Balance: et genoplivet run kan stadig tjene medalje (comeback er sjovt), men
  **aldrig ✦ perfekt** (core er tabt pr. definition) — så mestring forbliver ren.

**R2 · Double Alloy** — på victory-skærmen
- Tilbud: se video → **2× run'ets alloy** (inkl. medalje-bonus).
- Cap: **3/dag**. Balance: V6.5 satte alloy ÷1.5 for at strække meta-progressionen;
  2× for en reklame svarer ca. til før-nerf-raten — dvs. reklamen "køber tiden tilbage"
  uden at være hurtigere end den gamle, allerede accepterede fyldningstakt.

**R3 · Supply Drop (startboost)** — på deploy (Free Play + Campaign, ikke Daily)
- Tilbud: se video → **+50% start-scrap** i det kommende run.
- Balance: bekvemmelighed i early-game; påvirker ikke sen-økonomien (taperen styrer den).
  Ingen effekt på medaljer/✦ (fordelen er væk længe før wave 20 afgør noget).

**Bevidst fravalgt:**
- **Banner-ads: NEJ.** Ødelægger den håndbyggede mobile UI (safe-area, HUD-rækker) og
  koster FPS på lav-end enheder. Interstitial+rewarded tjener typisk alligevel 80-90%.
- Rewarded "gratis Armory-talent" — rører direkte ved threat-niveauet; for farlig kobling.
- App-open ads — understøttes ikke af plugin'et og føles påtrængende.

## 3. Frekvens-flow (opsummeret)

```
run slutter → resultat-skærm vises (medalje/alloy/rewarded-tilbud R1/R2)
  → spilleren forlader skærmen
      → runsSinceAd >= 3 ? og >= 240s siden sidst? og ikke i grace? og ingen rewarded lige vist?
          → JA: vis interstitial, nulstil tællere
          → NEJ: fortsæt direkte
```

## 4. Balance-invarianter (hårde regler, skal testes)

1. `✦ perfekt` kan **aldrig** opnås i et run hvor R1 (revive) er brugt.
2. Daily Op: intet R1, intet R3 (samme vilkår for alle dage/streaks). R2 er ok (kun meta).
3. Ingen reklame ændrer nogensinde `S.difficulty`, fjende-stats eller medal-tier-logik.
4. `Ads.enabled === false` (fremtidig IAP / web-version) ⇒ facade er 100% no-op, og
   rewarded-**tilbuddene** skjules (ikke bare deaktiveres).
5. Telemetri logger alle ad-events (`adInt`, `adR1/R2/R3`) så balancen kan efterprøves
   i play-logs, præcis som V6-tuningen blev det.

## 5. Teknisk fundament

- **Wrapper:** Capacitor (Android). Back-button/lifecycle/haptics er allerede bygget (V4.6).
- **Plugin:** [`@capacitor-community/admob`](https://github.com/capacitor-community/admob)
  — banner/interstitial/rewarded + **UMP consent** (GDPR). Ingen app-open/native formats.
- **Consent:** UMP-flow ved første start (EEA/UK: GDPR-besked; ellers evt. IDFA-besked).
  Opsættes i AdMob-konsollen ("Privacy & messaging"). Skal kunne genåbnes fra Settings
  ("Privatlivsvalg") — Play-krav for EEA.
- **Arkitektur i spillet:** én `Ads`-facade i den single-file HTML med to backends:
  `NullAds` (browser/dev — simulerer med dev-dialog) og `AdMobAds` (Capacitor).
  Spillogikken kalder KUN facaden. Se `ads.example.js`.

## 6. Google Play-krav (compliance-tjekliste)

| Krav | Detalje |
|---|---|
| Target SDK | **API 35 nu; API 36 (Android 16) for nye apps fra 31/8-2026** — byg direkte mod 36 |
| Format | AAB (App Bundle) + Play App Signing |
| UMP/GDPR | Consent-besked FØR første ad-request i EEA; "skift samtykke" i Settings |
| Data safety-formular | Deklarér AdMob-indsamling (device ID, diagnostics, ads interaction) |
| Privacy policy | Offentlig URL kræves (kan hostes som GitHub Pages i dette repo) |
| Content rating | IARC-spørgeskema; spillet er stiliseret sci-fi-vold → typisk PEGI 7/E10+ |
| Families | Målgruppe 13+ (undgå Families-politikkens strengere ad-krav) |
| app-ads.txt | Publiceres på samme domæne som privacy policy (AdMob verificering) |
| Test | AdMob **test-ad-units** i al udvikling; rigtige IDs kun i release-build (ellers konto-ban) |

## 7. Fremtid (uden for første version)

- **IAP "Remove Ads"** (~30-45 kr): sætter `Store("adsRemoved")` → `Ads.enabled=false`.
  Rewarded-fordele kan evt. beholdes gratis for købere (generøst, anbefalet).
- Cloud save (Play Games Services) — separat spor, kræves ikke for ads.

## Kilder

- [capacitor-community/admob (GitHub)](https://github.com/capacitor-community/admob)
- [npm: @capacitor-community/admob](https://www.npmjs.com/package/@capacitor-community/admob)
- [Google Play target API level requirements](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en)
- [Meet Google Play's target API level requirement (Android Developers)](https://developer.android.com/google/play/requirements/target-sdk)
