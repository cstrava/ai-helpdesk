# Demonstrație (modele reale)

## Pregătire

Pornește aplicația conform README. Creează două conturi user din interfață și un support prin CLI. Folosește ferestre/browser profile separate pentru user și support.

## Română

1. Autentifică-te ca user. Scrie: „Nu mă pot conecta la aplicația de pontaj de azi dimineață.”
2. Răspunde clarificării cu eroarea reală: „Apare «cont blocat». Colegii se pot conecta. Nu pot înregistra orele.”
3. Testează o corectură: „Corectez: problema a început ieri, nu azi.”
4. Pregătește ciorna. Verifică să păstreze corectura și să nu inventeze detalii. Editează titlul.
5. Confirmă o singură dată. Notează ID-ul, categoria și statusul open.
6. Reîncarcă pagina: conversația și legătura spre tichet trebuie recuperate; nu se mai acceptă mesaje în conversația convertită.
7. Ca support, caută ID-ul tichetului, preia-l, corectează categoria dacă este cazul și treci în in_progress. Adaugă un răspuns public și o notă internă. Marchează resolved cu mesaj de rezolvare și verifică istoricul.
8. Ca user, verifică starea și istoricul; nu trebuie să existe controale de editare. Al doilea user nu vede datele primului.

## English and language switching

1. Start a new conversation: “My USB headset is not detected on my laptop.”
2. Provide real details when asked: “It stopped working after reconnecting it this morning. I cannot join calls. Another USB port did not help.”
3. Switch language: „Te rog să continuăm în română. Corectez: este un microfon USB, nu căști.”
4. Prepare the draft. Check the latest language and correction, edit if needed, then confirm.

## Verificare manuală a erorilor

Într-un mediu de demonstrație, întrerupe temporar serviciul Ollama și trimite un mesaj: trebuie să rămână în editor, cu eroare clară. Repornește serviciul și retrimite. Nu elimina volume. Pentru timeout și răspunsuri invalide există și teste automate simulate.

## Interfață

Verifică desktop și telefon, Tab/Shift+Tab în dialoguri, Escape, focus vizibil, liste goale, încărcare, erori și logout. Testele automate de browser sunt separate de această verificare cu modele reale.

## Demonstrația completă — 5–10 minute

Acest scenariu demonstrează etapele 1–4. Pentru review/export, folosește exclusiv date sintetice; nu transforma baza personală în fixture și nu distribui CSV-ul.

1. **Minutele 0–2:** autentifică-te, scrie un mesaj fără să-l trimiți, apoi refresh. Mesajul trebuie recuperat în aceeași filă. Trimite-l și verifică răspunsul.
2. **Minutele 2–4:** pregătește ciorna, modifică titlul și descrierea, apoi refresh. Modificările trebuie recuperate fără creare de tichet.
3. **Minutele 4–5:** confirmă și refresh. Verifică același ID și conversația închisă. Nu trebuie să reapară ciorna.
4. **Minutele 5–7:** ca support, caută ID-ul, preia tichetul, adaugă răspuns public și notă internă, modifică categoria și rezolvă cu mesaj. Ca proprietar, verifică răspunsul/rezolvarea și absența notei; redeschide cu motiv. Ca al doilea user verifică izolarea. Creează conturile explicit conform README; pornirea nu le creează automat.
5. **Minutele 7–8:** ca support, filtrează „Atribuite mie” și după prioritate, schimbă prioritatea și verifică auditul. Consultă dashboardul de 30 de zile și notificarea primită de proprietar după răspunsul public; verifică faptul că nota internă nu a generat notificare. Revizuiește explicit categoria unui exemplu sintetic și exportă-l; editarea categoriei după aceea trebuie să invalideze exemplul. Nu exporta text real în materialele demo.
6. **Minutele 8–9:** repetă o conversație scurtă în engleză, verificând manual fidelitatea ciornei. Erorile Qwen sunt posibile și trebuie corectate înainte de confirmare.
7. **Minutul 9–10:** logout, login și verifică absența conținutului nesalvat. Istoricul salvat în DB rămâne accesibil.

Pierderea răspunsului după salvare este simulată reproductibil în Playwright: cererea ajunge la backend, acesta creează tichetul, iar browserul primește 502. Interfața trebuie să recupereze tichetul prin GET fără al doilea POST. Rularea este pe DB separată, cu ML/LLM simulate:

```bash
cd frontend
E2E_PYTHON=../.venv/bin/python POSTGRES_PORT=55434 npm run test:e2e
```

Nu simula erori prin oprirea bazei personale. Testele automate cu modele simulate nu înlocuiesc verificarea manuală RO/EN cu modelele reale.
