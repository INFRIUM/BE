# myapp/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    Bridge,
    Component,
    Sensor,
    Experiment,
    Measurement,
    AnalysisWindow,
    AnomalyResult,
    RiskResult,
    AI2AnalysisResult,
    Alert,
    AlertStatusHistory,
    OperationLog,
)

User = get_user_model()


# =========================================================
# 사용자
# =========================================================
class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        source="first_name",
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
        ]


# =========================================================
# 회원가입
# =========================================================
class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=150,
    )

    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    def validate_email(self, value):
        email = value.strip().lower()

        if User.objects.filter(
            email__iexact=email
        ).exists():
            raise serializers.ValidationError(
                "이미 가입된 이메일입니다."
            )

        return email

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({
                "password_confirm":
                    "비밀번호가 일치하지 않습니다."
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop(
            "password_confirm"
        )

        name = validated_data["name"]
        email = validated_data["email"]
        password = validated_data["password"]

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
        )

        return user


# =========================================================
# 로그인
# =========================================================
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
    )


# =========================================================
# 교량
# =========================================================
class BridgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bridge
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
        ]


# =========================================================
# 구조 부재
# =========================================================
class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = "__all__"


# =========================================================
# 센서
# =========================================================
class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = "__all__"
        read_only_fields = [
            "created_at",
            "updated_at",
        ]


# =========================================================
# 실험
# =========================================================
class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = "__all__"
        read_only_fields = [
            "created_at",
        ]


# =========================================================
# 원시 계측 데이터
# =========================================================
class MeasurementSerializer(serializers.ModelSerializer):
    bridge_id = serializers.CharField(
        source="bridge.bridge_id",
        read_only=True,
    )

    sensor_id = serializers.CharField(
        source="sensor.sensor_id",
        read_only=True,
    )

    sensor_type = serializers.CharField(
        source="sensor.sensor_type",
        read_only=True,
    )

    class Meta:
        model = Measurement
        fields = "__all__"


# =========================================================
# 분석 Window
# =========================================================
class AnalysisWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisWindow
        fields = "__all__"
        read_only_fields = [
            "created_at",
        ]


# =========================================================
# AI① 이상징후 탐지 결과
# =========================================================
class AnomalyResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnomalyResult
        fields = "__all__"
        read_only_fields = [
            "analyzed_at",
        ]


# =========================================================
# AI② 위험도 분석 결과
# =========================================================
class RiskResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskResult
        fields = "__all__"
        read_only_fields = [
            "analyzed_at",
        ]


# =========================================================
# AI② 구조 상태 분류 결과 - Frontend 조회용
#
# 주의:
# damage_class = 구조 상태 분류 결과
# risk_level   = 실제 안전 등급으로 확정된 값이 아님
# AI② v1에서는 risk_score / risk_level이 NULL일 수 있음
# =========================================================
class AI2AnalysisResultSerializer(serializers.ModelSerializer):

    bridge_id = serializers.SerializerMethodField()

    window_id = serializers.CharField(
        source="source_window_id",
        read_only=True,
    )

    class Meta:
        model = AI2AnalysisResult
        fields = "__all__"

        read_only_fields = [
            "id",
            "backend_received_at",
            "analyzed_at",
        ]

    def get_bridge_id(self, obj):
        if obj.window and obj.window.bridge:
            return obj.window.bridge.bridge_id

        return None


