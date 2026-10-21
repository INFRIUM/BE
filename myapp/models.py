# models.py

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q


# =========================================================
# Choices
# =========================================================

class BridgeType(models.TextChoices):
    STEEL_BOX_GIRDER = "STEEL_BOX", "Steel Box Girder"
    STEEL_TRUSS = "STEEL_TRUSS", "Steel Truss"


class RiskLevel(models.TextChoices):
    NORMAL = "NORMAL", "정상"
    CAUTION = "CAUTION", "주의"
    WARNING = "WARNING", "경고"
    DANGER = "DANGER", "위험"


class AnomalyLabel(models.TextChoices):
    NORMAL = "NORMAL", "정상"
    ANOMALY = "ANOMALY", "이상"
    PENDING = "PENDING", "분석대기"


class DataStatus(models.TextChoices):
    VALID = "VALID", "유효"
    INVALID = "INVALID", "불량"
    DELAYED = "DELAYED", "지연"
    UNKNOWN = "UNKNOWN", "미확인"


class ExperimentStage(models.TextChoices):
    NORMAL = "NORMAL", "정상"
    ABNORMAL = "ABNORMAL", "이상"


class AlertStatus(models.TextChoices):
    UNCONFIRMED = "UNCONFIRMED", "미확인"
    CONFIRMED = "CONFIRMED", "확인"
    INSPECTING = "INSPECTING", "점검 중"
    RESOLVED = "RESOLVED", "조치 완료"


class LogLevel(models.TextChoices):
    INFO = "INFO", "INFO"
    WARNING = "WARNING", "WARNING"
    ERROR = "ERROR", "ERROR"


class ConditionCode(models.TextChoices):
    NORMAL = "NORMAL", "정상"
    D1 = "D1", "연결부 풀림"
    D2 = "D2", "지지조건 변경"
    D3 = "D3", "부재 강성 변경"


class LoadSource(models.TextChoices):
    LOAD_CELL = "LOAD_CELL", "Load Cell"
    KNOWN_MASS = "KNOWN_MASS", "Known Mass"


class LoadPosition(models.TextChoices):
    LEFT = "LEFT", "Left"
    CENTER = "CENTER", "Center"
    RIGHT = "RIGHT", "Right"


# =========================================================
# 1. 교량
# D01 Bridge_ID
# D02 Bridge_Type
# =========================================================

