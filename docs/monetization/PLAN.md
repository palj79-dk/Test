# Fallen Grid — Monetization Implementeringsplan (V7-linjen)

> Status: **PLAN — ikke implementeret.** Læs `SPEC.md` først (design + balance + compliance).
> Kodeeksemplerne her bruger de faktiske anker-strenge fra `fallengrid-v6.7.html`,
> så de kan omsættes direkte til `rep(old, new)`-byggescripts som alle tidligere iterationer.

## Overblik over iterationer

| Iter | Indhold | Kan testes i browser? |
|---|---|---|
| **V7.0** | `Ads`-facade + ALLE integrationspunkter med Null-backend + dev-simulering | ✅ Ja — hele balancen testes uden AdMob |
| **V7.1** | Capacitor-projekt (`android/`-skelet, config, build-scripts) | Emulator/enhed |
| **V7.2** | AdMob-plugin + UMP-consent + test-ad-units | Emulator/enhed |
| **V7.3** | Play-forberedelse: privacy policy, data safety, ikoner, AAB, intern test | Play Console |
| **V7.4** | Tuning fra telemetri (ad-events i play-logs) + rigtige ad-unit-IDs | Produktion |

Rækkefølgen er bevidst: **V7.0 gør hele reklame-økonomien spilbar og testbar i browseren**
(med samme play-log-loop som al V6-tuning), før der overhovedet røres ved Android.

---

## V7.0 — Ads-facade + integrationspunkter (Null-backend)

### 1. Facaden (indsættes som modul i spillets script)

Fuld kode i `ads.example.js`. Kerneidé:

```js
const Ads = {
  backend: null,            // NullAds (browser/dev) eller AdMobAds (Capacitor)
  enabled: true,            // false ved fremtidig "Remove Ads"-IAP eller ren web-build
  runsSinceInt: 0,          // interstitial-kadence
  lastIntAt: 0, intToday: 0, r2Today: 0,
  init() { this.backend = (window.Capacitor?.isPluginAvailable?.("AdMob")) ? AdMobAds : NullAds; this.backend.init(); },
  // kaldes når spilleren FORLADER en resultat-skærm
  maybeInterstitial(done) { /* kadence-guards fra SPEC §2.1, ellers done() direkte */ },
  // rewarded-tilbud; giver KUN reward hvis videoen fuldføres
  offer(slot, onReward) { /* R1/R2/R3; caps; Telemetry.ev("ad"+slot) */ },
};
```

Nøgle-guards (skal med i verify):

```js
maybeInterstitial(done) {
  const now = Date.now();
  const ok = this.enabled
    && Store.get("totalRuns", 0) > 3            // livstids-grace (onboarding)
    && this.sessionRuns > 2                     // session-grace
    && this.runsSinceInt >= 3                   // "efter 2-3 baner"
    && now - this.lastIntAt >= 240000           // min 4 min mellem
    && this.intToday < 6                        // dagligt loft
    && !this.rewardedJustShown;                 // aldrig dobbelt-reklame
  if (!ok) return done();
  this.backend.showInterstitial(() => { this.runsSinceInt = 0; this.lastIntAt = now;
    this.intToday++; Telemetry.ev("adInt"); done(); });
}
```

`NullAds` viser i dev-mode en lille overlay-dialog ("[DEV] Interstitial — OK?" /
"[DEV] Rewarded R2 — fuldfør? Annullér?") så flowet kan mærkes og testes i browseren;
i alm. web-drift er den ren no-op (tilbud skjules).

### 2. Integrationspunkter (præcise ankre i `fallengrid-v6.7.html`)

**a) Run-tæller** — i `reset()` (anker: `S.medalChecked = false; S.medalMsg = "";`):

```js
Ads.sessionRuns = (Ads.sessionRuns || 0) + 1; Ads.runsSinceInt++;
Store.set("totalRuns", Store.get("totalRuns", 0) + 1);
```

**b) Interstitial ved skærm-forladelse** — gameover/victory-knapperne wrappes.
Anker (gameover): `byId("r").onclick = () => { reset(); S.screen = "playing"; render(); };`

```js
byId("r").onclick = () => Ads.maybeInterstitial(() => { reset(); S.screen = "playing"; render(); });
byId("m").onclick = () => Ads.maybeInterstitial(() => { S.screen = "menu"; render(); });
// victory: samme mønster for "r", "m" og "nm" (Next Mission) — IKKE for "a" (Armory er stadig samme flow)
```

