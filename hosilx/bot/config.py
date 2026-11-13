
"""Muhit sozlamalari. Maxfiy qiymatlar faqat environment'dan olinadi."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    supabase_url: str
    supabase_service_key: str

    web_url: str = ""
    mode: str = "polling"
    webhook_url: str = ""
    webhook_secret: str = ""
    webhook_path: str = "/telegram/webhook"
    port: int = 10000
    redis_url: str = ""

    # Gemini AI
    gemini_api_key: str = ""
    ai_model: str = "gemini-2.5-flash"
    ai_daily_limit: int = 50

    finance_extended: bool = False
    log_level: str = "INFO"
    keepalive_url: str = ""
    keepalive_interval: int = 600

    def __repr__(self) -> str:
        return (
            f"Settings(mode={self.mode!r}, "
            f"supabase_url={self.supabase_url!r}, "
            f"web_url={self.web_url!r}, secrets=***)"
        )


def _bool(v: str) -> bool:
    return v.strip().lower() in {"1", "true", "yes", "on"}


def resolve_keepalive_url(env: Mapping[str, str]) -> str:
    """KEEPALIVE_URL yoki Render RENDER_EXTERNAL_URL manzilini oladi."""
    if (env.get("KEEPALIVE") or "").strip().lower() in {
        "0", "false", "off", "no"
    }:
        return ""

    url = (
        env.get("KEEPALIVE_URL")
        or env.get("RENDER_EXTERNAL_URL")
        or ""
    ).strip().rstrip("/")

    return url if url.startswith("https://") else ""


def load_settings(env: Mapping[str, str]) -> Settings:

    def need(name: str) -> str:
        value = (env.get(name) or "").strip()
        if not value:
            raise ConfigError(f"{name} kiritilmagan")
        return value

    # Telegram
    token = (
        env.get("TELEGRAM_BOT_TOKEN")
        or env.get("BOT_TOKEN")
        or ""
    ).strip()

    if not token:
        raise ConfigError("TELEGRAM_BOT_TOKEN kiritilmagan")

    if not re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{20,}", token):
        raise ConfigError("TELEGRAM_BOT_TOKEN formati noto'g'ri")

    # Supabase
    url = need("SUPABASE_URL").rstrip("/")

    if not url.startswith("https://"):
        raise ConfigError("SUPABASE_URL https:// bilan boshlanishi kerak")

    service_key = need("SUPABASE_SERVICE_KEY")

    # Bot rejimi
    mode = (env.get("BOT_MODE") or "polling").strip().lower()

    if mode not in {"polling", "webhook"}:
        raise ConfigError("BOT_MODE polling yoki webhook bo'lishi kerak")

    webhook_url = (
        env.get("WEBHOOK_URL") or ""
    ).strip().rstrip("/")

    secret = (env.get("WEBHOOK_SECRET") or "").strip()

    if mode == "webhook":
        if not webhook_url.startswith("https://"):
            raise ConfigError(
                "webhook rejimi uchun WEBHOOK_URL (https) kerak"
            )

        if not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", secret):
            raise ConfigError(
                "WEBHOOK_SECRET 16-256 belgi bo'lishi kerak"
            )

    # Web sayt
    web_url = (env.get("WEB_URL") or "").strip().rstrip("/")

    if web_url and not web_url.startswith("https://"):
        raise ConfigError("WEB_URL https:// bilan boshlanishi kerak")

    # Sonli sozlamalar
    try:
        port = int(env.get("PORT") or 10000)
        limit = int(env.get("AI_DAILY_LIMIT") or 50)
        interval = int(env.get("KEEPALIVE_INTERVAL") or 600)
    except ValueError as exc:
        raise ConfigError(
            "PORT, AI_DAILY_LIMIT va KEEPALIVE_INTERVAL "
            "butun son bo'lishi kerak"
        ) from exc

    if not 1 <= limit <= 100000:
        raise ConfigError("AI_DAILY_LIMIT noto'g'ri")

    if not 60 <= interval <= 840:
        raise ConfigError(
            "KEEPALIVE_INTERVAL 60 dan 840 soniyagacha bo'lishi kerak"
        )

    # Gemini
    gemini_key = (env.get("GEMINI_API_KEY") or "").strip()
    ai_model = (
        env.get("AI_MODEL") or "gemini-2.5-flash"
    ).strip()

    return Settings(
        bot_token=token,
        supabase_url=url,
        supabase_service_key=service_key,

        web_url=web_url,
        mode=mode,
        webhook_url=webhook_url,
        webhook_secret=secret,
        port=port,

        redis_url=(env.get("REDIS_URL") or "").strip(),

        gemini_api_key=gemini_key,
        ai_model=ai_model,
        ai_daily_limit=limit,

        finance_extended=_bool(
            env.get("FINANCE_EXTENDED_CATEGORIES") or ""
        ),

        log_level=(
            env.get("LOG_LEVEL") or "INFO"
        ).strip().upper(),

        keepalive_url=resolve_keepalive_url(env),
        keepalive_interval=interval,
    )
