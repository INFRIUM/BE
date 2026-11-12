# INFRIUM BE 작업 지침

이 저장소는 교량 모형 구조 상태 모니터링 프로토타입 INFRIUM의 Django REST Framework 백엔드다. HW·AI·FE의 구현 상태를 설명할 때는 해당 파트의 소스나 실행 결과로 확인한 범위를 명시한다.

## 작업에 필요한 문서와 코드

| 작업 | 먼저 볼 곳 |
| --- | --- |
| 파트 간 역할, 데이터 흐름, 통합 현황 | [프로젝트 전체 문서](docs/INFRIUM.md) |
| 모델, API, AI② 계약, 재현 절차 | [백엔드 개발 명세](docs/BACKEND.md) |
| API 구현과 권한 확인 | `myapp/urls.py`, `myapp/views.py`, `myapp/serializers.py`, `Infrium/settings.py` |
| DB 변경과 기존 데이터 영향 확인 | `myapp/models.py`, `myapp/migrations/` |

현재 동작을 판단할 때는 체크아웃한 코드와 마이그레이션을 기준으로 삼는다. `myapp/README.md`는 AI② Ingest 구현 이전의 연동 준비 기록이다. 외부에 공개되는 API 계약이나 구현 범위가 바뀌면 관련 개발 문서도 함께 갱신한다.

## 구현 변경 시 확인할 계약

- Measurement Batch는 교량·활성 센서·실험 관계와 `event_id` 고유성을 검증한다. 오류가 있는 배치에서 일부 행만 저장되는 일이 없도록 원자성을 유지한다.
- AI② `ai2-risk-evidence-v1`에서 `damage_class`는 구조 상태다. `risk_score`와 `risk_level`은 `null`로 유지하고, `data_quality`, `evidence`, `raw_payload`를 보존한다.
- AI② Ingest의 Window FK는 선택적이다. 송신 측의 `duplicate`와 BE의 `ingest_duplicate`를 구분한다. 같은 비어 있지 않은 `message_id`와 같은 JSON을 순차 재전송하면 기존 결과를 반환한다.
- 알림 읽음과 처리 상태는 별개다. 처리 상태가 변경되면 상태와 이력을 함께 저장한다.
- 인증이나 외부 연동을 수정할 때 라우트별 권한을 확인한다. 환경 변수 키 목록은 `.env.example`을 사용하고 실제 비밀값은 문서·로그·커밋에서 제외한다.

## 검증

BE 저장소 루트에서 변경 범위에 맞는 검증을 실행한다. Django 설정 확인에는 `python manage.py check`, 모델 변경에는 `python manage.py makemigrations --check --dry-run`을 사용한다. API 변경은 백엔드 명세의 해당 재현 절차를 기준으로 개발 또는 테스트 DB에서 검증한다. 결과를 보고할 때는 실행한 검사와 환경이 없어 실행하지 못한 검사를 명시한다.
