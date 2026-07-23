/* =========================================================================
   Fallen Grid — Ads-facade (EKSEMPEL, ikke i brug endnu)
   -------------------------------------------------------------------------
   Kopieres ind i spillets <script> i V7.0 (tilpasset Store/Telemetry/byId).
   Spillogikken må KUN tale med `Ads` — aldrig direkte med backends.
   To backends:
     - NullAds  : browser/dev. I dev-mode simuleres ads med en overlay-dialog,
                  så hele flowet (kadence, rewards, caps) kan play-testes uden
                  AdMob. I alm. web-drift er den ren no-op (tilbud skjules).
     - AdMobAds : Capacitor + @capacitor-community/admob (Android). Bruger
                  Googles TEST-ad-units indtil Play-release.
   Balance-invarianter (fra SPEC.md §4) er kommenteret ved hver guard.
   ========================================================================= */

/* ---------- Null-backend (browser / dev-simulering) ---------- */
const NullAds = {
  dev: false, // slås til fra Settings ("Dev · Simulate Ads") — persisted i Store("adSim")
  init() { this.dev = Store.get("adSim", false); },
  available() { return this.dev; },            // uden dev-sim: ingen tilbud i browseren
  showInterstitial(done) {
    if (!this.dev) return done();
    this._dialog("[DEV] Interstitial", ["OK"], () => done());
  },
  showRewarded(onReward, onSkip) {
    if (!this.dev) return onSkip && onSkip();
    this._dialog("[DEV] Rewarded video", ["Fuldfør (giv reward)", "Annullér"],
      (i) => (i === 0 ? onReward() : onSkip && onSkip()));
  },
  // minimal overlay-dialog i spillets egen stil (ingen window.confirm — den fryser RAF)
  _dialog(title, btns, cb) {
    const w = document.createElement("div");
    w.style.cssText = "position:fixed;inset:0;background:rgba(4,8,10,0.82);z-index:99;display:flex;align-items:center;justify-content:center";
    w.innerHTML = `<div style="background:#101820;border:1px solid #2c3a42;border-radius:8px;padding:18px;min-width:230px;text-align:center">
      <div style="color:#f2b23a;font:800 13px ui-monospace,monospace;margin-bottom:12px">${title}</div>
      ${btns.map((b, i) => `<button data-i="${i}" style="display:block;width:100%;margin:6px 0;padding:10px;background:#16222b;color:#dfe8ec;border:1px solid #2c3a42;border-radius:5px;font:700 12px ui-monospace,monospace">${b}</button>`).join("")}
    </div>`;
    w.querySelectorAll("button").forEach((b) => (b.onclick = () => { w.remove(); cb(+b.dataset.i); }));
    document.body.appendChild(w);
  },
};

/* ---------- AdMob-backend (Capacitor / Android) ---------- */
const AdMobAds = {
  // Googles officielle TEST-ids — udskiftes FØRST ved Play-release (V7.4)
  ids: {
    int: "ca-app-pub-3940256099942544/1033173712",
    rew: "ca-app-pub-3940256099942544/5224354917",
  },
  ready: false,
  async init() {
    try {
      const { AdMob } = Capacitor.Plugins;
      await AdMob.initialize();
      // UMP-consent (GDPR): kræves i EEA/UK FØR første ad-request
      const info = await AdMob.requestConsentInfo();
      if (info.isConsentFormAvailable && info.status === "REQUIRED") await AdMob.showConsentForm();
      this.ready = true;
    } catch (e) { this.ready = false; }
  },
  available() { return this.ready; },
  async showInterstitial(done) {
    try {
      const { AdMob } = Capacitor.Plugins;
      await AdMob.prepareInterstitial({ adId: this.ids.int });
      const l = await AdMob.addListener("interstitialAdDismissed", () => { l.remove(); done(); });
      await AdMob.showInterstitial();
    } catch (e) { done(); } // ad kunne ikke loades (offline etc.) → spillet fortsætter bare
  },
  async showRewarded(onReward, onSkip) {
    try {
      const { AdMob } = Capacitor.Plugins;
      let rewarded = false;
      const lr = await AdMob.addListener("onRewardedVideoAdReward", () => { rewarded = true; });
      const ld = await AdMob.addListener("onRewardedVideoAdDismissed", () => {
        lr.remove(); ld.remove();
        rewarded ? onReward() : onSkip && onSkip(); // KUN reward ved fuldført video
      });
      await AdMob.prepareRewardVideoAd({ adId: this.ids.rew });
      await AdMob.showRewardVideoAd();
    } catch (e) { onSkip && onSkip(); }
  },
  async openPrivacyOptions() { // Settings → "Privatlivsvalg" (Play-krav i EEA)
    const { AdMob } = Capacitor.Plugins;
    await AdMob.resetConsentInfo();
    const info = await AdMob.requestConsentInfo();
    if (info.isConsentFormAvailable) await AdMob.showConsentForm();
  },
};