class Bridge(models.Model):
    bridge_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    bridge_type = models.CharField(
        max_length=30,
        choices=BridgeType.choices,
    )

    name = models.CharField(
        max_length=100,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "bridges"
        ordering = ["bridge_id"]

    def __str__(self):
        return f"{self.bridge_id} ({self.get_bridge_type_display()})"


# =========================================================
# 2. 구조 부재
#
# F08-02-04 Sensor-Component 매핑
# F08-06-04 위험 의심 부재 매핑
#
# 예)
# D03 = 중앙 대각재
# BOTTOM_CHORD_01 = 하현재
# =========================================================

class Component(models.Model):
    bridge = models.ForeignKey(
        Bridge,
        on_delete=models.CASCADE,
        related_name="components",
    )

    component_id = models.CharField(
        max_length=50,
    )

    name = models.CharField(
        max_length=100,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    class Meta:
        db_table = "components"

        constraints = [
            models.UniqueConstraint(
                fields=["bridge", "component_id"],
                name="unique_component_per_bridge",
            )
        ]

        indexes = [
            models.Index(fields=["bridge", "component_id"]),
        ]

        ordering = ["bridge", "component_id"]

    def __str__(self):
        return f"{self.bridge.bridge_id} - {self.component_id}"


# =========================================================
# 3. 센서
#
# D03 Sensor_ID
# D04 Sensor_Type
# D05 Location
# D16 model_x / y / z
# D17 zone_id
#
# F08-02-04 Sensor-Component 매핑
# =========================================================

class Sensor(models.Model):
    bridge = models.ForeignKey(
        Bridge,
        on_delete=models.CASCADE,
        related_name="sensors",
    )

    component = models.ForeignKey(
        Component,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sensors",
    )

    sensor_id = models.CharField(
        max_length=50,
    )

    sensor_type = models.CharField(
        max_length=50,
    )

    # 사람이 읽는 실제 설치 위치
    location = models.CharField(
        max_length=255,
    )

    # 설치 구간 식별자
    zone_id = models.CharField(
        max_length=50,
        blank=True,
    )

    # Digital Twin 모델 내부 좌표
    model_x = models.FloatField(
        null=True,
        blank=True,
    )

    model_y = models.FloatField(
        null=True,
        blank=True,
    )

    model_z = models.FloatField(
        null=True,
        blank=True,
    )

    # 센서 기본 단위
    default_unit = models.CharField(
        max_length=30,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "sensors"

        constraints = [
            models.UniqueConstraint(
                fields=["bridge", "sensor_id"],
                name="unique_sensor_per_bridge",
            )
        ]

        indexes = [
            models.Index(fields=["bridge", "sensor_id"]),
            models.Index(fields=["bridge", "component"]),
            models.Index(fields=["sensor_type"]),
        ]

        ordering = ["bridge", "sensor_id"]

    def __str__(self):
        return f"{self.bridge.bridge_id} - {self.sensor_id}"


# =========================================================
# 4. 실험
#
# D22 experiment_id / stage
# =========================================================

class Experiment(models.Model):
    experiment_id = models.CharField(
        max_length=100,
        unique=True,
    )

    bridge = models.ForeignKey(
        Bridge,
        on_delete=models.CASCADE,
        related_name="experiments",
    )

    stage = models.CharField(
        max_length=20,
        choices=ExperimentStage.choices,
    )

    # D01 / D02 / D03 / D04 등의 상세 이상상태를
    # 별도로 저장할 수 있도록 둠.
    damage_state = models.CharField(
        max_length=50,
        blank=True,
    )

    condition_code = models.CharField(
        max_length=20,
        choices=ConditionCode.choices,
        default=ConditionCode.NORMAL,
    )

    load_n = models.FloatField(
        null=True,
        blank=True,
    )

    load_position = models.CharField(
        max_length=20,
        choices=LoadPosition.choices,
        blank=True,
    )

    load_source = models.CharField(
        max_length=20,
        choices=LoadSource.choices,
        blank=True,
    )

    repeat_no = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    impact_condition = models.CharField(
        max_length=100,
        blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "experiments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.experiment_id} - {self.stage}"


# =========================================================
# 5. 원시 계측 데이터
#
# D06 Timestamp
# D07 Sensor_Value
# D11 event_id
# D12 sequence
# D18 unit
# D20 quality / status
# D21 received_at
# D22 experiment_id
#
# F08-03 / F08-04
# =========================================================

class Measurement(models.Model):
    # 재전송 중복 제거용
    event_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    bridge = models.ForeignKey(
        Bridge,
        on_delete=models.CASCADE,
        related_name="measurements",
    )

    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name="measurements",
    )

    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="measurements",
    )

    # 원 측정시각
    measured_at = models.DateTimeField(
        db_index=True,
    )

    # 동일 센서·시각 내 순서가 필요할 경우
    sequence = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    # =========================================================
    # 단일값 센서용
    # TEMP, LOAD 등
    # =========================================================
    value = models.FloatField(
        null=True,
        blank=True,
    )

    # =========================================================
    # 3축 가속도 센서용
    # ADXL355
    # 단위: g
    # =========================================================
    ax_g = models.FloatField(
        null=True,
        blank=True,
    )

    ay_g = models.FloatField(
        null=True,
        blank=True,
    )

    az_g = models.FloatField(
        null=True,
        blank=True,
    )

    unit = models.CharField(
        max_length=30,
    )

    quality_status = models.CharField(
        max_length=20,
        choices=DataStatus.choices,
        default=DataStatus.VALID,
    )

    # Backend가 실제로 받은 시각
    received_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "measurements"

        indexes = [
            models.Index(
                fields=["bridge", "measured_at"]
            ),
            models.Index(
                fields=["sensor", "measured_at"]
            ),
            models.Index(
                fields=["experiment", "measured_at"]
            ),
        ]

        ordering = ["measured_at", "sequence"]

    def __str__(self):
        return (
            f"{self.sensor.sensor_id} / "
            f"{self.measured_at} / "
            f"{self.value}{self.unit}"
        )


# =========================================================
# 6. 분석 Window
#
# D13 window_id
#
# Measurement와 AI①/AI② 결과를 연결
# Sliding Window를 고려해서 M:N 관계 사용
# =========================================================

class AnalysisWindow(models.Model):
    window_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    bridge = models.ForeignKey(
        Bridge,
        on_delete=models.CASCADE,
        related_name="analysis_windows",
    )

    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analysis_windows",
    )

    start_at = models.DateTimeField()

    end_at = models.DateTimeField(
        db_index=True,
    )

    measurements = models.ManyToManyField(
        Measurement,
        related_name="analysis_windows",
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "analysis_windows"

        indexes = [
            models.Index(
                fields=["bridge", "end_at"]
            ),
        ]

        ordering = ["-end_at"]

    def __str__(self):
        return self.window_id


    # AI①/AI② 데이터 계약 버전
    schema_version = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    # AI①에서 전달받은 원본 JSON
    ai1_payload = models.JSONField(
        null=True,
        blank=True,
    )

    # AI② 분석 API에 전달한 JSON
    ai2_request_payload = models.JSONField(
        null=True,
        blank=True,
    )


# =========================================================
# 7. AI① 이상징후 결과
#
# D08 Anomaly_Score
# D14 anomaly_label
# D19 model_version
#
# F08-05
# =========================================================

class AnomalyResult(models.Model):
    window = models.ForeignKey(
        AnalysisWindow,
        on_delete=models.CASCADE,
        related_name="anomaly_results",
    )

    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name="anomaly_results",
    )

    anomaly_score = models.FloatField()

    anomaly_label = models.CharField(
        max_length=20,
        choices=AnomalyLabel.choices,
        default=AnomalyLabel.PENDING,
    )

    model_version = models.CharField(
        max_length=100,
    )

    analyzed_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "anomaly_results"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "window",
                    "sensor",
                    "model_version",
                ],
                name="unique_anomaly_result",
            )
        ]

        indexes = [
            models.Index(
                fields=["sensor", "analyzed_at"]
            ),
            models.Index(
                fields=["window"]
            ),
        ]

        ordering = ["-analyzed_at"]

    def __str__(self):
        return (
            f"{self.sensor.sensor_id} / "
            f"{self.anomaly_score}"
        )


