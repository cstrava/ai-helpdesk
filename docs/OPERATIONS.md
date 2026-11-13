# Operare locală, backup și restore

## Pornire și conturi

Urmează README pentru `.env` local, GPU NVIDIA, ponderile XLM-R și modelul Qwen. Nu suprascrie configurația existentă. Pornirea normală nu creează conturi sau date demo.

```bash
docker compose up -d --build
docker compose ps
docker compose exec api python -m backend.app.manage create-support --email support@example.com
```

Ultima comandă este explicită, interactivă și cere parola fără afișare. Creează două conturi user prin interfață, cu adrese distincte. Nu folosi conturi personale în teste sau în materiale publice. `docker compose stop` păstrează datele. Nu utiliza `down -v`.

## Înaintea unui upgrade

1. Oprește scrierile aplicației într-o fereastră de mentenanță.
2. Salvează backupul într-un director privat, în afara Git. Exemplu, din directorul proiectului:

```bash
mkdir -p "$HOME/backups/ai-helpdesk"
chmod 700 "$HOME/backups/ai-helpdesk"
(umask 077; docker compose exec -T db pg_dump -U helpdesk -d ai_helpdesk -Fc > "$HOME/backups/ai-helpdesk/before-upgrade.dump")
sha256sum "$HOME/backups/ai-helpdesk/before-upgrade.dump"
```

Folosește un nume nou la fiecare backup; exemplul nu trebuie să suprascrie o copie importantă. Backupul conține date private. Nu îl publica și nu îl include în Git. Păstrează separat configurația locală prin mecanismul tău sigur de backup, fără a o afișa în loguri.

3. Verifică restaurarea într-un PostgreSQL separat. Exemplu de container fără rețea și fără volumele aplicației:

```bash
docker run -d --name ai-helpdesk-restore-check --network none \
  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_DB=restore_check postgres:17
docker exec ai-helpdesk-restore-check pg_isready -U postgres -d restore_check
# Continuă numai după ce pg_isready confirmă disponibilitatea.
docker exec -i ai-helpdesk-restore-check pg_restore -U postgres -d restore_check \
  --no-owner --no-privileges --exit-on-error < "$HOME/backups/ai-helpdesk/before-upgrade.dump"
docker exec ai-helpdesk-restore-check psql -U postgres -d restore_check -c '\dt'
```

Compară schema, numărătorile, conținutul și secvențele cu sursa; restaurarea fără eroare nu demonstrează singură identitatea datelor. Oprește containerul de verificare după inspecție. Nu îndrepta comenzile de restore spre baza personală existentă. Recuperarea efectivă a aplicației trebuie făcută într-un volum nou, verificată și apoi comutată explicit; nu există restore automat la pornire.

4. Aplică upgrade-ul numai după backup verificat. Compose rulează migrările înaintea API-ului. Pentru executare explicită:

```bash
docker compose run --rm --no-deps api python -m backend.app.manage migrate
```

Migrările sunt tranzacționale și serializate. Etapa 1 întărește adoptarea migrărilor legacy 001–003. Etapa 2 adaugă `005_ticket_collaboration.sql`; trebuie aplicată înainte de pornirea noului cod. Păstrează datele existente, adaugă noile tabele/câmpuri și folosește numai auditul existent pentru datele istorice de rezolvare. O schemă parțială este respinsă fără înregistrări noi de migrare. Nu modifica SQL deja aplicat și nu șterge manual înregistrări din schema_migrations pentru a forța adoptarea.

## Teste separate de baza aplicației

Exemplu de instanță exclusiv pentru teste, fără volumele aplicației și cu trust numai pe loopback:

```bash
docker run -d --name ai-helpdesk-tests -p 127.0.0.1:55434:5432 \
  -e POSTGRES_USER=helpdesk -e POSTGRES_DB=ai_helpdesk_test \
  -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17
POSTGRES_PORT=55434 POSTGRES_PASSWORD=test-only .venv/bin/python -m pytest backend/tests -q --tb=short
cd frontend
npm ci
npm run typecheck
npm run lint
npm test
npm run build
E2E_PYTHON=../.venv/bin/python POSTGRES_PORT=55434 npm run test:e2e
```

Așteaptă disponibilitatea PostgreSQL înaintea testelor. Porturile browser sunt 8001/5174. Schemele temporare sunt eliminate de fixture; niciun test nu trebuie să folosească baza ai_helpdesk. Eticheta test-only este exclusiv pentru instanța izolată cu trust, nu o parolă implicită a aplicației.
