# Evaluarea modelelor de clasificare

## Reproducere

Artefactele modelelor și dataseturile sunt locale și nu se comit. Instalează într-un mediu dedicat dependențele CPU și ML:

```bash
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.11.0+cpu
python -m pip install -r ml/requirements.evaluation.txt
python ml/src/reproduce_evaluation.py
```

Scriptul este numai pentru inferență. Verifică hash-urile train/validation și că `scenario_id` nu se suprapune între perechile bilingve de train/holdout. Perechile RO/EN ale aceluiași scenariu rămân în același grup. Raportul `ml/reports/reproducible_v1_v2_baseline.json` conține configurația de grupare, seedul splitului grouped (42), identificatorii și hash-urile artefactelor/datei, versiunile bibliotecilor, accuracy, macro-F1, rezultate pe clasă și matrice de confuzie. Nu conține texte, nu reantrenează modelul activ și nu modifică fișierele de date.

## Ce se compară

- **Baseline:** TF-IDF + Linear SVM, antrenat numai pe corpusul inițial în engleză.
- **v1:** XLM-RoBERTa anterior, evaluat pe validarea engleză și pilotul bilingv.
- **v2:** experimentul bilingv local, evaluat pe validarea engleză existentă și pilotul bilingv dedicat.
- **Grouped English validation:** același split englezesc grouped, cu seed 42. Acest split a fost inclus în arhiva folosită pentru selecția modelului v2; rezultatele sunt o comparație de validare, nu un holdout independent.
- **Pilot bilingv:** holdout separat cu 16 scenarii RO/EN pereche. Se compară fiecare limbă separat. Aceste scenarii sintetice sunt puține și nu estimează performanța pe incidente reale.

Scriptul nu rulează v2 pe `grouped/test.csv`; acel split rămâne neatins în această evaluare. Nu amesteca metricile pilotului cu cele ale corpusului grouped și nu trata traducerile unui scenariu drept observații independente.

Codul/configurația completă de antrenare v2 nu este versionată. Ponderile și config-ul local pot fi hash-uite, iar inferența/metricile pot fi repetate, însă antrenarea v2 nu poate fi reprodusă din repository. Seedul 42 din acest raport aparține splitului grouped, nu este prezentat drept seedul antrenării v2.

## Rezultate

Rulare locală cu artefactele disponibile (CPU, inference-only):

| Set și limbă | Model | Accuracy | Macro-F1 |
|---|---|---:|---:|
| Validare grouped EN (n=4784) | Baseline SVM | 0.8612 | 0.8560 |
| Validare grouped EN (n=4784) | XLM-R v1 | 0.8798 | 0.8782 |
| Validare grouped EN (n=4784) | XLM-R v2 | 0.8142 | 0.8024 |
| Pilot RO (16 scenarii) | Baseline SVM | 0.1250 | 0.0333 |
| Pilot RO (16 scenarii) | XLM-R v1 | 0.1875 | 0.0982 |
| Pilot RO (16 scenarii) | XLM-R v2 | 0.5625 | 0.5292 |
| Pilot EN (aceleași 16 scenarii) | Baseline SVM | 0.3125 | 0.2579 |
| Pilot EN (aceleași 16 scenarii) | XLM-R v1 | 0.2500 | 0.2121 |
| Pilot EN (aceleași 16 scenarii) | XLM-R v2 | 0.6250 | 0.5750 |

În pilot, v2 a crescut accuracy cu 37.5 puncte procentuale față de v1 în fiecare limbă; sunt doar 16 perechi de scenarii sintetice, nu exemple independente per traducere. Pe validarea grouped originală în engleză, v2 a scăzut față de v1 cu 6.56 puncte procentuale accuracy și 7.58 puncte macro-F1. Scorul v2 de validare nu este independent, fiindcă validarea grouped a fost inclusă în arhiva de date pregătită pentru experimentul v2. Această regresie este motiv să păstrăm v2 ca experiment, nu ca înlocuitor necondiționat pentru v1.

Matricele de confuzie și metricile pe clasă, hash-urile și versiunile de biblioteci sunt în `ml/reports/reproducible_v1_v2_baseline.json`. Separat, raportul istoric `ml/reports/grouped/test_comparison.json` compară baseline-ul SVM cu XLM-R v1 pe grouped test; nu este scorul v2. `ml/reports/ro_evaluation_v1.json` este un alt set românesc mic pentru v1 și nu este comparabil cu validarea grouped.

Orice metrică trebuie citită împreună cu splitul, hash-ul datelor, versiunea modelului și limitările acestei evaluări. Nu schimba holdout-ul pentru a îmbunătăți scoruri și nu folosi scorurile ca argument că modelul poate atribui urgența sau rezolva tichetul fără om.
