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
| `PATCH /tickets/{id}` | numai support; `final_category` și/sau `status`; fără câmpuri null sau necunoscute |
| `GET /tickets/{id}/events` | cei care pot vedea tichetul; actor, dată, câmp, valori vechi/noi |
| `POST /predict` | autentificat și CSRF; clasificare v2 |
| `GET /health` | public; verifică disponibilitatea DB, fără inferență |

Filtre: `search` (maximum 200 caractere; căutare literală case-insensitive în titlu/descriere/UUID), `status`, `category`, `limit` 1–100, `offset` ≥0. Ordine: created_at DESC, id DESC. Auditul este tranzacțional; salvările identice nu produc evenimente.

Accesul la resursele altui user returnează 404. Support nu primește automat acces la conversațiile AI ale altora. Stările curente sunt open, in_progress și resolved; cerința unui mesaj de rezolvare și redeschiderea cu motiv aparțin etapei 2, încă neimplementată.

## Limitele livrării curente

Nu există încă endpointuri pentru răspunsuri pe tichet, note interne, atribuiri, priorități, notificări, dashboard sau export ML. Nu presupune existența lor din plan. Testele browser/backend simulează inferența; serverul de producție nu oferă un mod mock.