# =========================================================
# 8. AI② 위험도 분석 결과
#
# D09 Risk_Score
# D10 Risk_Level
# D15 contributing_sensor_ids
# D19 model_version
#
# F08-06
# =========================================================

class RiskResult(models.Model):
    bridge = models.ForeignKey(
        Bridge,
        on_delete=models.CASCADE,
        related_name="risk_results",
    )

    window = models.ForeignKey(
        AnalysisWindow,
        on_delete=models.CASCADE,
        related_name="risk_results",
    )

    risk_score = models.FloatField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ]
    )

    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
    )

    model_version = models.CharField(
        max_length=100,
    )

    # D15
    contributing_sensors = models.ManyToManyField(
        Sensor,
        blank=True,
        related_name="contributed_risk_results",
    )

    # F08-06-04
    # contributing_sensor_ids를 통해 매핑한
    # 위험 의심 구조 부재
    suspected_components = models.ManyToManyField(
        Component,
        blank=True,
        related_name="suspected_risk_results",
    )

    analyzed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = "risk_results"

        constraints = [
            models.CheckConstraint(
                condition=Q(
                    risk_score__gte=0,
                    risk_score__lte=100,
                ),
                name="risk_score_between_0_100",
            ),

            models.UniqueConstraint(
                fields=[
                    "window",
                    "model_version",
                ],
                name="unique_risk_result_per_model",
            ),
        ]

        indexes = [
            models.Index(
                fields=["bridge", "analyzed_at"]
            ),
            models.Index(
                fields=["risk_level"]
            ),
        ]

        ordering = ["-analyzed_at"]

    def __str__(self):
        return (
            f"{self.bridge.bridge_id} / "
            f"{self.risk_score} / "
            f"{self.get_risk_level_display()}"
        )