/* ---------- Facaden (det eneste, spillet kalder) ---------- */
const Ads = {
  backend: null,
  enabled: true,            // false ved "Remove Ads"-IAP (Store("adsRemoved")) eller ren web
  sessionRuns: 0,           // nulstilles pr. app-start
  runsSinceInt: Store.get("runsSinceInt", 0),
  lastIntAt: 0,
  rewardedJustShown: false, // SPEC §2.1: aldrig interstitial lige efter rewarded

  init() {
    this.enabled = !Store.get("adsRemoved", false);
    this.backend = (window.Capacitor && Capacitor.isPluginAvailable && Capacitor.isPluginAvailable("AdMob"))
      ? AdMobAds : NullAds;
    this.backend.init();
  },

  _day() { return new Date().toISOString().slice(0, 10); },
  _daily(k) { const d = Store.get("adDaily", {}); return d.day === this._day() ? (d[k] || 0) : 0; },
  _bumpDaily(k) {
    let d = Store.get("adDaily", {});
    if (d.day !== this._day()) d = { day: this._day() };
    d[k] = (d[k] || 0) + 1; Store.set("adDaily", d);
  },

  // kaldes fra reset(): tæller runs til interstitial-kadencen
  noteRunStart() {
    this.sessionRuns++; this.runsSinceInt++;
    Store.set("runsSinceInt", this.runsSinceInt);
    Store.set("totalRuns", Store.get("totalRuns", 0) + 1);
  },

  // Interstitial ved skærm-forladelse. `done` kører ALTID (ad eller ej).
  maybeInterstitial(done) {
    const ok = this.enabled && this.backend.available()
      && Store.get("totalRuns", 0) > 3          // SPEC: livstids-grace (onboarding)
      && this.sessionRuns > 2                   // SPEC: session-grace
      && this.runsSinceInt >= 3                 // SPEC: "efter 2-3 baner"
      && Date.now() - this.lastIntAt >= 240000  // SPEC: min 4 min
      && this._daily("int") < 6                 // SPEC: max 6/dag
      && !this.rewardedJustShown;
    this.rewardedJustShown = false;
    if (!ok) return done();
    this.backend.showInterstitial(() => {
      this.runsSinceInt = 0; Store.set("runsSinceInt", 0);
      this.lastIntAt = Date.now(); this._bumpDaily("int");
      Telemetry.ev("adInt");
      done();
    });
  },

  // Kan et rewarded-tilbud overhovedet vises? (styrer om knappen renderes)
  canOffer(slot) {
    if (!this.enabled || !this.backend.available()) return false;
    if (slot === "R2" && this._daily("r2") >= 3) return false;   // SPEC: R2 max 3/dag
    return true;
  },

  // Viser rewarded-video for et slot; onReward kaldes KUN ved fuldført video.
  offer(slot, onReward) {
    if (!this.canOffer(slot)) return;
    this.backend.showRewarded(() => {
      this.rewardedJustShown = true;
      if (slot === "R2") this._bumpDaily("r2");
      Telemetry.ev("ad" + slot);                 // adR1 / adR2 / adR3 i play-loggen
      onReward();
    });
  },

  openPrivacyOptions() { if (this.backend.openPrivacyOptions) this.backend.openPrivacyOptions(); },
};

/* =========================================================================
   Integrations-cheatsheet (detaljer + præcise ankre: se PLAN.md V7.0 §2)
   - reset()                : Ads.noteRunStart()  (+ S.revived=false, S.alloyDoubled=false)
   - gameover/victory exits : wrap i Ads.maybeInterstitial(() => {...})
   - gameover-panel         : R1 Second Wind  → restore 50% core, én gang, ikke Daily,
                              ✦ perfekt forbliver umulig (S.leaked er allerede true)
   - victory-panel          : R2 Double Alloy → Meta.add(S.lastAlloy); S.lastAlloy *= 2
   - deploy (free/campaign) : R3 Supply Drop  → S.pendingBoost=1.5, forbruges i reset()
   - Settings               : "Privatlivsvalg" → Ads.openPrivacyOptions()
                              "Dev · Simulate Ads" → Store("adSim") (kun Null-backend)
   ========================================================================= */
