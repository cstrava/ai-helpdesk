# Plan AI Helpdesk

Păstrăm datele, modelele și identitatea vizuală. Commiturile și push-urile pe branchuri de lucru sunt autorizate; fără merge în branchul implicit.

Tabel istoric al livrării din 9 noiembrie; nu reprezintă finalizarea noilor etape de portofoliu.

| Etapă | Acceptare | Progres |
|---|---|---|
| 1 Audit | Inventar API/schemă/teste și verificări inițiale | Finalizat: 5 teste frontend și lint trecute; backend inițial blocat de conexiunea 5433 |
| 2 Autentificare | Hash parole, sesiuni revocabile HttpOnly, CSRF, roluri și izolare pe ID | Implementat și testat cu PostgreSQL izolat |
| 3 Conversații | Istoric propriu, redeschidere după refresh, legătură tichet | Implementat; restaurare verificată în Chromium desktop/mobil |
| 4 Tichete | Confirmare, deduplicare, filtre server, audit, controale support | Implementat; inclusiv test concurent, audit și izolare |
| 5 Calitate | Bilingv, corecturi, erori clare, text păstrat | Implementat și verificat RO/EN cu modele reale; timeout/invalid/offline/rollback testate. Limitele calitative sunt documentate |
| 6 Docker/migrări | Runner versionat compatibil cu datele existente, Compose complet, 5434 | Finalizat: imagini construite, config validă, modele reale și persistență sesiune/conversație după restart API verificate în DB izolată |
| 7 Teste/CI | Izolare, roluri, flux complet simulat fără GPU, frontend, Actions | Finalizat local: 31 backend, 7 frontend și 2 fluxuri browser desktop/mobil cu roluri și audit trecute. Actions configurat; neexecutat remote |
| 8 Documentație | Instalare, demo RO/EN, limite ML, verificări finale | Finalizat: README/DEMO, capturi și tastatură verificate, rezultate și limitări consemnate |

## Livrare portofoliu — 2026-11-13

Bază verificată: branch implicit `feature/data-pipeline`, commit `8474796`, working tree curat. CI istoric pe această bază: 31 backend, 7 frontend, 2 browser, build și lint reușite. Aceste rezultate nu validează schimbările noi.

