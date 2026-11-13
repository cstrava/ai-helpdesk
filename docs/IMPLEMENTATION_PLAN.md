# Plan AI Helpdesk

Păstrăm datele, modelele și identitatea vizuală. Fără commit sau push.

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

CI este configurat, dar nu s-a făcut push și nu există o execuție GitHub Actions remote. Testele automate nu validează calitatea generală a modelelor. Rezultatele reale RO/EN și verificările finale sunt completate mai jos după rulare.

## Rezultate finale și limitări observate

- Backend: 31 teste trecute, inclusiv upgrade real al schemei 001–003 cu păstrarea datelor și owner null, invalidarea sesiunilor, CSRF, roluri, IDOR, audit, concurență, filtre și ciornă bazată doar pe mesaje user.
- Frontend: 7 teste trecute, lint și build de producție reușite. Testul Playwright extins include user → tichet → logout → support → corectare/status → audit și focus Tab/Shift+Tab/Escape. Remediat păstrarea selecției între conturi și viewportul mobil lărgit de tabel; tabelul păstrează derularea locală prin containment CSS.
- Modele reale: conversație/ciornă/confirmare RO și EN, schimbare EN→RO, corectură headset→microfon, clasificare v2, retry 409 și logout 200 verificate prin API pe date de test. Nu constituie evaluare generală ML.
- Qwen a repetat întrebări și a generalizat unele detalii. Inițial a copiat fapte din întrebările asistentului; generatorul primește acum doar mesajele user, iar testul de regresie confirmă filtrarea. Repetarea testului real nu a mai introdus afirmația neconfirmată despre conectarea dispozitivului; unele generalizări și întrebări repetitive rămân limitări reale. Ciorna editabilă și confirmarea umană sunt esențiale.
- API restart: /health 200, sesiunea și conversația de test persistente; migrările au putut rula din nou fără recrearea datelor.
- În runda inițială nu am aplicat migrările pe volumul PostgreSQL al aplicației; testele au folosit ai_helpdesk_test într-un container separat. Pornirea efectivă, autorizată ulterior, este consemnată mai jos.
- Nu există execuție Actions remote (fără commit/push); nu au fost verificate Safari/Firefox sau un telefon fizic. Verificarea mobilă folosește Chromium cu emulare Pixel 7.

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
