"""
Jaskr GymGrid - Application Configuration
Encapsulates environment variables, demo clock snapshot settings, and security tokens.
"""
import os
import datetime as dt

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "jaskr-gymgrid-secret-key-2026-academic-dbms")
    
    # DEMO CLOCK SNAPSHOT: 2026-10-30 10:00:00
    DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() in ("true", "1", "yes")
    APP_TODAY_STR = os.environ.get("APP_TODAY", "2026-10-30")
    APP_NOW_STR = os.environ.get("APP_NOW", "2026-10-30 10:00:00")
    
    @classmethod
    def get_app_today(cls):
        if cls.DEMO_MODE:
            return dt.datetime.strptime(cls.APP_TODAY_STR, "%Y-%m-%d").date()
        return dt.date.today()

    @classmethod
    def get_app_now(cls):
        if cls.DEMO_MODE:
            return dt.datetime.strptime(cls.APP_NOW_STR, "%Y-%m-%d %H:%M:%S")
        return dt.datetime.now()