# =========================================================
# AI② 구조 상태 분석 결과
# AI② API Schema: ai2-risk-evidence-v1
# =========================================================
class AI2AnalysisResult(models.Model):

    # -----------------------------------------------------
    # AI② API Schema 버전
    #
    # 기존 DB 행에는 값이 없으므로 NULL 허용.
    # 신규 ingest에서는 Serializer에서 필수 검증 예정.
    # -----------------------------------------------------
    schema_version = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
    )

    # -----------------------------------------------------
    # AI②가 전달한 교량 유형
    # 예: BOX / TRUSS
    # -----------------------------------------------------
    bridge_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # AI②가 전달한 실험 ID
    # -----------------------------------------------------
    experiment_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
    )

    # -----------------------------------------------------
    # Backend AnalysisWindow 연결
    #
    # AI②의 window_id와 Backend의 AnalysisWindow가
    # 매칭되는 경우 연결한다.
    # -----------------------------------------------------
    window = models.ForeignKey(
        AnalysisWindow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai2_analysis_results",
    )

    # -----------------------------------------------------
    # AI②가 실제로 보내온 원본 window_id
    #
    # 위 window FK와 별도로 원본 식별자를 보존한다.
    # -----------------------------------------------------
    source_window_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
    )

    # -----------------------------------------------------
    # AI② 원본 timestamp
    # -----------------------------------------------------
    source_timestamp = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # AI② event_time 객체
    #
    # window_start
    # window_start_us
    # window_end_us
    # 등을 JSON 그대로 보존
    # -----------------------------------------------------
    event_time = models.JSONField(
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # AI② message_id
    # -----------------------------------------------------
    message_id = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        db_index=True,
    )

    # -----------------------------------------------------
    # Model C 구조 상태 분류 결과
    #
    # NORMAL / D1 / D2 / D3
    #
    # 주의:
    # damage_class는 안전 등급이나 위험 등급이 아님.
    # -----------------------------------------------------
    damage_class = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # 구조 상태별 확률
    #
    # 예:
    # {
    #     "NORMAL": 0.05,
    #     "D1": 0.15,
    #     "D2": 0.72,
    #     "D3": 0.08
    # }
    # -----------------------------------------------------
    damage_probabilities = models.JSONField(
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # 위험도 점수
    #
    # AI② v1에서는 NULL이 정상일 수 있음.
    # 절대로 NULL을 0으로 변환하지 않는다.
    # -----------------------------------------------------
    risk_score = models.FloatField(
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # 위험 등급
    #
    # AI② v1에서는 NULL이 정상일 수 있음.
    # 절대로 NULL을 NORMAL로 변환하지 않는다.
    # -----------------------------------------------------
    risk_level = models.CharField(
        max_length=30,
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # 위험도 산출 상태
    #
    # 예:
    # PENDING_VALIDATION
    # EVALUATION_ERROR
    #
    # 기존 DB 호환을 위해 NULL 허용.
    # -----------------------------------------------------
    risk_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
    )

    # -----------------------------------------------------
    # 데이터 품질 정보 전체
    #
    # primary_status 하나만 저장하지 않고
    # statuses 배열 등을 포함한 객체 전체를 저장한다.
    # -----------------------------------------------------
    data_quality = models.JSONField(
        default=dict,
        blank=True,
    )

    # -----------------------------------------------------
    # AI② 판단 근거 전체
    #
    # baseline
    # feature_changes
    # ai1_result
    # xgboost_model_c
    # error
    # 등을 그대로 저장
    # -----------------------------------------------------
    evidence = models.JSONField(
        default=dict,
        blank=True,
    )

    # -----------------------------------------------------
    # AI② 처리 상태
    #
    # 예:
    # PROCESSED
    # DUPLICATE
    # WINDOW_CONFLICT
    # STALE_DATA
    # FUTURE_TIMESTAMP
    # OUT_OF_ORDER
    #
    # 기존 DB 호환을 위해 NULL 허용.
    # -----------------------------------------------------
    processing_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
    )

    # -----------------------------------------------------
    # 중복 Window 여부
    # -----------------------------------------------------
    duplicate = models.BooleanField(
        default=False,
        db_index=True,
    )

    # -----------------------------------------------------
    # 순서 역전 여부
    # -----------------------------------------------------
    out_of_order = models.BooleanField(
        default=False,
        db_index=True,
    )

    # -----------------------------------------------------
    # AI②가 요청을 받은 시각
    #
    # 기존 DB에는 값이 없으므로 NULL 허용.
    # -----------------------------------------------------
    ai2_received_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # AI① 상태
    #
    # 예:
    # AVAILABLE
    # PENDING_WARMUP
    # -----------------------------------------------------
    ai1_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )

    # -----------------------------------------------------
    # Django Backend가 AI② 결과를 받은 시각
    #
    # 기존 데이터에는 값이 없으므로 NULL 허용.
    # 신규 ingest()에서 timezone.now() 기록 예정.
    # -----------------------------------------------------
    backend_received_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    # -----------------------------------------------------
    # AI②가 전송한 JSON 원본 전체
    #
    # Schema 변경 및 디버깅을 위해 보존
    # -----------------------------------------------------
    raw_payload = models.JSONField(
        default=dict,
        blank=True,
    )

    # -----------------------------------------------------
    # 기존 AI② 결과 필드
    # 기존 DB 및 과거 테스트 데이터 호환을 위해 유지
    # -----------------------------------------------------

    # 기존 AI② 모델 버전
    model_version = models.CharField(
        max_length=100,
        blank=True,
    )

    # 기존 AI② 원본 응답
    raw_response = models.JSONField(
        null=True,
        blank=True,
    )

    # 기존 AI② 분석 결과 생성 시각
    analyzed_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "ai2_analysis_results"
        ordering = [
            "-backend_received_at",
        ]

    def __str__(self):
        return (
            f"{self.source_window_id or 'NO_WINDOW'} "
            f"- {self.damage_class or 'NO_RESULT'}"
        )


