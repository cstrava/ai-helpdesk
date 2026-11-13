# API și reguli de acces

Documentația OpenAPI este disponibilă la `http://127.0.0.1:8000/docs`. Frontendul folosește prefixul `/api` prin Nginx; API-ul direct nu are acest prefix.

## Autentificare

`POST /auth/register` creează doar user. `POST /auth/login` setează cookie HttpOnly și returnează identitatea și CSRF. `GET /auth/me` recuperează sesiunea. `POST /auth/logout` o invalidează. Operațiile de scriere autentificate cer `X-CSRF-Token`; originea trebuie să corespundă configurației. Înregistrarea/loginul sunt limitate la 30 de cereri în 10 minute per peer direct și operație.

## Conversații și confirmare

| Endpoint | Acces / rezultat |
|---|---|
| `POST /conversations` | user/support; creează conversație proprie |
| `GET /conversations?limit=21&offset=0` | numai conversații proprii, ordine descrescătoare după created_at și id |
| `GET /conversations/{id}` | numai proprietar; include tichetul asociat sau `ticket: null` |
| `GET /conversations/{id}/messages` | numai proprietar; ordine după id |
| `POST /conversations/{id}/messages` | numai proprietar; `content` 1–1000 caractere după trim; 409 dacă este convertită sau ocupată |
| `POST /conversations/{id}/ticket-draft` | numai proprietar; propunere validată, fără salvare ca tichet |
| `POST /conversations/{id}/tickets` | numai proprietar; confirmare explicită, 201 la creare, 409 dacă este duplicată, ocupată sau depășită |
| `POST /tickets` | 410; vechea creare directă este închisă |

Confirmarea cere `title` (1–160 caractere), `description` (1–2000), `last_message_id` întreg pozitiv și `confirmed: true` boolean strict. Textul este reclasificat. Ciorna trebuie să corespundă ultimului mesaj. Blocarea tranzacțională și unicitatea conversation_id protejează confirmările concurente.

După un răspuns pierdut clientul citește `GET /conversations/{id}`. Numai prezența unui tichet valid confirmă succesul. Un `ticket: null` nu garantează că prima cerere nu mai rulează; un eventual retry rămâne protejat de backend. Ciornă depășită: regenerare și reconfirmare, fără retry automat al textului vechi.

## Tichete

| Endpoint | Acces / rezultat |
|---|---|
| `GET /tickets` | user: proprii; support: toate, inclusiv cele istorice fără owner |
| `GET /tickets/{id}` | aceleași reguli de vizibilitate |
| `PATCH /tickets/{id}` | numai support; `final_category`, `status` și/sau `priority`; statusul și prioritatea cer `expected_version` când se schimbă |
| `GET /tickets/{id}/events` | cei care pot vedea tichetul; actor, dată, câmp, valori vechi/noi |
| `POST /predict` | autentificat și CSRF; clasificare v2 |
| `GET /health` | public; verifică disponibilitatea DB, fără inferență |

Filtre: `search` (maximum 200 caractere; căutare literală case-insensitive în titlu/descriere/UUID), `status`, `category`, `priority`, `assigned_to_me=true` și `unassigned=true` (ultimele două numai support și mutual exclusive), `limit` 1–100, `offset` ≥0. Ordine: created_at DESC, id DESC. Auditul este tranzacțional; salvările identice nu produc evenimente.

Accesul la resursele altui user returnează 404. Support nu primește automat acces la conversațiile AI ale altora. Stările sunt open, in_progress și resolved; regulile de tranziție, rezolvare și redeschidere sunt descrise mai jos.

Testele browser/backend simulează inferența; serverul de producție nu oferă un mod mock.

## Colaborare pe tichet — etapa 2

Migrarea 005 adaugă firul separat de AI, responsabilul, versiunea pentru concurență, prioritatea implicită normal și datele fluxului. `updated_at` reprezintă actualizarea metadatelor/statusului; notele interne nu îl modifică. Datele istorice fără dovezi rămân necunoscute. `first_resolved_at` se completează numai dintr-un eveniment de rezolvare existent sau la prima rezolvare nouă și nu este rescris la redeschidere.

