# Dataset Scoping Overview

Ez a projekt több, egymástól külön kezelt dokumentumdatasetet támogat úgy, hogy minden dataset kulcshoz saját vector collection és saját bemeneti mappa tartozik.

## Mire jó

- Elkülöníti a Sapientia dokumentumokat más cégek anyagaitól.
- Lehetővé teszi, hogy az ingest egyszerre csak egy datasetet töltsön be.
- Biztosítja, hogy a chat és query csak a kiválasztott datasetből olvasson.
- Megakadályozza, hogy nem kapcsolódó dokumentumok ugyanabba a retrieval indexbe keveredjenek.

## Hogyan működik

A rendszer mindenhol egy dataset kulcsot használ, például `sapientia` vagy `company_a`, amikor tudni kell, melyik dokumentumhalmazról van szó.

- Az ingest a `shared/` alatt lévő megfelelő mappából olvas.
- A dokumentumok a dataset kulcs alapján elnevezett pgvector collectionbe kerülnek.
- A retrieval ugyanazt a datasethez kötött collectiont tölti be.
- Az API a kérés body-jában is megkaphatja a `dataset_key` értéket.

Például a `sapientia` dataset a `shared/sapientia` mappához és a `document_embeddings_sapientia` collectionhöz tartozik.

alapértelmezetten shared/sapientia
dataset megadásával a shared/<dataset> mappa

## Tipikus használat

1. Tedd az egyik dataset fájljait a saját mappájába.
2. Futtasd az ingest parancsot ahhoz a datasethez.
3. Tegyél fel kérdéseket ugyanazzal a dataset kulccsal.
4. Ha kell, ismételd meg ugyanezt egy másik datasetre.

## Parancs példák

```bash
docker compose exec api python -m src.utils.ingest_cli
```

```bash
docker compose exec api python -m src.utils.ingest_cli --dataset company_a
```

```bash
docker compose exec api python -m src.utils.query_cli --dataset company_a
```

## Miért ez a megoldás

A külön collection a legbiztonságosabb megoldás, ha erős elkülönítést szeretnél. Így sokkal nehezebb véletlenül összekeverni az adatokat, és a lekérdezés viselkedése is kiszámítható marad akkor is, ha később több cég anyagát kezeled.
