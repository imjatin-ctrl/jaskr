"""
Jaskr GymGrid - Flask Application Factory
Assembles all portal blueprints, config, template context processors, and security error handlers.
"""
from flask import Flask, render_template, redirect, url_for
from app.config import Config
from app.auth import auth_bp, get_current_user
from app.public import public_bp
from app.member import member_bp
from app.staff import staff_bp
from app.owner import owner_bp
from app.admin import admin_bp
from app.lab import lab_bp


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(member_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(owner_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(lab_bp)

    # Convenience shortcuts for top-level auth URLs
    @app.route("/login")
    def redirect_login():
        return redirect(url_for("auth.login"))

    @app.route("/logout")
    def redirect_logout():
        return redirect(url_for("auth.logout"))

    @app.route("/register")
    def redirect_register():
        return redirect(url_for("auth.register"))

    # Global Context Processors
    @app.context_processor
    def inject_globals():
        return {
            "demo_mode": Config.DEMO_MODE,
            "app_today": Config.get_app_today(),
            "app_now": Config.get_app_now(),
            "current_user": get_current_user()
        }

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html", reason="Access denied by role scoping security guard."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    return app
