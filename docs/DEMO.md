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
7. Ca support, caută ID-ul tichetului, corectează categoria dacă este cazul, treci în in_progress, apoi resolved. Verifică istoricul.
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
