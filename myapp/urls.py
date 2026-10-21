# myapp/urls.py

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    # 인증
    RegisterView,
    LoginView,
    MeView,
    LogoutView,

    # 기존 API
    BridgeViewSet,
    ComponentViewSet,
    SensorViewSet,
    ExperimentViewSet,
    MeasurementViewSet,
    AnalysisWindowViewSet,
    AnomalyResultViewSet,
    RiskResultViewSet,
    AI2AnalysisResultViewSet,
    AlertViewSet,
    AlertStatusHistoryViewSet,
    OperationLogViewSet,
)


# =========================================================
# Router
# =========================================================
router = DefaultRouter()

router.register(r"bridges", BridgeViewSet)
router.register(r"components", ComponentViewSet)
router.register(r"sensors", SensorViewSet)
router.register(r"experiments", ExperimentViewSet)
router.register(r"measurements", MeasurementViewSet)
router.register(r"analysis-windows", AnalysisWindowViewSet)
router.register(r"anomaly-results", AnomalyResultViewSet)
router.register(r"risk-results", RiskResultViewSet)
router.register(r"ai2-analysis-results", AI2AnalysisResultViewSet)
router.register(r"alerts", AlertViewSet)
router.register(r"alert-histories", AlertStatusHistoryViewSet)
router.register(r"operation-logs", OperationLogViewSet)


# =========================================================
# 인증 API
# =========================================================
urlpatterns = [
    path(
        "auth/register/",
        RegisterView.as_view(),
        name="register",
    ),

    path(
        "auth/login/",
        LoginView.as_view(),
        name="login",
    ),

    path(
        "auth/me/",
        MeView.as_view(),
        name="me",
    ),

    path(
        "auth/logout/",
        LogoutView.as_view(),
        name="logout",
    ),
]


# =========================================================
# 기존 Router API 추가
# =========================================================
urlpatterns += router.urls