| Etapă | Criterii verificabile | Stare |
|---|---|---|
| 1 Stabilitate | Instalare curată, typecheck inclusiv Node, lint/test/build; recuperare confirmare după răspuns pierdut fără duplicate; sessionStorage per cont/conversație cu ștergere la logout; respingere explicită a schemelor legacy parțiale și păstrarea datelor | Implementată pe `fix/application-reliability`; verificări locale trecute; [CI push reușit](https://github.com/cstrava/ai-helpdesk/actions/runs/43454447275), [PR #1](https://github.com/cstrava/ai-helpdesk/pull/1) |
| 2 Colaborare | Fir public separat de AI, note interne invizibile userilor, mesaje idempotente, atribuiri concurente protejate, rezolvare cu mesaj și redeschidere cu motiv; API/UI și teste de izolare | Implementată pe `feat/ticket-collaboration`, bază PR #1; verificări locale și reale trecute; [CI reușit](https://github.com/cstrava/ai-helpdesk/actions/runs/43462307139) și al doilea push [reușit](https://github.com/cstrava/ai-helpdesk/actions/runs/43462355989) |
| 3 Spațiu support | Filtre combinate, impact declarat de user, prioritate auditată, dashboard cu formule/interval/excluderi, notificări persistente fără duplicate sau scurgeri din note | Implementată pe `feat/support-workspace`; 56 backend, 23 frontend și 4 Playwright desktop/mobil trecute, lint/typecheck/build trecute; [CI reușit](https://github.com/cstrava/ai-helpdesk/actions/runs/43466142551) și al doilea push [reușit](https://github.com/cstrava/ai-helpdesk/actions/runs/43466211044) |
| 4 Feedback ML | Revizuire explicită invalidabilă, export minimal support-only, evaluare reproductibilă cu proveniență și metrici RO/EN separate; fără reantrenare sau înlocuirea modelului | Implementată pe `feat/ml-feedback-evaluation`; 57 backend, 24 frontend și 4 Playwright trecute; lint/typecheck/build și build Docker trecute. [CI reușit](https://github.com/cstrava/ai-helpdesk/actions/runs/43474446987) și al doilea push [reușit](https://github.com/cstrava/ai-helpdesk/actions/runs/43474500679) |
| 5 Integrare și documentație | E2E desktop/mobil pentru flux complet, migrare de la zero și upgrade, restart/Nginx, RO/EN real în mediu izolat, instrucțiuni backup/restore/demo și CI final | Verificări locale consemnate mai jos; PR/CI pentru acest branch urmează |

Reguli: baza personală nu este fixture; testele folosesc PostgreSQL separat. Nu publicăm date, exporturi, secrete sau modele. PR-uri tematice, eventual în lanț, fără force-push sau merge. Etapele neterminate rămân marcate explicit.

## Istoric anterior

## Decizii

- Datele vechi fără proprietar rămân neatribuite și inaccesibile utilizatorilor obișnuiți. Suportul poate administra tichetele istorice. Conversațiile neatribuite nu sunt expuse. Nu atribuim automat unui cont date istorice.
- POST /tickets răspunde 410: crearea trece obligatoriu prin conversație/ciornă/confirmare. Retry după succes este respins 409, fără duplicat; UI oferă recuperarea rezultatului din istoric/listă.
- Sesiuni opace în DB, 8 ore, cookie HttpOnly, SameSite=Lax, Secure configurabil pentru HTTPS. CSRF per sesiune și verificarea originii; scrypt N=131072,r=8,p=1.
- Testele folosesc exclusiv ai_helpdesk_test și scheme temporare. Serverul browser simulează doar inferența; autentificarea, SQL și HTTP sunt reale. În producție nu există flag de simulare.
- API Docker păstrează inferența XLM-R pe CPU și rezervarea NVIDIA pentru Ollama. Ponderile nu au fost modificate.
- Actualizare țintită Vitest 4 și typescript-eslint; override minimatch 11 pentru dependența de lint. Ultima instalare npm: zero vulnerabilități. Fără upgrade forțat.

## Jurnal

- Audit: README și .gitignore conțineau shell literal; remediate. Migrări originale 001–003 existente, fără runner. Frontend Compose era opțional; acum inclus implicit.
- După conturi/istoric/tichete: 15 teste backend existente adaptate trecute; 5 frontend trecute; build și lint trecute.
- După teste securitate/concurență/migrări/erori: 27 backend trecute; 7 frontend trecute; Chromium desktop și Pixel 7, câte un flux complet cu server/DB reale și modele simulate, trecute.
- Capturi inspectate: ajustat filtrele pe mobil; păstrat aspectul existent. Logout accesibil și pe mobil.
- Docker: ambele imagini construite cu succes; API /health, login, predicție XLM-R v2 reală și logout verificate în mediu izolat. Niciun volum existent nu a fost șters sau migrat de teste.
- Prima rulare pytest a inclus accidental datele conexiunii în traceback; nu au fost copiate în fișiere. Raportarea inițializării DB a fost corectată să ascundă detaliile conexiunii.

## Limite ale verificării

La 9 noiembrie, CI era configurat, dar nu exista o execuție remote. La 13 noiembrie, baza `8474796` are [CI reușit](https://github.com/cstrava/ai-helpdesk/actions/runs/43449306371). Testele automate nu validează calitatea generală a modelelor. Rezultatele reale RO/EN și verificările finale sunt completate mai jos după rulare.

## Rezultate finale și limitări observate

- Backend: 31 teste trecute, inclusiv upgrade real al schemei 001–003 cu păstrarea datelor și owner null, invalidarea sesiunilor, CSRF, roluri, IDOR, audit, concurență, filtre și ciornă bazată doar pe mesaje user.
- Frontend: 7 teste trecute, lint și build de producție reușite. Testul Playwright extins include user → tichet → logout → support → corectare/status → audit și focus Tab/Shift+Tab/Escape. Remediat păstrarea selecției între conturi și viewportul mobil lărgit de tabel; tabelul păstrează derularea locală prin containment CSS.
- Modele reale: conversație/ciornă/confirmare RO și EN, schimbare EN→RO, corectură headset→microfon, clasificare v2, retry 409 și logout 200 verificate prin API pe date de test. Nu constituie evaluare generală ML.
- Qwen a repetat întrebări și a generalizat unele detalii. Inițial a copiat fapte din întrebările asistentului; generatorul primește acum doar mesajele user, iar testul de regresie confirmă filtrarea. Repetarea testului real nu a mai introdus afirmația neconfirmată despre conectarea dispozitivului; unele generalizări și întrebări repetitive rămân limitări reale. Ciorna editabilă și confirmarea umană sunt esențiale.
- API restart: /health 200, sesiunea și conversația de test persistente; migrările au putut rula din nou fără recrearea datelor.
- În runda inițială nu am aplicat migrările pe volumul PostgreSQL al aplicației; testele au folosit ai_helpdesk_test într-un container separat. Pornirea efectivă, autorizată ulterior, este consemnată mai jos.
- La acea dată nu exista execuție Actions remote (fără commit/push); nu au fost verificate Safari/Firefox sau un telefon fizic. Verificarea mobilă folosește Chromium cu emulare Pixel 7.

## Închidere — 2026-11-09

- Ultima verificare: 31/31 backend, 7/7 frontend, 2/2 Playwright (desktop și mobil, inclusiv support/audit). Lint, build Vite, build imagini API/frontend, validare Compose, parse YAML CI și git diff --check trecute.
- npm audit complet și pentru producție: zero vulnerabilități la data verificării.
- Imaginea Nginx servește pagina și transmite /api/health către API: verificat, răspuns ok. Importul API fără torch/transformers a fost verificat separat, pentru compatibilitatea CI fără modele.
- Capturile finale desktop/mobil au fost inspectate. Testele de tastatură verifică Tab, Shift+Tab și Escape în dialog. Nu s-a realizat un audit complet de accesibilitate.
- Containerele temporare sunt oprite la final; Ollama este readus la starea inițială oprită. Containerele/volumele nu se șterg. Baza aplicației și ponderile existente sunt păstrate.
- Nu s-a făcut commit sau push. Fișierele ML neversionate preexistente au rămas neatinse.

## Pornire pentru testare în browser — 2026-11-09

- Confirmat că `docker compose up -d --build` rulează migrările înainte de Uvicorn. Portul 5173 era liber; nu a fost oprit niciun proces Vite.
- Înainte de migrare: backup custom PostgreSQL în `/home/analog/backups/ai-helpdesk/20261109T161806Z/ai_helpdesk.dump`, în afara repository-ului, cu permisiuni restrictive. SHA256SUMS, baseline.json și verification.json sunt în același director.
- Backup verificat prin restaurare integrală într-un container PostgreSQL 17 separat, fără rețea: schema, digestul conținutului fiecărui tabel, numărul rândurilor și secvențele identice cu originalul. Sursa a fost reverificată neschimbată înainte de migrare.
- Aplicat Compose complet; migrările 001–004 înregistrate. Compararea valorilor originale după migrare confirmă păstrarea celor 7 conversații, 32 mesaje și 3 tichete. Proprietarii istorici rămân NULL. Raport: migration-verification.json lângă backup.
- API, PostgreSQL, frontend și Ollama sunt healthy. Interfață: http://127.0.0.1:5173 ; HTTP 200 pentru pagină și /api/health, HTTP 401 pentru sesiune absentă. PostgreSQL publicat pe 127.0.0.1:5434.
- Nu au fost create conturi sau parole de demonstrație în baza aplicației. User se creează prin înregistrarea publică; support prin CLI interactiv, cu email separat.
- Containerul de verificare a backupului este oprit după verificare; aplicația rămâne pornită. Nu s-au șters volume sau resetat baze de date. Fără commit/push.

## Verificări etapa 1 — 2026-11-13

- Instalare curată `npm ci`: reușită; zero vulnerabilități raportate în acea instalare. Tipuri Node declarate explicit; typecheck acoperă aplicația și configurațiile Vite/Vitest/Playwright. Lint, 19 teste frontend și build trecute.
- 43 teste backend trecute pe PostgreSQL separat, port 55434: inclusiv confirmare concurentă/retry, upgrade legacy cu păstrarea datelor, migrare de la zero și 11 variante de schemă incompatibilă (coloane, tip, default, identity, nullability, check, FK, unicitate, index, tabel lipsă).
- 4 teste Playwright trecute: flux existent și recuperare după 502 produs după salvarea reală a tichetului, fiecare pe desktop și Pixel 7 emulat. ML/LLM simulate în aceste teste.
- Imagini API/frontend construite separat; integrare Nginx pe 5175 și API pe 8002, exclusiv pe baza ai_helpdesk_smoke din containerul de test. Fluxuri reale RO și EN: conversație, ciornă, clasificare v2 (Hardware/Access pentru cele două exemple), confirmare, GET de recuperare, retry 409 și logout trecute.
- După restartul exclusiv al API-ului de verificare, sesiunea, cele două conversații și legăturile la tichete au persistat; runnerul a rulat din nou fără recrearea datelor.
- Observație calitativă: Qwen a cerut aplicația de apeluri în RO și dispozitivul în EN deși problema/impactul erau deja descrise. Ciornele inspectate nu au introdus detalii noi evidente. Două exemple nu reprezintă evaluare generală ML. Modelul activ și ponderile nu au fost modificate; scorurile istorice v1/v2 rămân distincte.
- Nu am aplicat modificări sau teste pe baza personală și nu am actualizat containerele aplicației existente. Etapele 2–5 rămân neterminate.

## Verificări etapa 2 — 2026-11-13

- Migrarea 005 adaugă mesaje publice/note interne, atribuirea, prioritatea implicită normal și versiuni optimiste. Upgrade 004→005 verificat cu date sintetice: textul, versiunea modelului și owner null păstrate; data primei rezolvări preluată numai din audit datat, altfel null. Migrare repetabilă și pornire de la zero testate.
- 54 teste backend trecute pe PostgreSQL izolat: autorizare/IDOR, note interne absente din toate răspunsurile user testate, cursor privat refuzat, mesaje concurente deduplicate, preluări concurente fără suprascriere, conflict la status cu rollback, rezolvare/redeschidere concurente, păstrarea primei rezolvări și upgrade.
- 22 teste frontend trecute; typecheck, lint și build trecute. Teste noi pentru cheie de retry stabilă, text păstrat după eșec, note interne distincte, claim cu versiune și motiv obligatoriu de redeschidere.
- Playwright desktop/mobil: flux extins cu preluare support, răspuns, notă internă, mesaj de rezolvare și redeschidere de către proprietar; păstrează verificarea recuperării confirmării după 502. Inferența este simulată în browser.
- Imagini API/frontend separate construite. Prin Nginx temporar (5175), două fluxuri reale RO/EN au trecut pe baza ai_helpdesk_smoke: ciornă/clasificare/confirmare, preluare, reply deduplicat, notă invizibilă proprietarului, rezolvare și redeschidere. Restartul API-ului temporar a păstrat sesiunea și istoricul. Ciornele inspectate nu au introdus detalii noi evidente; Qwen continuă să ceară uneori clarificări neesențiale. Nu este evaluare ML generală.
- Captură mobilă inspectată; eliminat autofocusul categoriei care putea derula dialogul direct la formularul de jos. Stilul verde/crem păstrat, nota internă are marcaj textual și fundal distinct. Nu este un audit complet de accesibilitate.

## Continuarea livrării

Etapele 1–2 nu înseamnă finalizarea întregului proiect. Rămân:

1. Etapa 3: funcțiile sunt implementate, 56 backend/23 frontend și 4 Playwright trecute; ambele rulări Actions au trecut. E2E Playwright acoperă fluxul principal, nu Nginx pentru funcțiile noi.
2. Etapa 4: review/export și evaluarea reproductibilă implementate local. Evaluarea a raportat +37.5 pp accuracy v2 față de v1 pe pilotul bilingv sintetic (16 scenarii/limbă), dar -6.56 pp pe validarea grouped EN care nu este holdout independent; vezi `docs/ML_EVALUATION.md`. 57 backend/24 frontend/4 Playwright, lint/typecheck/build și build Docker au trecut. Mai rămân push-ul și CI.
3. Etapa 5: rămân verificarea integrării prin Nginx, migrare de la zero și upgrade, restart/persistență, fluxuri RO/EN cu modele reale în mediu izolat și verificarea finală a documentației/accesibilității.

### Verificări etapa 3 — 2026-11-13

- Migrarea 006 și toate migrările 001–006 au rulat în schema izolată a suitei; backend 56/56 trecut. Testele noi verifică impact opțional/user-declarat, prioritate doar support, filtre combinate și permisiuni, audit, dashboard descriptiv și notificări (fără notificare pentru notă internă, fără notificarea actorului și citire).
- Frontend: 23/23 teste, lint (inclusiv typecheck), typecheck explicit și build de producție trecute.
- Playwright: 4/4 în Chromium desktop și Pixel 7 emulat pentru fluxurile existente de confirmare/recuperare. Inference mock; nu este E2E pentru dashboard/notificări.
- Nu am testat încă integrarea cu Nginx pentru noua versiune și nu există încă rezultat Actions pentru branchul etapei 3. Baza și serviciile personale nu au fost folosite ca fixture.

### Verificări etapa 4 — 2026-11-13

- Backend: 57/57 teste pe PostgreSQL temporar separat; testul explicit de review/export a fost repetat independent. Acoperă autorizarea support-only, minimizarea câmpurilor, idempotency/conflict, CSV injection și invalidarea după editarea textului sau categoriei.
- Frontend: 24/24 teste, lint, typecheck și build de producție trecute. Playwright: 4/4 pe Chromium desktop și Pixel 7 emulat; include review explicit, export și invalidarea lui. Fluxurile Playwright folosesc backendul de browser cu inferență simulată.
- `python -m compileall -q backend/app backend/tests ml/src`, `git diff --check` și build-ul Docker API/frontend trecute.
- Evaluare CPU inference-only repetată pentru artefactele locale. Metricile și limitele, inclusiv lipsa configurației de antrenare v2 și validarea grouped neindependentă, sunt în `docs/ML_EVALUATION.md`. Modelele/dataseturile nu au fost publicate.
- Pull request [#4](https://github.com/cstrava/ai-helpdesk/pull/4), bază `feat/support-workspace`; ambele rulări Actions au trecut (linkurile din tabel). PR-ul nu a fost integrat în branchul implicit.

### Verificări integrate etapa 5 — 2026-11-13

- Am pornit un Compose temporar `ai-helpdesk-portfolio-verify`: PostgreSQL propriu într-un volum distinct, API pe `127.0.0.1:8004`, frontend/Nginx pe `127.0.0.1:5176`. Nu am pornit, repornit, migrat sau folosit baza/API/frontend ale aplicației personale. Testul a apelat Ollama local existent doar pentru inferență, prin rețeaua Docker comună.
- Nginx `/api/health`, autentificare, rutele conversation/draft/ticket/collaboration/review/export au trecut prin proxy către API. Model Qwen `qwen3:4b-instruct` și clasificatorul XLM-R v2 au rulat local (clasificarea API pe CPU).
- Flux real RO: conversație cu răspuns Qwen, ciornă și categorie XLM-R, confirmare, recuperare tichet, preluare support, răspuns public, notă internă invizibilă userului, rezolvare, redeschidere, review explicit și export CSV. Flux real EN: conversație, răspuns Qwen, ciornă/categorie, confirmare și recuperare.
- Migrarea de la zero a înregistrat 001–007 în PostgreSQL izolat. Testele backend de upgrade/adoptare legacy și migrare repetată au trecut în suita de 57 teste. După restartul API temporar, containerul a revenit healthy, Nginx `/api/health` a răspuns `ok`, iar datele sintetice au rămas în volum (3 tichete și 3 conversații).
- Fluxul browser desktop/mobil complet rămâne verificat în Playwright cu modele simulate (4/4); integrarea reală Nginx/RO/EN de mai sus a fost verificată prin client HTTP, nu prin browser real. Testul browser verifică și contrastul textului vizibil în detaliul tichetului (prag 4.5:1) și fluxul verifică Tab/Shift+Tab/Escape și focusul dialogului. Contrastul pentru texte secundare și indicatorii de focus au fost întunecați; este un audit automat țintit, nu o certificare completă de accesibilitate. Nu am verificat Safari/Firefox sau un telefon fizic.
- Imaginile API/frontend s-au construit; serviciile temporare au fost oprite fără eliminarea volumului. Baza personală și volumele acesteia nu au fost modificate. PR/CI pentru etapa 5 urmează.

Lanțul de PR-uri este #1 (`feature/data-pipeline`) → #2 → #3 → #4; PR #5 va avea baza `feat/ml-feedback-evaluation`. Niciun PR nu a fost integrat în branchul implicit. Baza și containerele personale nu au fost actualizate cu aceste schimbări. Înainte de a rula versiunea cumulată pe acea bază, urmează backupul și verificarea restaurării din `docs/OPERATIONS.md`, apoi aplică migrările lipsă prin procedura documentată.