# =========================================================
# 9. 위험 알림
#
# D23 alert_id
# F08-12
# F11
# =========================================================

class Alert(models.Model):
    alert_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    bridge = models.ForeignKey(
        Bridge,
        on_delete=models.CASCADE,
        related_name="alerts",
    )

    # 같은 분석 결과를 반복 수신해도
    # 같은 알림을 중복 생성하지 않음
    risk_result = models.OneToOneField(
        RiskResult,
        on_delete=models.CASCADE,
        related_name="alert",
    )

    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
    )

    recommendation = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
        default=AlertStatus.UNCONFIRMED,
    )

    occurred_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_read = models.BooleanField(
        default=False,
        db_index=True,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )


    class Meta:
        db_table = "alerts"

        indexes = [
            models.Index(
                fields=["bridge", "occurred_at"]
            ),
            models.Index(
                fields=["risk_level", "status"]
            ),
        ]

        ordering = ["-occurred_at"]

    def __str__(self):
        return (
            f"{self.bridge.bridge_id} - "
            f"{self.get_risk_level_display()}"
        )


# =========================================================
# 10. 알림 처리상태 변경 이력
#
# F08-12-03
# 미확인 → 확인 → 점검 중 → 조치 완료
# =========================================================

class AlertStatusHistory(models.Model):
    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    from_status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
        blank=True,
    )

    to_status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alert_status_changes",
    )

    changed_at = models.DateTimeField(
        auto_now_add=True,
    )

    note = models.TextField(
        blank=True,
    )

    class Meta:
        db_table = "alert_status_history"
        ordering = ["-changed_at"]

    def __str__(self):
        return (
            f"{self.alert.alert_id}: "
            f"{self.from_status} -> {self.to_status}"
        )


# =========================================================
# 11. 운영 로그
#
# F12-03
# 수집·API·모델·재전송 실패 기록
# =========================================================

class OperationLog(models.Model):
    level = models.CharField(
        max_length=10,
        choices=LogLevel.choices,
        default=LogLevel.INFO,
    )

    source = models.CharField(
        max_length=50,
    )

    target_id = models.CharField(
        max_length=100,
        blank=True,
    )

    error_code = models.CharField(
        max_length=50,
        blank=True,
    )

    message = models.TextField()

    retry_result = models.TextField(
        blank=True,
    )

    occurred_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = "operation_logs"
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"[{self.level}] {self.source} - {self.message[:30]}"