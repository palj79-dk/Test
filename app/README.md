# Fallen Grid — Android APK (unofficial / sideload)

This folder wraps the single-file game (`../fallengrid-v*.html`) in
[Capacitor](https://capacitorjs.com/) so it can be built into an installable
Android APK. No Google Play account, store listing, or ads are involved — this
is a personal/test build you install by hand ("sideload").

## How the APK is built (GitHub Actions — no local setup)

`.github/workflows/android.yml` runs on every push that touches the game or this
folder, and can also be started manually (Actions tab → **Build Android APK** →
*Run workflow*). It:

1. bundles the **newest** `fallengrid-v*.html` as `www/index.html`,
2. generates the Android project with Capacitor,
3. signs with the **committed stable debug keystore** (`keystore/debug.keystore`),
4. uploads `fallengrid-vX.YZ.apk` as a downloadable **artifact**.

Download it from the finished workflow run (Summary → Artifacts → `fallengrid-apk`).

## Install on the phone (Samsung / any Android)

1. Copy the `.apk` to the phone (USB, Google Drive, or email it to yourself).
2. Tap it in Files. Android asks to allow **"Install unknown apps"** for whatever
   app opened it (Files/Chrome/Drive) — allow it once.
3. Tap **Install**. Done — the game runs offline as a normal app.

## Updating (e.g. to remove the Dev options later)

Push a new game version → download the new APK → tap it → Android updates the app
**in place**. Because every build uses the same committed keystore, updates install
cleanly **and keep your save data** (Alloy, campaign, medals). Only an *uninstall*
wipes progress.

## Building locally instead (optional)

Requires Android Studio (bundles JDK 17 + SDK + Gradle):

```
cd app
npm install
cp ../fallengrid-v<latest>.html www/index.html
npx cap add android
npx cap sync android
cp keystore/debug.keystore ~/.android/debug.keystore   # stable key = clean updates
cd android && ./gradlew assembleDebug
# -> android/app/build/outputs/apk/debug/app-debug.apk
```

## Notes

- App id: `dk.lundjacobsen.fallengrid` · name: **Fallen Grid**.
- Permissions: only `VIBRATE` (haptics). Fully offline, no network.
- The `keystore/debug.keystore` here is a throwaway **debug** key (password
  `android`) — safe to commit; it is NOT a Play upload key. Its only job is to be
  *stable* so updates install over each other.
- Before any real public release, work through `docs/ANALYSIS-prerelease.md`
  (strip Dev options, `DEV_BUILD=false`, privacy policy, etc.).
