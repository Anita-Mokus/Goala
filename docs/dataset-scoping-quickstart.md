# Dataset Script Usage

Ez a script arra szolgál, hogy egy adott dataset dokumentumait beolvasd a vector database-be, majd ugyanarra a datasetre kérdezz rá az AI-val.

Minden dataset külön kulcsot kap, például `sapientia` vagy `company_a`. A betöltés és a kérdezés mindig ugyanazzal a kulccsal történjen, így az AI csak az adott dataset adatait fogja használni.

Használat egy datasetre:
```bash
docker compose exec api python -m src.utils.ingest_cli --dataset sapientia
docker compose exec api python -m src.utils.query_cli --dataset sapientia
```

Másik datasetnél csak a kulcsot kell átírni:
```bash
docker compose exec api python -m src.utils.ingest_cli --dataset company_a
docker compose exec api python -m src.utils.query_cli --dataset company_a
```