**c) R1 · Second Wind** — på gameover-panelet.
Anker: `<h2>Reactor Lost</h2>` (indsæt knap før "Redeploy") + guard `!S.isDaily && !S.revived`:

```js
${Ads.canOffer("R1") && !S.isDaily && !S.revived ?
  `<button class="btn" id="rev">📺 Second Wind · restore ${Math.ceil(S.coreMax/2)} core</button>` : ""}
// handler:
const rv = byId("rev"); if (rv) rv.onclick = () => Ads.offer("R1", () => {
  S.revived = true; S.core = Math.ceil(S.coreMax / 2);
  S.screen = "playing"; S.banner = { text: "SECOND WIND", t: 1.9 }; render();
});
```

Balance-invariant: `S.leaked` er allerede true (ellers var vi ikke på gameover) ⇒
✦ perfekt er automatisk umulig i et genoplivet run. `S.revived` nulstilles i `reset()`.
NB: gameover-stien har allerede kørt `runAchCheck(false)`/`awardAlloy` — revive skal
**genåbne run'et FØR de hooks**, dvs. R1-versionen af gameover-skærmen kræver at
`Telemetry.end`/`awardAlloy`/`runAchCheck` udskydes til spilleren har fravalgt R1
(detalje-design i V7.0-bygget; enklest: vis R1-valget som en "pre-gameover"-skærm).

**d) R2 · Double Alloy** — på victory-panelet.
Anker: `<div class="wallet">⬡ +${S.lastAlloy} ALLOY` (tilføj knap under):

```js
${Ads.canOffer("R2") && !S.alloyDoubled ?
  `<button class="btn" id="dbl">📺 Double Alloy · +${S.lastAlloy} ⬡</button>` : ""}
// handler:
const db = byId("dbl"); if (db) db.onclick = () => Ads.offer("R2", () => {
  Meta.add(S.lastAlloy); S.lastAlloy *= 2; S.alloyDoubled = true; render();
});
```

**e) R3 · Supply Drop** — på Free Play-deploy og Campaign-deploy.
Ankre: `byId("go").onclick` (freeplay) og `byId("cgo").onclick` (campaign): tilføj en
lille checkbox/knap over Deploy; effekten sættes som `S.pendingBoost = 1.5` og forbruges
i `reset()` hvor start-scrap beregnes (anker: `S.scrap = Math.round((baseStartScrap()`).

**f) Telemetri** — nye felter i `Telemetry.begin`-recorden: `adInt: 0, adR1: 0, adR2: 0, adR3: 0`
(anker: `earlySends: 0, overlapSends: 0,`) + `Telemetry.ev("adR1")` osv. i facaden.

**g) Settings** — "Privatlivsvalg"-knap (åbner UMP-form igen; Null-backend: vis info-tekst).
Anker: settings-skærmens Dev-sektion.

### 3. Verify (V7.0)

- Interstitial-kadence: 3 runs → tilbud; grace (første 3 livstid + 2 session) respekteres;
  240s-minimum; ingen interstitial efter rewarded.
- R1: kun på ikke-Daily gameover, én gang pr. run; revive genåbner spillet med halv core;
  ✦ umulig; medalje stadig mulig.
- R2: fordobler præcis (inkl. medaljebonus), cap 3/dag, kun én gang pr. victory.
- R3: +50% start-scrap i næste run, ikke i Daily.
- `Ads.enabled=false` ⇒ ingen knapper/ingen dialogs nogen steder.
- Fuld `verify_core`-regression uændret grøn.

---

## V7.1 — Capacitor-skelet

```bash
npm init -y && npm i @capacitor/core @capacitor/cli @capacitor/android
npx cap init "Fallen Grid" "dk.lundjacobsen.fallengrid" --web-dir=www
mkdir -p www && cp fallengrid-v7.x.html www/index.html   # build-script kopierer + omdøber
npx cap add android
```

`capacitor.config.ts`:

```ts
import { CapacitorConfig } from '@capacitor/cli';
const config: CapacitorConfig = {
  appId: 'dk.lundjacobsen.fallengrid',
  appName: 'Fallen Grid',
  webDir: 'www',
  android: { backgroundColor: '#06090c' },
};
export default config;
```

