# myapp/views.py

from django.db import transaction
from django.contrib.auth import authenticate
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from rest_framework.exceptions import ValidationError
from rest_framework import status, viewsets, generics
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
    AlertStatus,
    AlertStatusHistory,
    OperationLog,
)

from .serializers import (
    BridgeSerializer,
    ComponentSerializer,
    SensorSerializer,
    ExperimentSerializer,
    MeasurementSerializer,
    AnalysisWindowSerializer,
    AnomalyResultSerializer,
    RiskResultSerializer,
    AI2AnalysisResultSerializer,
    AI2AnalysisResultIngestSerializer,
    AlertSerializer,
    AlertStatusHistorySerializer,
    OperationLogSerializer,
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,

)


# =========================================================
# 회원가입
# =========================================================
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = serializer.save()

        return Response(
            {
                "message": "회원가입이 완료되었습니다.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


# =========================================================
# 로그인
# =========================================================
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        email = (
            serializer.validated_data["email"]
            .strip()
            .lower()
        )

        password = serializer.validated_data[
            "password"
        ]

        user = authenticate(
            username=email,
            password=password,
        )

        if user is None:
            return Response(
                {
                    "error": "이메일 또는 비밀번호가 올바르지 않습니다."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token, _ = Token.objects.get_or_create(
            user=user
        )

        return Response(
            {
                "message": "로그인되었습니다.",
                "token": token.key,
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


# =========================================================
# 현재 로그인 사용자
# =========================================================
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            UserSerializer(
                request.user
            ).data,
            status=status.HTTP_200_OK,
        )


# =========================================================
# 로그아웃
# =========================================================
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(
            user=request.user
        ).delete()

        return Response(
            {
                "message": "로그아웃되었습니다."
            },
            status=status.HTTP_200_OK,
        )


# =========================================================
# 교량
# =========================================================
class BridgeViewSet(viewsets.ModelViewSet):
    queryset = Bridge.objects.all()
    serializer_class = BridgeSerializer


# =========================================================
# 구조 부재
# =========================================================
class ComponentViewSet(viewsets.ModelViewSet):
    queryset = Component.objects.all()
    serializer_class = ComponentSerializer


# =========================================================
# 센서
# =========================================================
class SensorViewSet(viewsets.ModelViewSet):
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        bridge_id = self.request.query_params.get("bridge_id")

        if bridge_id:
            queryset = queryset.filter(
                bridge__bridge_id=bridge_id
            )

        return queryset


# =========================================================
# 실험
# =========================================================
class ExperimentViewSet(viewsets.ModelViewSet):
    queryset = Experiment.objects.all()
    serializer_class = ExperimentSerializer


# =========================================================
# 원시 계측 데이터
# =========================================================
class MeasurementViewSet(viewsets.ModelViewSet):
    queryset = (
        Measurement.objects
        .select_related(
            "bridge",
            "sensor",
            "sensor__component",
            "experiment",
        )
        .all()
    )

    serializer_class = MeasurementSerializer

    # =========================================================
    # GET /api/v1/measurements/
    #
    # Query Parameter
    # - bridge_id
    # - sensor_id
    # - from
    # - to
    #
    # 예:
    # /measurements/?bridge_id=BOX_01
    # /measurements/?sensor_id=ACC_BOX_01
    # =========================================================
    def get_queryset(self):

        queryset = super().get_queryset()

        bridge_id = self.request.query_params.get("bridge_id")
        sensor_id = self.request.query_params.get("sensor_id")

        from_time = self.request.query_params.get("from")
        to_time = self.request.query_params.get("to")

        # -----------------------------------------------------
        # Bridge 필터
        # -----------------------------------------------------
        if bridge_id:
            queryset = queryset.filter(
                bridge__bridge_id=bridge_id
            )

        # -----------------------------------------------------
        # Sensor 필터
        # -----------------------------------------------------
        if sensor_id:
            queryset = queryset.filter(
                sensor__sensor_id=sensor_id
            )

        # -----------------------------------------------------
        # 시작 시간 필터
        # measured_at >= from
        # -----------------------------------------------------
        if from_time:

            parsed_from = parse_datetime(from_time)

            if parsed_from is None:
                raise ValidationError({
                    "from":
                        "올바른 ISO 8601 날짜/시간 형식을 입력하세요."
                })

            if timezone.is_naive(parsed_from):
                parsed_from = timezone.make_aware(
                    parsed_from
                )

            queryset = queryset.filter(
                measured_at__gte=parsed_from
            )

        # -----------------------------------------------------
        # 종료 시간 필터
        # measured_at <= to
        # -----------------------------------------------------
        if to_time:

            parsed_to = parse_datetime(to_time)

            if parsed_to is None:
                raise ValidationError({
                    "to":
                        "올바른 ISO 8601 날짜/시간 형식을 입력하세요."
                })

            if timezone.is_naive(parsed_to):
                parsed_to = timezone.make_aware(
                    parsed_to
                )

            queryset = queryset.filter(
                measured_at__lte=parsed_to
            )

        # -----------------------------------------------------
        # 최신 측정값부터 반환
        # -----------------------------------------------------
        return queryset.order_by(
            "-measured_at",
            "-sequence",
        )


    # =========================================================
    # POST /api/v1/measurements/batch/
    #
    # 여러 센서 측정값을 한 번에 저장
    # =========================================================
    @action(
        detail=False,
        methods=["post"],
        url_path="batch",
    )
    def batch(self, request):

        # -----------------------------------------------------
        # 1. 요청 데이터 확인
        # -----------------------------------------------------
        bridge_id = request.data.get("bridge_id")
        measurements = request.data.get("measurements")
        experiment_id = request.data.get("experiment_id")

        if not bridge_id:
            return Response(
                {
                    "error": "bridge_id는 필수입니다."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(measurements, list) or not measurements:
            return Response(
                {
                    "error": "measurements는 비어 있지 않은 배열이어야 합니다."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


        # -----------------------------------------------------
        # 2. Bridge 확인
        # -----------------------------------------------------
        try:
            bridge = Bridge.objects.get(
                bridge_id=bridge_id
            )

        except Bridge.DoesNotExist:
            return Response(
                {
                    "error": f"등록되지 않은 Bridge입니다: {bridge_id}"
                },
                status=status.HTTP_404_NOT_FOUND,
            )


        # -----------------------------------------------------
        # 3. Experiment 확인
        # 현재는 없어도 됨
        # -----------------------------------------------------
        experiment = None

        if experiment_id:
            try:
                experiment = Experiment.objects.get(
                    experiment_id=experiment_id,
                    bridge=bridge,
                )

            except Experiment.DoesNotExist:
                return Response(
                    {
                        "error":
                            f"해당 Bridge에 등록되지 않은 Experiment입니다: "
                            f"{experiment_id}"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )


        # -----------------------------------------------------
        # 4. event_id 검사
        # -----------------------------------------------------
        event_ids = []

        for index, item in enumerate(measurements):

            event_id = item.get("event_id")

            if not event_id:
                return Response(
                    {
                        "error":
                            f"measurements[{index}].event_id가 없습니다."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            event_ids.append(event_id)


        # -----------------------------------------------------
        # 5. 요청 내부 event_id 중복 검사
        # -----------------------------------------------------
        duplicate_event_ids = {
            event_id
            for event_id in event_ids
            if event_ids.count(event_id) > 1
        }

        if duplicate_event_ids:
            return Response(
                {
                    "error": "요청 데이터 내부에 중복 event_id가 있습니다.",
                    "duplicate_event_ids": list(
                        duplicate_event_ids
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


        # -----------------------------------------------------
        # 6. DB에 이미 존재하는 event_id 검사
        # -----------------------------------------------------
        existing_event_ids = list(
            Measurement.objects
            .filter(event_id__in=event_ids)
            .values_list(
                "event_id",
                flat=True,
            )
        )

        if existing_event_ids:
            return Response(
                {
                    "error":
                        "이미 저장된 event_id가 포함되어 있습니다.",
                    "existing_event_ids":
                        existing_event_ids,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


        # -----------------------------------------------------
        # 7. Sensor 확인
        # -----------------------------------------------------
        sensor_ids = []

        for index, item in enumerate(measurements):

            sensor_id = item.get("sensor_id")

            if not sensor_id:
                return Response(
                    {
                        "error":
                            f"measurements[{index}].sensor_id가 없습니다."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            sensor_ids.append(sensor_id)


        sensors = {
            sensor.sensor_id: sensor
            for sensor in Sensor.objects.filter(
                bridge=bridge,
                sensor_id__in=sensor_ids,
                is_active=True,
            )
        }


        # 등록되지 않은 Sensor 확인
        missing_sensor_ids = [
            sensor_id
            for sensor_id in sensor_ids
            if sensor_id not in sensors
        ]

        if missing_sensor_ids:
            return Response(
                {
                    "error":
                        "등록되지 않았거나 비활성화된 Sensor가 있습니다.",
                    "sensor_ids":
                        missing_sensor_ids,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


        # -----------------------------------------------------
        # 8. Serializer용 데이터 생성
        # -----------------------------------------------------
        serializer_data = []

        for item in measurements:

            sensor = sensors[
                item["sensor_id"]
            ]

            serializer_data.append(
                {
                    "event_id":
                        item["event_id"],

                    "bridge":
                        bridge.pk,

                    "sensor":
                        sensor.pk,

                    "experiment":
                        experiment.pk
                        if experiment
                        else None,

                    "measured_at":
                        item.get("measured_at"),

                    "sequence":
                        item.get("sequence"),

                    "value":
                        item.get("value"),

                    # 가속도 센서(X/Y/Z) 값을 빠뜨리지 않고 전달
                    "ax_g":
                        item.get("ax_g"),
                    "ay_g":
                        item.get("ay_g"),
                    "az_g":
                        item.get("az_g"),

                    # unit을 보내지 않으면
                    # Sensor 기본 단위를 사용
                    "unit":
                        item.get("unit")
                        or sensor.default_unit,

                    "quality_status":
                        item.get(
                            "quality_status",
                            "VALID",
                        ),
                }
            )


        # -----------------------------------------------------
        # 9. Serializer 검증
        # -----------------------------------------------------
        serializer = self.get_serializer(
            data=serializer_data,
            many=True,
        )

        serializer.is_valid(
            raise_exception=True
        )


        # -----------------------------------------------------
        # 10. 전체 저장
        #
        # 한 건이라도 실패하면 전체 rollback
        # -----------------------------------------------------
        with transaction.atomic():

            created_measurements = (
                serializer.save()
            )


        # -----------------------------------------------------
        # 11. 저장 결과 반환
        # -----------------------------------------------------
        result_serializer = self.get_serializer(
            created_measurements,
            many=True,
        )

        return Response(
            {
                "message":
                    "측정 데이터 Batch 저장 완료",

                "bridge_id":
                    bridge.bridge_id,

                "created_count":
                    len(created_measurements),

                "measurements":
                    result_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


# =========================================================
# 분석 Window
# =========================================================
class AnalysisWindowViewSet(viewsets.ModelViewSet):
    queryset = AnalysisWindow.objects.all()
    serializer_class = AnalysisWindowSerializer


# =========================================================
# AI① 이상징후 탐지 결과
# =========================================================
class AnomalyResultViewSet(viewsets.ModelViewSet):
    queryset = AnomalyResult.objects.all()
    serializer_class = AnomalyResultSerializer


# =========================================================
# AI② 위험도 분석 결과
# =========================================================
class RiskResultViewSet(viewsets.ModelViewSet):
    queryset = RiskResult.objects.all()
    serializer_class = RiskResultSerializer


# =========================================================
# AI② 구조 상태 분석 결과
#
# GET
# /api/v1/ai2-analysis-results/
#
# POST
# /api/v1/ai2-analysis-results/ingest/
#
# AI② → Django Backend → DB → Frontend
#
# 주의:
# - damage_class는 구조 상태 분류 결과
# - risk_score / risk_level이 NULL이어도 정상
# - Backend에서 임의로 위험도를 생성하지 않음
# - AI② 원본 payload 전체를 raw_payload에 보존
# =========================================================
class AI2AnalysisResultViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = (
        AI2AnalysisResult.objects
        .select_related(
            "window",
            "window__bridge",
        )
        .all()
    )

    serializer_class = AI2AnalysisResultSerializer

    # =====================================================
    # GET /api/v1/ai2-analysis-results/
    #
    # Query Parameter
    # - bridge_id
    # - window_id
    # - experiment_id
    # - damage_class
    # - processing_status
    # =====================================================
    def get_queryset(self):

        queryset = super().get_queryset()

        bridge_id = self.request.query_params.get(
            "bridge_id"
        )

        window_id = self.request.query_params.get(
            "window_id"
        )

        experiment_id = self.request.query_params.get(
            "experiment_id"
        )

        damage_class = self.request.query_params.get(
            "damage_class"
        )

        processing_status = self.request.query_params.get(
            "processing_status"
        )

        if bridge_id:
            queryset = queryset.filter(
                window__bridge__bridge_id=bridge_id
            )

        if window_id:
            queryset = queryset.filter(
                source_window_id=window_id
            )

        if experiment_id:
            queryset = queryset.filter(
                experiment_id=experiment_id
            )

        if damage_class:
            queryset = queryset.filter(
                damage_class=damage_class
            )

        if processing_status:
            queryset = queryset.filter(
                processing_status=processing_status
            )

        return queryset.order_by(
            "-backend_received_at",
            "-id",
        )

    # =====================================================
    # POST /api/v1/ai2-analysis-results/ingest/
    #
    # AI② 분석 결과 수신
    # =====================================================
    @action(
        detail=False,
        methods=["post"],
        url_path="ingest",
    )
    def ingest(self, request):

        # -------------------------------------------------
        # 1. AI② Payload 검증
        # -------------------------------------------------
        ingest_serializer = (
            AI2AnalysisResultIngestSerializer(
                data=request.data
            )
        )

        ingest_serializer.is_valid(
            raise_exception=True
        )

        data = ingest_serializer.validated_data

        # -------------------------------------------------
        # 2. HTTP 재전송 Idempotency 확인
        #
        # 주의:
        # AI②가 판단한 DUPLICATE / WINDOW_CONFLICT와
        # Backend HTTP 재전송은 서로 다른 개념이다.
        #
        # 같은 message_id + 완전히 같은 payload인 경우만
        # 동일 HTTP 요청의 재전송으로 판단한다.
        # -------------------------------------------------
        message_id = data.get("message_id")

        if message_id:

            existing_results = (
                AI2AnalysisResult.objects
                .select_related(
                    "window",
                    "window__bridge",
                )
                .filter(
                    message_id=message_id
                )
                .order_by("-id")
            )

            for existing in existing_results:

                if existing.raw_payload == request.data:
                    return Response(
                        {
                            "message":
                                "동일한 AI② HTTP 요청이 이미 처리되었습니다.",

                            # AI②의 duplicate 필드와 구분
                            "ingest_duplicate": True,

                            "matched_window":
                                existing.window is not None,

                            "result":
                                AI2AnalysisResultSerializer(
                                    existing
                                ).data,
                        },
                        status=status.HTTP_200_OK,
                    )


        # -------------------------------------------------
        # 3. AI② 원본 window_id
        #
        # 오류 결과에서는 window_id가 NULL일 수 있다.
        # -------------------------------------------------
        source_window_id = data.get("window_id")


        # -------------------------------------------------
        # 4. Backend AnalysisWindow 연결 시도
        #
        # window_id가 NULL이면 연결을 시도하지 않는다.
        # 등록된 AnalysisWindow가 없어도
        # AI② 결과 자체는 DB에 보존한다.
        # -------------------------------------------------
        window = None

        if source_window_id:
            window = (
                AnalysisWindow.objects
                .select_related("bridge")
                .filter(
                    window_id=source_window_id
                )
                .first()
            )


        # -------------------------------------------------
        # 5. AI② 결과 저장
        #
        # risk_score / risk_level은 전달된 값을 그대로
        # 저장하며 NULL을 임의 값으로 변경하지 않는다.
        # -------------------------------------------------
        with transaction.atomic():

            result = AI2AnalysisResult.objects.create(

                schema_version=data[
                    "schema_version"
                ],

                bridge_type=data.get(
                    "bridge_type"
                ),

                experiment_id=data.get(
                    "experiment_id"
                ),

                window=window,

                source_window_id=(
                    source_window_id
                ),

                source_timestamp=data.get(
                    "timestamp"
                ),

                event_time=data.get(
                    "event_time"
                ),

                message_id=data.get(
                    "message_id"
                ),

                damage_class=data.get(
                    "damage_class"
                ),

                damage_probabilities=data.get(
                    "damage_probabilities"
                ),

                risk_score=data.get(
                    "risk_score"
                ),

                risk_level=data.get(
                    "risk_level"
                ),

                risk_status=data[
                    "risk_status"
                ],

                data_quality=data.get(
                    "data_quality",
                    {},
                ),

                evidence=data.get(
                    "evidence",
                    {},
                ),

                processing_status=data[
                    "processing_status"
                ],

                duplicate=data.get(
                    "duplicate",
                    False,
                ),

                out_of_order=data.get(
                    "out_of_order",
                    False,
                ),

                ai2_received_at=data.get(
                    "received_at"
                ),

                ai1_status=data.get(
                    "ai1_status"
                ),

                backend_received_at=(
                    timezone.now()
                ),

                # AI②가 실제로 전송한 JSON 전체 보존
                raw_payload=request.data,
            )

        # -------------------------------------------------
        # 6. Frontend 조회 형식으로 응답
        # -------------------------------------------------
        result_serializer = (
            AI2AnalysisResultSerializer(
                result
            )
        )

        return Response(
            {
                "message":
                    "AI② 분석 결과가 저장되었습니다.",

                "matched_window":
                    window is not None,

                "result":
                    result_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


# =========================================================
# 위험 알림
# =========================================================
class AlertViewSet(viewsets.ModelViewSet):
    queryset = (
        Alert.objects
        .select_related(
            "bridge",
            "risk_result",
        )
        .all()
    )

    serializer_class = AlertSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        bridge_id = self.request.query_params.get(
            "bridge_id"
        )
        status_value = self.request.query_params.get(
            "status"
        )
        risk_level = self.request.query_params.get(
            "risk_level"
        )
        is_read = self.request.query_params.get(
            "is_read"
        )

        if bridge_id:
            queryset = queryset.filter(
                bridge__bridge_id=bridge_id
            )

        if status_value:
            queryset = queryset.filter(
                status=status_value
            )

        if risk_level:
            queryset = queryset.filter(
                risk_level=risk_level
            )

        if is_read is not None:
            if is_read.lower() == "true":
                queryset = queryset.filter(
                    is_read=True
                )

            elif is_read.lower() == "false":
                queryset = queryset.filter(
                    is_read=False
                )

        return queryset.order_by(
            "-occurred_at"
        )

    # =====================================================
    # GET /api/v1/alerts/summary/
    # 알림 개수 요약
    # =====================================================
    @action(
        detail=False,
        methods=["get"],
        url_path="summary",
    )
    def summary(self, request):
        queryset = self.get_queryset()

        return Response({
            "total_count":
                queryset.count(),

            "unread_count":
                queryset.filter(
                    is_read=False
                ).count(),

            "unconfirmed_count":
                queryset.filter(
                    status=AlertStatus.UNCONFIRMED
                ).count(),

            "inspecting_count":
                queryset.filter(
                    status=AlertStatus.INSPECTING
                ).count(),
        })

    # =====================================================
    # POST /api/v1/alerts/{id}/read/
    # 알림 하나 읽음 처리
    # =====================================================
    @action(
        detail=True,
        methods=["post"],
        url_path="read",
    )
    def mark_read(self, request, pk=None):
        alert = self.get_object()

        if not alert.is_read:
            alert.is_read = True
            alert.read_at = timezone.now()

            alert.save(
                update_fields=[
                    "is_read",
                    "read_at",
                ]
            )

        return Response(
            self.get_serializer(alert).data
        )

    # =====================================================
    # POST /api/v1/alerts/read-all/
    # 모두 읽음
    # =====================================================
    @action(
        detail=False,
        methods=["post"],
        url_path="read-all",
    )
    def read_all(self, request):
        queryset = self.get_queryset().filter(
            is_read=False
        )

        updated_count = queryset.update(
            is_read=True,
            read_at=timezone.now(),
        )

        return Response({
            "message": "모든 알림을 읽음 처리했습니다.",
            "updated_count": updated_count,
        })

    # =====================================================
    # POST /api/v1/alerts/1/status/
    # 확인/점검/해결
    # =====================================================
    @action(
        detail=True,
        methods=["post"],
        url_path="status",
    )
    def change_status(self, request, pk=None):
        alert = self.get_object()

        new_status = request.data.get(
            "status"
        )

        note = request.data.get(
            "note",
            "",
        )

        valid_statuses = {
            value
            for value, _
            in AlertStatus.choices
        }

        if new_status not in valid_statuses:
            return Response(
                {
                    "error":
                        "올바르지 않은 알림 상태입니다."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = alert.status

        if old_status == new_status:
            return Response(
                self.get_serializer(alert).data
            )

        with transaction.atomic():

            alert.status = new_status

            if new_status == AlertStatus.RESOLVED:
                alert.resolved_at = timezone.now()

            alert.save(
                update_fields=[
                    "status",
                    "resolved_at",
                ]
            )

            AlertStatusHistory.objects.create(
                alert=alert,
                from_status=old_status,
                to_status=new_status,
                changed_by=(
                    request.user
                    if request.user.is_authenticated
                    else None
                ),
                note=note,
            )

        return Response(
            self.get_serializer(alert).data
        )

# =========================================================
# 알림 처리상태 이력
# =========================================================
class AlertStatusHistoryViewSet(
    viewsets.ReadOnlyModelViewSet
):
    queryset = (
        AlertStatusHistory.objects
        .select_related(
            "alert",
            "alert__bridge",
            "changed_by",
        )
        .all()
    )

    serializer_class = (
        AlertStatusHistorySerializer
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        bridge_id = self.request.query_params.get(
            "bridge_id"
        )

        alert_id = self.request.query_params.get(
            "alert_id"
        )

        if bridge_id:
            queryset = queryset.filter(
                alert__bridge__bridge_id=
                    bridge_id
            )

        if alert_id:
            queryset = queryset.filter(
                alert__alert_id=alert_id
            )

        return queryset.order_by(
            "-changed_at"
        )


# =========================================================
# 운영 로그
# =========================================================
class OperationLogViewSet(viewsets.ModelViewSet):
    queryset = OperationLog.objects.all()
    serializer_class = OperationLogSerializer