| Endpoint | Reguli |
|---|---|
| `GET /support/agents` | support-only; lista conturilor support valide |
| `GET /tickets/{id}/messages?limit=50&after_id={uuid}` | proprietar/support; ordine created_at ASC, id ASC; cursor UUID vizibil în același tichet |
| `POST /tickets/{id}/messages` | proprietar/support; content 1–4000 după trim, request_id UUID; visibility public implicit sau internal exclusiv support |
| `POST /tickets/{id}/claim` | support; expected_version; numai tichet neatribuit |
| `PUT /tickets/{id}/assignment` | support; expected_version și assignee_id support valid sau null pentru dezatribuire |
| `POST /tickets/{id}/reopen` | proprietar/support; reason 1–4000, expected_version și request_id UUID; numai resolved → open |

`PATCH /tickets/{id}` rămâne support-only pentru categorie/status. Schimbarea statusului cere expected_version. Rezolvarea cere și resolution_message (1–4000) și request_id UUID; mesajul devine public. Versiunea este returnată de listă/detaliu/creare și crește la schimbarea metadatelor/statusului/atribuirii. O versiune depășită produce 409 fără salvare parțială. Corectarea categoriei poate include expected_version; frontendul îl trimite întotdeauna.

Tranziții permise: open → in_progress sau resolved; in_progress → open sau resolved, numai support. resolved → open cere operația de redeschidere și motiv. O salvare fără schimbare nu adaugă audit. Răspunsurile obișnuite, inclusiv pe tichete resolved, nu schimbă statusul. Conversația AI convertită rămâne închisă chiar după redeschiderea tichetului.

Idempotency: cheia request_id este unică per tichet și autor. Retry cu același conținut/vizibilitate/tip returnează același mesaj; reutilizarea pentru alt conținut produce 409. Mesajele de redeschidere se deduplică la fel. O confirmare de rezolvare repetată cu versiunea veche poate returna 409: reîncarcă tichetul, fără duplicarea mesajului. Două preluări sau tranziții concurente cu aceeași versiune au un singur câștigător.

Notele interne sunt filtrate în SQL înaintea paginării pentru user; un cursor către o notă internă returnează 404. Nu sunt introduse în audit și nu schimbă versiunea/datele publice ale tichetului. UUID-urile evită expunerea unui contor secvențial. Nu există contoare publice de note.

## Spațiul support — etapa 3

`POST /conversations/{id}/tickets` acceptă câmpul opțional `impact`: `individual`, `team` sau `organization`. Acesta este declarat de utilizator, nu generat de model. `GET /tickets` returnează impactul; utilizatorul nu poate schimba prioritatea.

Prioritatea este `low`, `normal`, `high` sau `urgent`; pentru datele vechi migrarea păstrează default `normal`. Modificarea este support-only, cere `expected_version` dacă valoarea chiar se schimbă și este înregistrată în `ticket_events`.

| Endpoint | Reguli |
|---|---|
| `GET /support/dashboard?days=30` | support-only; zile între 1 și 365 |
| `GET /notifications?limit=20&offset=0` | notificări proprii, paginație după created_at/id; numai tichetele accesibile |
| `GET /notifications/unread-count` | număr necitit pentru destinatar |
| `PATCH /notifications/{id}/read` | marchează notificarea destinatarului ca citită; 404 dacă nu este accesibilă |

Notificările sunt persistente și deduplicate în tranzacția acțiunii-sursă. Răspunsurile publice notifică cealaltă parte (proprietarul și agentul atribuit); dacă tichetul este neatribuit, răspunsul proprietarului notifică echipa support. Notele interne nu notifică. Atribuirea și schimbarea statusului notifică proprietarul și agentul relevant, exceptând actorul. Polling-ul UI este la 30 secunde; nu se trimit emailuri.

Dashboardul folosește o fereastră mobilă `[acum - days, acum]`, filtrată după `tickets.created_at`. Numerele pe status, categorie și prioritate și totalul neatribuit descriu tichetele create în interval. Primul răspuns este cel mai timpuriu mesaj public (`reply` sau `resolution`) al unui autor support, minus `tickets.created_at`; notele interne și mesajele user/AI sunt excluse. Prima rezolvare folosește `first_resolved_at - created_at`, câmp stabilit la prima tranziție în resolved. Mediile includ doar tichetele cu eveniment cunoscut; numărul fără eveniment este raportat separat. Datele istorice necunoscute rămân necunoscute. Valorile sunt descriptive, nu SLA-uri contractuale.