- `android/app/build.gradle`: `targetSdkVersion 36` (Play-krav for nye apps fra 31/8-2026).
- Spillets V4.6-arbejde (Capacitor back-button, lifecycle-pause, haptics, safe-area) virker
  allerede — `window.Capacitor`-detektionen findes i koden.
- Repo-læg: `android/`-mappen committes; `www/` genereres af build-script (gitignore).

## V7.2 — AdMob + UMP

```bash
npm i @capacitor-community/admob && npx cap sync
```

`AndroidManifest.xml` (i `<application>`):

```xml
<meta-data android:name="com.google.android.gms.ads.APPLICATION_ID"
           android:value="ca-app-pub-XXXXXXXXXXXXXXXX~YYYYYYYYYY"/>
```

`AdMobAds`-backend (skitse — fuld version i `ads.example.js`):

```js
const AdMobAds = {
  ids: { int: "ca-app-pub-3940256099942544/1033173712",      // Googles TEST-id
         rew: "ca-app-pub-3940256099942544/5224354917" },    // udskiftes i V7.4
  async init() {
    const { AdMob } = Capacitor.Plugins;
    await AdMob.initialize();
    const info = await AdMob.requestConsentInfo();           // UMP
    if (info.isConsentFormAvailable && info.status === "REQUIRED") await AdMob.showConsentForm();
  },
  async showInterstitial(done) {
    const { AdMob } = Capacitor.Plugins;
    try { await AdMob.prepareInterstitial({ adId: this.ids.int });
          await AdMob.showInterstitial(); } catch (e) {} finally { done(); }
  },
  async showRewarded(onReward, onSkip) {
    const { AdMob } = Capacitor.Plugins;
    try {
      const got = await new Promise(async (res) => {
        const l = await AdMob.addListener("onRewardedVideoAdReward", () => res(true));
        const d = await AdMob.addListener("onRewardedVideoAdDismissed", () => res(false));
        await AdMob.prepareRewardVideoAd({ adId: this.ids.rew });
        await AdMob.showRewardVideoAd();
        // res(true) fra reward-listener vinder over dismiss
      });
      got ? onReward() : onSkip && onSkip();
    } catch (e) { onSkip && onSkip(); }
  },
};
```

Regler: **KUN test-IDs indtil Play-releasen** (rigtige IDs i udvikling = risiko for AdMob-ban).
Consent-genåbning fra Settings: `AdMob.resetConsentInfo()` + `requestConsentInfo()`.

## V7.3 — Play-forberedelse

1. Privacy policy + `app-ads.txt` hostes (forslag: GitHub Pages fra dette repo, `docs/`-branch).
2. Play Console: app oprettes, **Data safety** udfyldes (AdMob: device IDs, ad interactions,
   diagnostics — "shared with third parties for advertising").
3. IARC content rating; målgruppe 13+.
4. Ikon (512px), feature graphic (1024×500), 4-8 screenshots (portræt).
5. `bundleRelease` → AAB → **intern test-track** først.

## V7.4 — Tuning

- Ad-events er i play-loggen fra V7.0 ⇒ samme analyse-loop som V6:
  ser vi R2-opt-in >60%? Er interstitial-frekvensen reelt ~1 pr. 3 runs?
  Falder session-længden efter interstitials? (i så fald: kadence 3→4 runs).
- Udskift test-IDs med rigtige ad-units; slå `mediation` til senere hvis eCPM skuffer.

---

## Åbne beslutninger (tages når V7.0 startes)

1. R1-flowets præcise skærm ("pre-gameover"-skærm vs. udskudte hooks) — se V7.0.2c.
2. Skal R2 også tilbydes på gameover (halv effekt)? (Anbefaling: nej, hold det simpelt.)
3. App-id (`dk.lundjacobsen.fallengrid`?) og AdMob-kontoens ejerskab.
4. "Remove Ads"-IAP i første release eller vente? (Anbefaling: vente til V7.5+, men
   `Ads.enabled`-flaget bygges fra start.)

## Kilder

- [capacitor-community/admob (GitHub)](https://github.com/capacitor-community/admob) ·
  [npm](https://www.npmjs.com/package/@capacitor-community/admob)
- [Google Play target API level requirements](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en) ·
  [Android Developers: target-sdk](https://developer.android.com/google/play/requirements/target-sdk)
