# Fallen Grid — kritisk pre-release analyse (skrevet ved V6.14)

> Gemt på brugerens anmodning: skal genbesøges når spillet skifter fra TEST til RELEASE.
> Flere menupunkter findes i dag **kun til test** — se tjeklisten nederst.

## Overordnet dom

Et usædvanligt indholdsrigt og teknisk ambitiøst projekt, langt forbi prototype-stadiet —
men med tre strukturelle problemer: sværhedsgraden er ikke løst i bunden, systemmængden
overstiger polerings-dybden, og fundamentet (én ~1 MB HTML-fil, én tester) er skrøbeligt
i forhold til ambitionen om Google Play.

## Positivt

- **Indholdsvolumen er reel.** 18 baner i 4 geometri-tiers, 5 tårne med branches + T4,
  10+ fjendetyper med taktiske traits (camo, skjold, energi-resistens, freeze-immun),
  hero, 20 bølger + endless, kampagne med medaljer, daily med modes, Challenge Lab,
  achievements, armory-meta. Mere indhold end mange betalte mobil-TD-spil.
- **Gode kernemekanik-beslutninger.** Send-tidligt som tempo-værktøj uden straf (V6.11) er
  elegant — omkostningen er fjende-tæthed, ikke kunstig HP. Salgs-/byggebekræftelser
  fjerner fejltryk. Obstacles→Excavate lukker en pæn cirkel (gene → sink → belønning).
  Overclock giver maksede tårne videre formål.
- **Arbejdsmetode over gennemsnittet.** Telemetri pr. bølge (scrap/spent/maxed/oc),
  deterministiske seeds, Playwright-regressionssuite efter hver iteration, balancering
  fra rigtige play-logs. Har konkret fanget fejl (FIFO-spawn-buggen: 271 "hostiles" var kø).
- **Teknisk selvstændighed.** Alt prozeduralt — lyd, sprites, 3D — ingen assets, ingen
  server, kører offline. Android-essentials (back, lifecycle, haptik, safe-area) på plads.

## Negativt

1. **Sværhedsproblemet er behandlet symptomatisk, ikke kausalt.** Fire iterationer i træk
   (taper V6.5, HP-accelerator V6.12, sinks V6.13, baner V6.14) angreb samme klage:
   "fjender dør på sekunder, scrap hober sig op." Hver patch hjalp målbart (5306→3082
   overskud), men grundmodellen — indkomst vokser med kills, udgifter er engangs —
   genskaber overskuddet. Så længe forsvar aldrig mister værdi og indkomst aldrig falder,
   løber en erfaren spiller altid fra kurven. V6.14-banerne er det første *strukturelle*
   svar; effekten skal bekræftes i næste play-log.
2. **Balancen hviler på én spiller og en headless-sim.** "Maxed diverse vinder" beviser at
   spillet *kan* vindes — ikke at kurven føles rigtig. Nul data om nye spilleres wave 1-10.
   Threat-systemet (+HP pr. Armory-niveau) gør det svært at ræsonnere om, hvad en frisk
   spiller møder. Største ubekendte før release.
3. **Systemer > dybde.** Daily, Lab, Custom-sliders, Threat, medaljer, achievements, hero,
   dev-overrides — hvert system ~80 % færdigt og de konkurrerer om opmærksomheden (menuen
   måtte allerede saneres én gang). Hårdt spørgsmål: ville spillet være bedre med
   Daily + Lab + Custom skåret og timerne lagt i fjende-variation pr. bane? Biomes er kun
   farvetoner; alle 18 baner spiller samme fjender i samme rækkefølge.
4. **Overclock risikerer degenereret optimal-spil.** Rent fladt "+10 % dmg"-køb uden
   modspil → slutspil kan kollapse til "få maksede tårne i bedste knæk + OC-spam" — præcis
   den klump obstacles/resistenser skulle modvirke. Sinket virker økonomisk, men belønner
   ikke variation.
5. **Teknisk gæld.** Én fil ~1,08 MB med three.js r147 (2022) inline; builds via
   python-strengudskiftning med tælle-asserts — ét flertydigt anker kan korrumpere filen
   stille. Verifikations-scripts ligger i sessions-scratchpad, IKKE i repoet — dør
   containeren, dør testsuiten. Save-data er kun localStorage (WebView kan rydde den);
   V6.14's bane-omrokering brød allerede medalje-indeks én gang → launch kræver
   migreringsstrategi.
6. **Udestående release-risici.** Ydelse kun testet i SwiftShader headless — postFX på
   billig Android-GPU uafprøvet (batteri/varme). Rewarded ads (Second Wind, +50 % scrap)
   vil *sænke* sværhedsgraden i et spil, hvis hovedproblem er, at det er for let.
   Canvas-UI = ingen skærmlæser; 360px-design har små hit-targets.

## Prioritering (anbefalet rækkefølge)

1. Play-test V6.14 på Hard/Brutal på de nye Tier C/D-baner — afgør om geometri-svaret virker.
2. Commit verify-scriptsene til repoet — billigste forsikring i projektet.
3. Én rigtig telefon-test (ydelse + varme) før mere indhold.
4. Overvej at skære/skjule 1-2 systemer frem for at tilføje nye.

## RELEASE-TJEKLISTE — test-ting der SKAL fjernes/ændres før Google Play

- [ ] `DEV_BUILD = false` (logging skal default være OFF i drift — krav fra V6.8).
- [ ] Fjern **Dev · Armory Override** (OFF/0/50/100 %) fra Settings + `setDevArmory`-eksport.
- [ ] Fjern **Dev · Fresh Start / Reset All**-knappen (tilføjet V6.19) fra Settings.
- [ ] Fjern **Dev · Map Unlock** ("unlock all maps (test)"-toggle, `devUnlock`-nøglen) fra Settings (tilføjet V6.15).
- [ ] Genovervej Play Log-sektionen i Settings (View/Export er et udviklerværktøj).
- [ ] Save-migrering: bane-indeks (medals/camp/map-nøgler) hvis rosteren er ændret siden testerens sidste version.
- [ ] Fjern/skjul `__GAME`-debug-eksporterne fra produktions-buildet hvis muligt.
