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
| 2 Colaborare | Fir public separat de AI, note interne invizibile userilor, mesaje idempotente, atribuiri concurente protejate, rezolvare cu mesaj și redeschidere cu motiv; API/UI și teste de izolare | Implementată pe `feat/ticket-collaboration`, bază PR #1; verificări locale și reale trecute, CI nou în așteptare |
| 3 Spațiu support | Filtre combinate, impact declarat de user, prioritate auditată, dashboard cu formule/interval/excluderi, notificări persistente fără duplicate sau scurgeri din note | Neîncepută |
| 4 Feedback ML | Revizuire explicită invalidabilă, export minimal support-only, evaluare reproductibilă cu proveniență și metrici RO/EN separate; fără reantrenare sau înlocuirea modelului | Neîncepută |
| 5 Integrare și documentație | E2E desktop/mobil pentru flux complet, migrare de la zero și upgrade, restart/Nginx, RO/EN real în mediu izolat, instrucțiuni backup/restore/demo și CI final | Neîncepută |

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

1. Etapa 3: filtre atribuite mie/neatribuite și prioritate, impact opțional declarat de user, editare/audit prioritate, dashboard cu formule și interval, notificări persistente cu polling și linkuri. Aceste funcții nu au încă endpointuri sau UI.
2. Etapa 4: revizuire ML explicită invalidabilă, export support-only minimal, evaluare reproductibilă v1/v2/baseline cu metrici separate și raportarea regresiei pe validarea originală. Nu s-au reantrenat sau înlocuit modele.
3. Etapa 5: verificare integrată a funcțiilor viitoare, demo final complet, audit mai larg de accesibilitate/contrast și documentație finală actualizată.

Următoarea bază tehnică este `feat/ticket-collaboration`; PR-ul ei depinde de PR #1. Nu s-a făcut merge în branchul implicit. Baza personală și containerele aplicației existente nu au fost actualizate; înainte de pornirea noii versiuni este necesar backup verificat și migrarea 005.
