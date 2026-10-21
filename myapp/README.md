# INFREUM AI② 내일 연동 전 준비 패치

## 이 패치가 하는 일
- `MeasurementViewSet.batch`에서 ACC 3축 `ax_g`, `ay_g`, `az_g`가 누락되는 버그 수정.
- AI② 결과 읽기 전용 `AI2AnalysisResultSerializer`, `AI2AnalysisResultViewSet` 추가.
- 기존 모델/CRUD/Batch API 삭제 또는 이름 변경 없음.

## 적용 전 가정
- **이미** `myapp/models.py`에 `AI2AnalysisResult` 모델을 사용자가 추가함. 이전에 제공된 코드의 클래스 이름과 같아야 함.
- `AnalysisWindow`에 `schema_version`, `ai1_payload`, `ai2_request_payload` 필드 추가.
- AI②의 실제 FastAPI 주소, 인증 및 최종 JSON 규격은 아직 합의 전. 이 패치에는 AI②로 전송하는 HTTP 클라이언트가 **없음**.

## 적용 순서
1. 기존 `myapp/serializers.py`, `myapp/views.py`와 MySQL DB를 먼저 백업.
2. 두 파일을 `myapp/` 폴더에 복사하여 덮어쓰기.
3. PyCharm/PowerShell에서 `python manage.py check`.
4. `python manage.py makemigrations --check --dry-run`으로 `models.py`에 미적용 변경이 있는지 확인. 변경 사항이 있으면 `python manage.py makemigrations myapp`으로 파일 생성 후 SQL 및 변경 내용 검토, 그 다음 백업된 DB에 `python manage.py migrate` 실행. **실행 전 DB 백업 권장.**
5. 선택: 실제 프로젝트의 `myapp/urls.py` 또는 라우터 정의 파일에 `router.register(r"ai2-analysis-results", AI2AnalysisResultViewSet, basename="ai2-analysis-results")` 추가. 이때 필요한 import 및 실제 변수 이름은 사용 중인 `urls.py`에 맞게 수정.
6. 기존 테스트용으로 등록된 bridge_id, sensor_id를 사용하여 `POST /api/v1/measurements/batch/`로 ACC 3축 전송 후 `GET /api/v1/measurements/`에서 값 확인.

## 주의
- AI② 분석 결과를 저장하는 서버 로직, API 키 인증, 실제 AI② 호출은 포함하지 않음.
- `AI2AnalysisResultViewSet`은 GET만 허용. POST/PUT은 서버 내부 저장 API 계약 확정 후 별도 구현.
- 운영 배포 전 DRF 인증/권한을 설정해 센서 데이터와 분석 결과에 대한 무단 열람·수정을 차단할 것. 기존 CRUD에도 같은 문제가 적용될 수 있음.
- 기존 `AnalysisWindow`의 `window_id`는 전체 DB에서 고유이며, AI② 문서의 bridge_type+window_id 정책과 다름. 내일 ID 충돌 정책 합의 필요.
- `RiskResult`의 null 불허 설계는 유지함. 미검증 AI② 결과를 여기에 넣지 말고 `AI2AnalysisResult`로 분리.
