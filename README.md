# IT구성관리 시스템 (MVP)

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

## 4) 서비스 마스터 엑셀 import/export 컬럼 (현재 스키마)

서비스 마스터 화면의 `엑셀 export`는 아래 컬럼 순서로 내려갑니다.  
`엑셀 import`도 동일 컬럼명을 사용하면 그대로 반영됩니다.

- 서비스관리번호 (`service_mgmt_no`)
- 서비스명 (`name`) **[필수]**
- 시스템 구분 (`system_type`) - 코드그룹 `svc_category` 값만 허용
- 설명 (`description`)
- 운영구분 (`operation_type`) - 코드그룹 `opr_division` 값만 허용
- 서비스 등급 (`service_grade`)
- 서비스 수준 (`service_level`)
- ITGC 여부 (`itgc`) - `1/0`, `Y/N`, `TRUE/FALSE` 등 불리언 허용
- 고객사 담당자 (`customer_owner`)
- Appl. 담당자 (`partner_operator`)
- Appl. 운영자 (`appl_owner`) - 저장 시 시스템에서 자동 계산
- 서버 담당자 (`server_owner`)
- DB 담당자 (`db_owner`)
- 서비스 오픈일 (`opened_at`) - 날짜 형식
- 구축 구분 (`build_type`) - 코드그룹 `dev_type` 값만 허용
- 형상관리 (`scm_tool`)
- 배포도구 (`deploy_tool`)
- 모니터링도구 (`monitoring_tool`)
- GC (`gc`) - 불리언
- 파마 (`pharma`) - 불리언
- 플라즈마 (`plasma`) - 불리언
- MU (`mu`) - 불리언
- 엔티스 (`entis`) - 불리언
- 대정 (`daejung`) - 불리언
- DY (`dy`) - 불리언
- BS (`bs`) - 불리언
- BS Share 비율 (`bs_share_ratio`) - 소수 가능
- BS Share 비고 (`bs_share_note`)
- 비고 (`notes`)

### import 시 유의사항

- `서비스명(name)`이 비어 있으면 해당 행은 스킵됩니다.
- `시스템 구분`, `운영구분`, `구축 구분`은 각각 지정 코드그룹에 없는 값이면 스킵됩니다.
- `Appl. 운영자(appl_owner)`는 입력값보다 시스템 계산값이 우선됩니다.
