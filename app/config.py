"""
Jaskr GymGrid - Application Configuration
Encapsulates environment variables, live system clock sync, and security tokens.
"""
import os
import datetime as dt

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "jaskr-gymgrid-secret-key-2026-academic-dbms")
    
    # Enables demo quick-login shortcuts and visual evaluator aids
    DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() in ("true", "1", "yes")
    
    # System Clock Sync: always uses current real-time system date and time
    # (Optional snapshot override only if APP_TODAY or APP_NOW env vars are explicitly set)
    APP_TODAY_STR = os.environ.get("APP_TODAY", "")
    APP_NOW_STR = os.environ.get("APP_NOW", "")
    
    @classmethod
    def get_app_today(cls):
        if cls.APP_TODAY_STR:
            try:
                return dt.datetime.strptime(cls.APP_TODAY_STR, "%Y-%m-%d").date()
            except Exception:
                pass
        return dt.date.today()

    @classmethod
    def get_app_now(cls):
        if cls.APP_NOW_STR:
            try:
                return dt.datetime.strptime(cls.APP_NOW_STR, "%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        return dt.datetime.now()
