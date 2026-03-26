import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


def _env(primary: str, legacy: Optional[str], default: str) -> str:
    v = os.getenv(primary)
    if v is not None and v != "":
        return v
    if legacy:
        return os.getenv(legacy, default)
    return default


def _env_int(primary: str, legacy: Optional[str], default: int) -> int:
    raw = _env(primary, legacy, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    ai_backend_host: str = _env("AI_BACKEND_HOST", None, "0.0.0.0")
    ai_backend_port: int = _env_int("AI_BACKEND_PORT", None, 8000)
    ai_backend_log_level: str = _env("AI_BACKEND_LOG_LEVEL", None, "INFO")

    # Roboflow Workflow API Configuration
    roboflow_api_key: str = os.getenv("ROBOFLOW_API_KEY", "")
    roboflow_workspace: str = os.getenv("ROBOFLOW_WORKSPACE", "sanar-gautam")
    roboflow_license_plate_workflow_id: str = os.getenv("ROBOFLOW_LICENSE_PLATE_WORKFLOW_ID", "find-license-plates")
    roboflow_parking_slot_workflow_id: str = os.getenv("ROBOFLOW_PARKING_SLOT_WORKFLOW_ID", "find-parked-vehicles-and-empty-parking-slots")

    # Detection Confidence Thresholds (0-100, converted to 0-1 internally)
    plate_detection_confidence: float = float(os.getenv("PLATE_DETECTION_CONFIDENCE", "20"))
    parking_slot_confidence: float = float(os.getenv("PARKING_SLOT_CONFIDENCE", "20"))

    gate_frame_skip: int = int(os.getenv("GATE_FRAME_SKIP", "10"))
    lot_frame_skip: int = int(os.getenv("LOT_FRAME_SKIP", "20"))
    duplicate_detection_window: int = int(
        os.getenv("DUPLICATE_DETECTION_WINDOW", "10")
    )

    nextjs_api_url: str = os.getenv("NEXTJS_API_URL", "http://localhost:3000")
    nextjs_webhook_entry: str = os.getenv(
        "NEXTJS_WEBHOOK_ENTRY", "/api/ai/webhook/entry"
    )
    nextjs_webhook_exit: str = os.getenv(
        "NEXTJS_WEBHOOK_EXIT", "/api/ai/webhook/exit"
    )
    nextjs_webhook_capacity: str = os.getenv(
        "NEXTJS_WEBHOOK_CAPACITY", "/api/ai/webhook/capacity"
    )
    nextjs_webhook_timeout_seconds: float = float(os.getenv("NEXTJS_WEBHOOK_TIMEOUT_SECONDS", "30"))
    ai_webhook_secret: str = _env("AI_WEBHOOK_SECRET", None, "")

    max_concurrent_streams: int = int(os.getenv("MAX_CONCURRENT_STREAMS", "10"))
    buffer_size: int = int(os.getenv("BUFFER_SIZE", "100"))

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
