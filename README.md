# ITAM Portal (MVP)

Python/Django 기반 인프라 자산관리(InfraAsset) MVP입니다.  
Admin(Jazzmin) 중심으로 마스터 데이터와 인프라 자산을 관리하고, FAISS + sentence-transformers 기반 AI 검색 API를 제공합니다.

## 1) 로컬 실행

Windows PowerShell 기준:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python manage.py makemigrations
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py seed_roles
.venv\Scripts\python manage.py runserver
```

## 2) 초기 데이터 적재 / 인덱싱

```powershell
.venv\Scripts\python manage.py import_excel --path ".\설계_장판지.xlsx"
.venv\Scripts\python manage.py build_asset_index
```

## 3) 주요 URL

- Admin: `http://127.0.0.1:8000/admin/`
- 조회 웹: `http://127.0.0.1:8000/`
- AI 검색 API: `http://127.0.0.1:8000/api/ai/search?q=검색어`