# =========================================================
# AI② → Backend 수신용 Serializer
#
# AI② API Schema:
# ai2-risk-evidence-v1
#
# 주의:
# - AI② v1에서는 risk_score / risk_level이 항상 NULL
# - damage_class는 구조 상태 분류 결과이며 안전 등급이 아님
# - data_quality / evidence 객체 전체를 보존
# - 오류 결과에서는 일부 식별 필드가 NULL일 수 있음
# =========================================================
class AI2AnalysisResultIngestSerializer(serializers.Serializer):

    # -----------------------------------------------------
    # 식별 / 메타데이터
    # -----------------------------------------------------
    schema_version = serializers.CharField(
        max_length=50,
        required=True,
    )

    bridge_type = serializers.ChoiceField(
        choices=[
            "BOX",
            "TRUSS",
        ],
        required=True,
        allow_null=True,
    )

    experiment_id = serializers.CharField(
        max_length=100,
        required=True,
        allow_null=True,
        allow_blank=True,
    )

    # 오류 결과에서는 NULL 가능
    window_id = serializers.CharField(
        max_length=100,
        required=True,
        allow_null=True,
        allow_blank=False,
    )

    # 오류 결과에서는 NULL 가능
    timestamp = serializers.CharField(
        max_length=100,
        required=True,
        allow_null=True,
        allow_blank=False,
    )

    event_time = serializers.JSONField(
        required=True,
        allow_null=True,
    )

    message_id = serializers.CharField(
        max_length=150,
        required=True,
        allow_null=True,
        allow_blank=True,
    )

    # -----------------------------------------------------
    # Model C 구조 상태 분류 결과
    # -----------------------------------------------------
    damage_class = serializers.ChoiceField(
        choices=[
            "NORMAL",
            "D1",
            "D2",
            "D3",
        ],
        required=True,
        allow_null=True,
    )

    damage_probabilities = serializers.JSONField(
        required=True,
        allow_null=True,
    )

    # -----------------------------------------------------
    # 위험도
    #
    # AI② v1에서는 두 값 모두 항상 NULL
    # -----------------------------------------------------
    risk_score = serializers.FloatField(
        required=True,
        allow_null=True,
    )

    risk_level = serializers.CharField(
        max_length=30,
        required=True,
        allow_null=True,
    )

    risk_status = serializers.ChoiceField(
        choices=[
            "PENDING_VALIDATION",
            "EVALUATION_ERROR",
        ],
        required=True,
    )

    # -----------------------------------------------------
    # 품질 / 판단 근거
    # -----------------------------------------------------
    data_quality = serializers.JSONField(
        required=True,
    )

    evidence = serializers.JSONField(
        required=True,
    )

    # -----------------------------------------------------
    # AI② 처리 상태
    # -----------------------------------------------------
    processing_status = serializers.ChoiceField(
        choices=[
            "PROCESSED",
            "DUPLICATE",
            "WINDOW_CONFLICT",
            "STALE_DATA",
            "FUTURE_TIMESTAMP",
            "OUT_OF_ORDER",
        ],
        required=True,
    )

    duplicate = serializers.BooleanField(
        required=True,
    )

    out_of_order = serializers.BooleanField(
        required=True,
    )

    received_at = serializers.DateTimeField(
        required=True,
    )

    # 정상 처리에서는 AVAILABLE / PENDING_WARMUP
    # 오류 응답 호환을 위해 NULL 허용
    ai1_status = serializers.ChoiceField(
        choices=[
            "AVAILABLE",
            "PENDING_WARMUP",
        ],
        required=False,
        allow_null=True,
    )

    # -----------------------------------------------------
    # 전체 Payload 검증
    # -----------------------------------------------------
    def validate(self, attrs):

        # =================================================
        # 1. Schema Version
        # =================================================
        if attrs["schema_version"] != "ai2-risk-evidence-v1":
            raise serializers.ValidationError({
                "schema_version":
                    "지원하지 않는 AI② schema_version입니다."
            })

        # =================================================
        # 2. AI② v1에서는 Risk 값이 반드시 NULL
        # =================================================
        if attrs.get("risk_score") is not None:
            raise serializers.ValidationError({
                "risk_score":
                    "AI② v1에서는 risk_score가 반드시 null이어야 합니다."
            })

        if attrs.get("risk_level") is not None:
            raise serializers.ValidationError({
                "risk_level":
                    "AI② v1에서는 risk_level이 반드시 null이어야 합니다."
            })

        # =================================================
        # 3. event_time 객체 타입 검증
        # =================================================
        event_time = attrs.get("event_time")

        if (
            event_time is not None
            and not isinstance(event_time, dict)
        ):
            raise serializers.ValidationError({
                "event_time":
                    "event_time은 object 또는 null이어야 합니다."
            })

        # =================================================
        # 4. damage_probabilities 객체 타입 / Key 검증
        # =================================================
        probabilities = attrs.get(
            "damage_probabilities"
        )

        if probabilities is not None:

            if not isinstance(probabilities, dict):
                raise serializers.ValidationError({
                    "damage_probabilities":
                        "damage_probabilities는 object 또는 null이어야 합니다."
                })

            allowed_keys = {
                "NORMAL",
                "D1",
                "D2",
                "D3",
            }

            unknown_keys = (
                set(probabilities.keys())
                - allowed_keys
            )

            if unknown_keys:
                raise serializers.ValidationError({
                    "damage_probabilities":
                        "허용되지 않은 damage class가 포함되어 있습니다."
                })

            # 확률 값은 숫자여야 함
            for key, value in probabilities.items():

                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                ):
                    raise serializers.ValidationError({
                        "damage_probabilities":
                            f"{key} 확률값은 숫자여야 합니다."
                    })

                if value < 0 or value > 1:
                    raise serializers.ValidationError({
                        "damage_probabilities":
                            f"{key} 확률값은 0 이상 1 이하여야 합니다."
                    })

        # =================================================
        # 5. data_quality는 object
        # =================================================
        data_quality = attrs.get("data_quality")

        if not isinstance(data_quality, dict):
            raise serializers.ValidationError({
                "data_quality":
                    "data_quality는 object여야 합니다."
            })

        # =================================================
        # 6. evidence는 object
        # =================================================
        evidence = attrs.get("evidence")

        if not isinstance(evidence, dict):
            raise serializers.ValidationError({
                "evidence":
                    "evidence는 object여야 합니다."
            })

        # =================================================
        # 7. duplicate / processing_status 일관성
        # =================================================
        processing_status = attrs["processing_status"]
        duplicate = attrs["duplicate"]
        out_of_order = attrs["out_of_order"]

        if processing_status in {
            "DUPLICATE",
            "WINDOW_CONFLICT",
        }:
            if duplicate is not True:
                raise serializers.ValidationError({
                    "duplicate":
                        "DUPLICATE 또는 WINDOW_CONFLICT에서는 "
                        "duplicate가 true여야 합니다."
                })

        else:
            if duplicate is True:
                raise serializers.ValidationError({
                    "duplicate":
                        "DUPLICATE 또는 WINDOW_CONFLICT가 아닌 경우 "
                        "duplicate는 false여야 합니다."
                })

        # =================================================
        # 8. OUT_OF_ORDER 일관성
        # =================================================
        if (
            processing_status == "OUT_OF_ORDER"
            and out_of_order is not True
        ):
            raise serializers.ValidationError({
                "out_of_order":
                    "OUT_OF_ORDER 상태에서는 "
                    "out_of_order가 true여야 합니다."
            })

        # =================================================
        # 9. 정상/중복/충돌 상태에서는
        #    out_of_order가 false여야 함
        # =================================================
        if (
                processing_status in {
            "PROCESSED",
            "DUPLICATE",
            "WINDOW_CONFLICT",
        }
                and out_of_order is True
        ):
            raise serializers.ValidationError({
                "out_of_order":
                    "PROCESSED, DUPLICATE, WINDOW_CONFLICT 상태에서는 "
                    "out_of_order가 false여야 합니다."
            })

        # =================================================
        # 10. 정상 분석에서는 ai1_status 필수
        # =================================================
        risk_status = attrs["risk_status"]
        ai1_status = attrs.get("ai1_status")

        if (
                risk_status == "PENDING_VALIDATION"
                and ai1_status not in {
            "AVAILABLE",
            "PENDING_WARMUP",
        }
        ):
            raise serializers.ValidationError({
                "ai1_status":
                    "PENDING_VALIDATION 상태에서는 "
                    "ai1_status가 AVAILABLE 또는 "
                    "PENDING_WARMUP이어야 합니다."
            })

        return attrs


# =========================================================
# 위험 알림
# =========================================================
class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = "__all__"

        read_only_fields = [
            "alert_id",
            "occurred_at",
            "status",
            "resolved_at",
            "is_read",
            "read_at",
        ]


# =========================================================
# 알림 처리상태 변경 이력
# =========================================================
class AlertStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertStatusHistory
        fields = "__all__"
        read_only_fields = [
            "changed_at",
        ]


# =========================================================
# 운영 로그
# =========================================================
class OperationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationLog
        fields = "__all__"
        read_only_fields = [
            "occurred_at",
        ]